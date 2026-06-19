"""Pequenos utilitários de texto com IA (OpenAI) usados pelo painel."""
import json

from openai import AsyncOpenAI

from app.core.config import settings


async def improve_faq(question: str, answer: str) -> dict:
    """Melhora a pergunta e a resposta de uma FAQ (clareza, tom cordial, correção).

    Retorna {"question": ..., "answer": ...}.
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada")
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    system = (
        "Você melhora perguntas e respostas de uma base de conhecimento de uma secretária "
        "virtual de WhatsApp (português do Brasil). Reescreva deixando a PERGUNTA clara e "
        "natural (como o cliente perguntaria) e a RESPOSTA cordial, objetiva e bem escrita, "
        "sem inventar informações novas — apenas melhore o que foi dado. "
        'Responda APENAS em JSON: {"question": "...", "answer": "..."}.'
    )
    user = f"PERGUNTA:\n{question}\n\nRESPOSTA:\n{answer}"

    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    return {
        "question": data.get("question", question),
        "answer": data.get("answer", answer),
    }
