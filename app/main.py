from contextlib import asynccontextmanager

import anthropic
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import Base, engine
from app.models import article, team  # noqa: F401  (registers models on Base.metadata)
from app.routers import articles, chat, espn, lineup, sleeper, teams
from app.services import anthropic_client
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
    await anthropic_client.close_client()


app = FastAPI(
    title="Fantasy Football AI Assistant",
    description="Sleeper-backed roster data, RAG over fantasy news, and Anthropic-powered Q&A.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sleeper.router)
app.include_router(teams.router)
app.include_router(espn.router)
app.include_router(articles.router)
app.include_router(chat.router)
app.include_router(lineup.router)


@app.exception_handler(SleeperAPIError)
async def sleeper_api_error_handler(request: Request, exc: SleeperAPIError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(EspnAPIError)
async def espn_api_error_handler(request: Request, exc: EspnAPIError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(anthropic.AuthenticationError)
async def anthropic_auth_error_handler(request: Request, exc: anthropic.AuthenticationError):
    return JSONResponse(
        status_code=500, content={"detail": "Anthropic API key is missing or invalid"}
    )


@app.exception_handler(anthropic.RateLimitError)
async def anthropic_rate_limit_handler(request: Request, exc: anthropic.RateLimitError):
    return JSONResponse(status_code=429, content={"detail": "Anthropic API rate limit hit"})


@app.exception_handler(anthropic.APIConnectionError)
async def anthropic_connection_error_handler(
    request: Request, exc: anthropic.APIConnectionError
):
    return JSONResponse(status_code=502, content={"detail": f"Failed to reach Anthropic API: {exc}"})


@app.exception_handler(anthropic.APIStatusError)
async def anthropic_status_error_handler(request: Request, exc: anthropic.APIStatusError):
    return JSONResponse(status_code=502, content={"detail": f"Anthropic API error: {exc.message}"})


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
