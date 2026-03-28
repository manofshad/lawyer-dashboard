from pydantic import BaseModel
from fastapi import APIRouter


router = APIRouter()


class EchoRequest(BaseModel):
    message: str


class EchoResponse(BaseModel):
    message: str


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/echo", response_model=EchoResponse)
async def echo(payload: EchoRequest) -> EchoResponse:
    return EchoResponse(message=payload.message)

