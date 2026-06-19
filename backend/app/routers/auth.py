"""Auth do painel — login (retorna JWT) e /me."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_token, get_current_user, verify_password
from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    token: str
    user: dict


@router.post("/login", response_model=LoginOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(User).where(User.email == body.email.lower().strip()))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "email ou senha inválidos")
    if not user.is_active:
        raise HTTPException(403, "usuário inativo")

    tenant = await db.get(Tenant, user.tenant_id)
    token = create_token(user)
    return LoginOut(
        token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "tenant_id": str(user.tenant_id),
            "tenant_slug": tenant.slug if tenant else None,
            "tenant_name": tenant.name if tenant else None,
        },
    )


@router.get("/me")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, user.tenant_id)
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "tenant_slug": tenant.slug if tenant else None,
        "tenant_name": tenant.name if tenant else None,
    }
