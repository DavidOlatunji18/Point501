"""Shared Anthropic API client for /chat and /lineup."""

import anthropic

from app.core.config import get_settings

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        settings = get_settings()
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
