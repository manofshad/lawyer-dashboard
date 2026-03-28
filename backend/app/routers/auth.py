from typing import Any

from fastapi import APIRouter, Depends

from ..auth import AuthenticatedUser, get_current_user


router = APIRouter()


@router.get("/api/me")
async def me(current_user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "sub": current_user.claims.get("sub"),
        "email": current_user.claims.get("email"),
        "role": current_user.claims.get("role"),
        "claims": current_user.claims,
    }

