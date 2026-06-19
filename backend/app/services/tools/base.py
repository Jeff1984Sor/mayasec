"""Interface Tool + registry.

Cada tool declara name/description/parameters (formato function declaration do Gemini)
e implementa run(). O registry guarda todas as tools conhecidas; get_active_tools()
filtra só as habilitadas no tool_config daquele tenant.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.tenant import Tenant
from app.models.tool_config import ToolConfig


@dataclass
class ToolContext:
    """Tudo que uma tool precisa para rodar."""

    db: AsyncSession
    tenant: Tenant
    contact: Contact
    conversation: Conversation


class Tool(ABC):
    name: str
    description: str
    # JSON Schema dos parâmetros, no formato function declaration do Gemini
    parameters: dict = {"type": "object", "properties": {}}

    @abstractmethod
    async def run(self, ctx: ToolContext, **kwargs) -> dict:
        """Executa a ação e retorna um dict serializável (vai de volta pro modelo)."""

    def to_function_declaration(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    async def get_active_tools(self, db: AsyncSession, tenant: Tenant) -> list[Tool]:
        """Tools habilitadas no tool_config deste tenant."""
        stmt = (
            select(ToolConfig.tool_name)
            .where(ToolConfig.tenant_id == tenant.id)
            .where(ToolConfig.is_enabled.is_(True))
        )
        enabled = {row for row in (await db.execute(stmt)).scalars().all()}
        return [t for name, t in self._tools.items() if name in enabled]


registry = ToolRegistry()
