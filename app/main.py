from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db.session import Base, engine
from app.models import article, team  # noqa: F401  (registers models on Base.metadata)
from app.routers import articles, espn, sleeper, teams
from app.services import espn as espn_service
from app.services import sleeper as sleeper_service
from app.services.espn import EspnAPIError
from app.services.sleeper import SleeperAPIError


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    await sleeper_service.close_http_client()
    await espn_service.close_http_client()


app = FastAPI(
    title="Fantasy Football AI Assistant",
    description="Sleeper-backed roster data, RAG over fantasy news, and Anthropic-powered Q&A.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(sleeper.router)
app.include_router(teams.router)
app.include_router(espn.router)
app.include_router(articles.router)


@app.exception_handler(SleeperAPIError)
async def sleeper_api_error_handler(request: Request, exc: SleeperAPIError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(EspnAPIError)
async def espn_api_error_handler(request: Request, exc: EspnAPIError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
