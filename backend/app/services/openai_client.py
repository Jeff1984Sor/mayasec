"""openai_client — wrapper async da OpenAI com function calling.

Mesma interface do gemini_client.run_chat() para o agent_service não precisar saber
qual provedor está ativo.
"""
import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger("mayasec.openai")


def _client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada")
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _to_tools(declarations: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": d["name"],
                "description": d.get("description", ""),
                "parameters": d.get("parameters") or {"type": "object", "properties": {}},
            },
        }
        for d in declarations
    ]


def _to_messages(system_instruction: str, history: list[dict], user_text: str) -> list[dict]:
    msgs = [{"role": "system", "content": system_instruction}]
    for h in history:
        role = "assistant" if h.get("role") == "model" else "user"
        text = " ".join(str(p) for p in h.get("parts", []))
        msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": user_text})
    return msgs


async def run_chat(
    *,
    system_instruction: str,
    history: list[dict],
    user_text: str,
    tool_declarations: list[dict],
    tool_runner,
    max_iterations: int = 5,
) -> str:
    client = _client()
    messages = _to_messages(system_instruction, history, user_text)
    tools = _to_tools(tool_declarations) if tool_declarations else None

    for _ in range(max_iterations):
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
        )
        choice = resp.choices[0].message

        if not choice.tool_calls:
            return (choice.content or "").strip()

        # Re-anexa a mensagem do assistente com as tool calls e responde cada uma
        messages.append(
            {
                "role": "assistant",
                "content": choice.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in choice.tool_calls
                ],
            }
        )
        for tc in choice.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                result = await tool_runner(tc.function.name, args)
            except Exception as exc:  # noqa: BLE001 — devolve o erro ao modelo
                logger.exception("tool %s falhou", tc.function.name)
                result = {"erro": str(exc)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    return ""
