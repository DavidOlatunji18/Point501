"""Orchestrates the /chat endpoint: assembles roster + RAG context, then runs
a tool-use loop against the Anthropic API so a single endpoint can answer
start/sit, waiver, trade, and general strategy questions without separate
hardcoded logic per question type."""

import asyncio
import json
from typing import Any

from app.core.config import get_settings
from app.models.team import Team
from app.services import articles as articles_service
from app.services import chat_tools, context, sleeper
from app.services.anthropic_client import get_client

MAX_TOOL_ITERATIONS = 6
AUTO_ARTICLE_SEARCH_LIMIT = 4
MAX_TOKENS = 8192

_SEASON_TYPE_LABELS = {1: "preseason", 2: "regular season", 3: "postseason"}

SYSTEM_PROMPT_TEMPLATE = """You are a fantasy football assistant. Answer the \
user's question directly and concisely, grounded in the data provided below \
and any tool calls you make - not general knowledge about players that may \
be outdated.

Current NFL week: {week}, season {season} ({season_type}).

{roster_section}

{articles_section}

Use the available tools for anything not already covered above: looking up \
a specific player not on the roster, checking a different week's schedule \
or byes, pulling box score stats, checking waiver-wire trends, or searching \
for more specific articles. When you cite information from an article, \
mention its title so the user knows the source. Give a direct, reasoned \
answer - don't pad with disclaimers."""


def _format_roster_section(team: Team | None, roster_context: list[dict[str, Any]]) -> str:
    if team is None:
        return "No team was specified for this question - answer generally."

    lines = [
        f'The user\'s team "{team.name}" (starting lineup slots: '
        f"{', '.join(team.starting_lineup_slots)}):"
    ]
    for player in roster_context:
        injury = f" - {player['injury_status']}" if player.get("injury_status") else ""
        lines.append(f"- {player['name']} ({player['position']}, {player['nfl_team']}){injury}")
    return "\n".join(lines)


def _format_articles_section(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return "No directly relevant ingested articles were found for this question."

    lines = ["Relevant excerpts from ingested fantasy news/analysis:"]
    for a in articles:
        lines.append(f"- [{a['title']}]: {a['text']}")
    return "\n".join(lines)


def _extract_text(content: list[Any]) -> str:
    return "\n".join(block.text for block in content if block.type == "text")


async def _roster_context_or_empty(team: Team | None) -> list[dict[str, Any]]:
    if team is None:
        return []
    return await context.build_roster_players_context(team)


async def answer_question(message: str, team: Team | None) -> dict[str, Any]:
    settings = get_settings()
    client = get_client()

    (week, season, season_type), roster_context, auto_articles = await asyncio.gather(
        sleeper.resolve_current_week(),
        _roster_context_or_empty(team),
        asyncio.to_thread(articles_service.search_articles, message, AUTO_ARTICLE_SEARCH_LIMIT),
    )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        week=week,
        season=season,
        season_type=_SEASON_TYPE_LABELS.get(season_type, season_type),
        roster_section=_format_roster_section(team, roster_context),
        articles_section=_format_articles_section(auto_articles),
    )

    messages: list[dict[str, Any]] = [{"role": "user", "content": message}]
    sources: dict[int, dict[str, Any]] = {
        a["article_id"]: {"title": a["title"], "source": a["source"]} for a in auto_articles
    }
    # Some questions make the model repeat an identical tool call (same name
    # + same arguments) across turns, or even twice in the same turn - each
    # repeat is a wasted network round trip. Cache by (name, args) for the
    # life of this request so a repeat is answered instantly instead of
    # re-dispatched.
    tool_call_cache: dict[tuple[str, str], tuple[str, bool]] = {}

    async def call_model(model: str, *, force_text: bool = False) -> Any:
        kwargs: dict[str, Any] = {"tool_choice": {"type": "none"}} if force_text else {}
        return await client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages,
            tools=chat_tools.TOOLS,
            thinking={"type": "adaptive"},
            **kwargs,
        )

    def _cache_key(block: Any) -> tuple[str, str]:
        return (block.name, json.dumps(block.input, sort_keys=True, default=str))

    async def run_tool_calls(content: list[Any]) -> None:
        tool_use_blocks = [block for block in content if block.type == "tool_use"]

        to_dispatch = []
        seen_keys = set()
        for block in tool_use_blocks:
            key = _cache_key(block)
            if key not in tool_call_cache and key not in seen_keys:
                to_dispatch.append(block)
                seen_keys.add(key)

        if to_dispatch:
            results = await asyncio.gather(
                *(chat_tools.dispatch(block.name, block.input) for block in to_dispatch)
            )
            for block, result in zip(to_dispatch, results):
                tool_call_cache[_cache_key(block)] = result

        tool_results = []
        for block in tool_use_blocks:
            result_content, is_error = tool_call_cache[_cache_key(block)]
            if block.name == "search_articles" and not is_error:
                for item in json.loads(result_content):
                    sources[item["article_id"]] = {
                        "title": item["title"],
                        "source": item["source"],
                    }
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_content,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": tool_results})

    # Start on the fast model - most questions (definitions, general
    # strategy, anything the roster/article context already covers) resolve
    # in one shot. The moment a question actually needs tool-driven research,
    # escalate to the slower-but-more-thorough model for the rest of the
    # loop, since that's exactly the case where digging further matters.
    model = settings.anthropic_fast_model
    response = await call_model(model)

    for _ in range(MAX_TOOL_ITERATIONS):
        if response.stop_reason == "refusal":
            return {
                "answer": (
                    "I wasn't able to answer that question - it may have "
                    "touched on a restricted topic."
                ),
                "sources": [],
            }

        if response.stop_reason != "tool_use":
            break

        await run_tool_calls(response.content)
        model = settings.anthropic_model
        response = await call_model(model)

    if response.stop_reason == "tool_use":
        # Out of tool-call budget - rather than give up, force one last call
        # with tools disabled so the model answers with whatever it's
        # gathered so far instead of returning nothing.
        await run_tool_calls(response.content)
        response = await call_model(model, force_text=True)

    answer = _extract_text(response.content) or (
        "I wasn't able to answer that question - try rephrasing or being more specific."
    )
    return {"answer": answer, "sources": list(sources.values())}
