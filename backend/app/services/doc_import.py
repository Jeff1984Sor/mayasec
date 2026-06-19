"""Importa o texto de um documento (Google Docs/Drive ou URL) para a base de conhecimento.

Requer que o documento esteja compartilhado como "qualquer pessoa com o link pode ver".
"""
import io
import re

import httpx


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


async def fetch_document_text(url: str) -> str:
    """Retorna o texto do documento. Suporta Google Docs (export txt),
    arquivos do Drive (PDF), e URLs diretas (texto/PDF).
    """
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        # Google Docs -> exporta como texto puro
        m = re.search(r"/document/d/([A-Za-z0-9_-]+)", url)
        if m:
            export = f"https://docs.google.com/document/d/{m.group(1)}/export?format=txt"
            r = await client.get(export)
            r.raise_for_status()
            return r.text

        # Arquivo do Drive (provável PDF)
        m = re.search(r"/file/d/([A-Za-z0-9_-]+)", url) or re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
        if m:
            dl = f"https://drive.google.com/uc?export=download&id={m.group(1)}"
            r = await client.get(dl)
            r.raise_for_status()
            ct = r.headers.get("content-type", "")
            if "pdf" in ct or url.lower().endswith(".pdf"):
                return _extract_pdf(r.content)
            return r.text

        # URL genérica
        r = await client.get(url)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "pdf" in ct or url.lower().endswith(".pdf"):
            return _extract_pdf(r.content)
        return r.text
