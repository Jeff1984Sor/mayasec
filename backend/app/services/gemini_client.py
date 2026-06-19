"""gemini_client — wrapper async isolando a SDK do Gemini (function calling).

Converte os parameters_schema das tools (JSON Schema) para o formato de
FunctionDeclaration do Gemini e roda um loop de function calling:
modelo pede tool -> executamos -> devolvemos o resultado -> resposta final.
"""
import asyncio
import logging

import google.generativeai as genai
from google.generativeai import protos as glm

from app.core.config import settings

logger = logging.getLogger("mayasec.gemini")

_TYPE_MAP = {
    "object": glm.Type.OBJECT,
    "string": glm.Type.STRING,
    "boolean": glm.Type.BOOLEAN,
    "number": glm.Type.NUMBER,
    "integer": glm.Type.INTEGER,
    "array": glm.Type.ARRAY,
}


def _to_schema(d: dict) -> glm.Schema:
    t = _TYPE_MAP.get(d.get("type", "object"), glm.Type.OBJECT)
    kwargs: dict = {"type_": t}
    if "description" in d:
        kwargs["description"] = d["description"]
    if d.get("type") == "object":
        props = {k: _to_schema(v) for k, v in d.get("properties", {}).items()}
        if props:
            kwargs["properties"] = props
        if d.get("required"):
            kwargs["required"] = d["required"]
    if d.get("type") == "array" and "items" in d:
        kwargs["items"] = _to_schema(d["items"])
    return glm.Schema(**kwargs)


def _to_declaration(decl: dict) -> glm.FunctionDeclaration:
    params = decl.get("parameters") or {}
    kwargs = {"name": decl["name"], "description": decl.get("description", "")}
    if params.get("properties"):
        kwargs["parameters"] = _to_schema(params)
    return glm.FunctionDeclaration(**kwargs)


def _configured() -> bool:
    if not settings.gemini_api_key:
        return False
    genai.configure(api_key=settings.gemini_api_key)
    return True


async def run_chat(
    *,
    system_instruction: str,
    history: list[dict],
    user_text: str,
    tool_declarations: list[dict],
    tool_runner,
    max_iterations: int = 5,
) -> str:
    """Roda uma conversa com function calling e devolve o texto final.

    - history: [{"role": "user"|"model", "parts": ["..."]}]
    - tool_runner: async callable (name, args_dict) -> dict (executa a tool)
    """
    if not _configured():
        raise RuntimeError("GEMINI_API_KEY não configurada")

    tools = None
    if tool_declarations:
        tools = [glm.Tool(function_declarations=[_to_declaration(d) for d in tool_declarations])]

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system_instruction,
        tools=tools,
    )
    chat = model.start_chat(history=history)

    resp = await asyncio.to_thread(chat.send_message, user_text)

    for _ in range(max_iterations):
        parts = resp.candidates[0].content.parts if resp.candidates else []
        calls = [p.function_call for p in parts if getattr(p, "function_call", None) and p.function_call.name]
        if not calls:
            break

        responses = []
        for fc in calls:
            args = {k: v for k, v in (fc.args or {}).items()}
            try:
                result = await tool_runner(fc.name, args)
            except Exception as exc:  # noqa: BLE001 — devolve o erro ao modelo
                logger.exception("tool %s falhou", fc.name)
                result = {"erro": str(exc)}
            responses.append(
                glm.Part(
                    function_response=glm.FunctionResponse(
                        name=fc.name, response={"result": result}
                    )
                )
            )
        resp = await asyncio.to_thread(chat.send_message, responses)

    try:
        return (resp.text or "").strip()
    except Exception:  # noqa: BLE001 — resposta sem texto plano
        return ""
