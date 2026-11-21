import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (register tables)
from app.database import engine
from app.migrate import upgrade_to_head
from app.routers import applications


@asynccontextmanager
async def lifespan(_: FastAPI):
    upgrade_to_head(engine)
    yield


app = FastAPI(title="B12 Application Management", lifespan=lifespan)
# Browser origins allowed to call the API (the local frontend by default).
_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(applications.router)
