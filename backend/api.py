"""Application assembly: lifecycle, routers and static frontend hosting."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .core.jobs import router as jobs_router
from .evaluation.api import router as evaluation_router
from .routers import catalog, chat, search, sessions


@asynccontextmanager
async def lifespan(application):
    from .core.jobs import recover_interrupted

    recover_interrupted()
    yield


app = FastAPI(title="xv6 RAG", lifespan=lifespan)

app.include_router(evaluation_router)
app.include_router(jobs_router)
app.include_router(catalog.router)
app.include_router(search.router)
app.include_router(sessions.router)
app.include_router(chat.router)

frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
