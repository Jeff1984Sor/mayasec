"""Schemas do payload do webhook WaSender.

Lenientes de propósito (extra=allow): a WaSender pode mandar campos extras que não
queremos quebrar. Extraímos só o que importa para o gateway.
"""
from pydantic import BaseModel, ConfigDict, Field


class WasenderKey(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_me: bool = Field(default=False, alias="fromMe")
    remote_jid: str | None = Field(default=None, alias="remoteJid")
    # Identificador do contato a usar (NÃO usar remoteJid)
    cleaned_sender_pn: str | None = Field(default=None, alias="cleanedSenderPn")
    message_id: str | None = Field(default=None, alias="id")


class WasenderMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: WasenderKey
    message_body: str | None = Field(default=None, alias="messageBody")
    message_type: str | None = Field(default=None, alias="messageType")


class WasenderData(BaseModel):
    model_config = ConfigDict(extra="allow")

    messages: WasenderMessage | None = None
    # session_id pode vir em diferentes nomes dependendo da config; aceitamos os comuns
    session_id: str | None = Field(default=None, alias="sessionId")


class WasenderWebhook(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    event: str | None = None
    session_id: str | None = Field(default=None, alias="sessionId")
    data: WasenderData | None = None
