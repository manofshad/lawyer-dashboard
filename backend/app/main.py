from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.auth import router as auth_router
from .routers.core import router as core_router
<<<<<<< HEAD
from .routers.extractions import router as extractions_router
=======
from .routers.incidents import router as incidents_router
>>>>>>> e47c39000c3dabd247a01b4b07f971f359cda407
from .settings import get_settings


settings = get_settings()
app = FastAPI(title="Hackathon Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router)
app.include_router(auth_router)
<<<<<<< HEAD
app.include_router(extractions_router)
=======
app.include_router(incidents_router)
>>>>>>> e47c39000c3dabd247a01b4b07f971f359cda407
