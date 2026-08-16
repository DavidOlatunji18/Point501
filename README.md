# Fantasy Football AI Assistant

FastAPI backend that pulls live NFL/fantasy data from Sleeper, stores up to
3 user rosters, retrieves relevant stats/news via RAG, and answers
natural-language fantasy questions through the Anthropic API.

## Status

**Phase 6 (this commit): React frontend - Rosters, Chat, and Lineup pages.**

Implemented:
- Project structure (`app/core`, `app/db`, `app/models`, `app/schemas`,
  `app/services`, `app/routers`)
- Async Sleeper client (`app/services/sleeper.py`) covering NFL state,
  users, leagues, rosters, matchups, trending players, and a cached full
  player lookup (name/team/position/injury_status)
- Read-only `/sleeper/*` endpoints for all of the above
- SQLite-backed `Team` + `RosterPlayer` models (`app/models/team.py`) -
  storing player *identity* and lineup config only, not stats/injury (those
  are looked up live from Sleeper via `sleeper_player_id`)
- `/teams` CRUD: create (up to 3, manual paste-as-text or Sleeper
  username+league_id auto-pull), list, get, patch (name/lineup slots),
  delete, `/sync` (re-pull a Sleeper-sourced roster), and per-player
  add/edit/remove without re-entering the whole roster
- Free-text roster parser (`app/services/roster_import.py`) that best-effort
  matches pasted player names against Sleeper's player database to backfill
  position/team/`sleeper_player_id`
- Async ESPN client (`app/services/espn.py`) - Sleeper's public API has no
  schedule or box-score endpoint, so this fills that gap: weekly schedule
  (`/espn/schedule`), derived bye weeks (`/espn/schedule/byes`, computed by
  diffing the full 32-team list against who's playing that week - ESPN
  doesn't expose byes directly either), and per-game box scores
  (`/espn/games/{event_id}/boxscore`) with raw per-player stats by category
  (passing/rushing/receiving/etc). Team abbreviations are normalized to
  Sleeper's convention (`WSH` -> `WAS`) so roster data joins cleanly.
  Kickoff times are converted from ESPN's raw UTC to Eastern (`kickoff_et`)
  since UTC rolls an evening ET game onto the next calendar date.
- Article ingestion pipeline: `/articles` (paste JSON) and `/articles/upload`
  (text file) chunk the content (`app/services/chunking.py`, paragraph-
  respecting, no mid-word splits), embed it with a local sentence-transformers
  model, and store it in a persistent Chroma collection
  (`app/services/vector_store.py`) - no external embedding API key or
  per-call cost. `/articles/search?q=` does the retrieval half (embeds the
  query, returns the closest chunks with article/source attribution) - this
  is what `/chat` will call for RAG context. Duplicate content (by hash) is
  rejected with 409, including under a concurrent-request race. SQLite
  (`Article` model) tracks metadata for listing/deleting; the chunk text +
  embeddings live only in Chroma.
- `POST /chat` (`app/services/chat.py`) - a single flexible endpoint for any
  natural-language question (start/sit, waivers, trades, general strategy -
  no separate hardcoded endpoint per question type). Automatically includes
  the specified team's roster (with live injury status) and a RAG search
  over ingested articles as context, then runs an agentic tool-use loop
  against Claude Opus 5 (`app/services/chat_tools.py`: search players,
  schedule/byes, box scores, trending adds/drops, targeted article search)
  so the model pulls exactly the additional data a given question needs.
  Returns `{answer, sources}`.
- `GET /lineup` (`app/services/lineup.py`) - a structured counterpart to
  `/chat` for the single highest-value use case: given a team's roster +
  starting lineup slots, recommend a full lineup for the week. Forces the
  model to respond via a single `strict: true` tool call
  (`recommend_lineup`) instead of freeform text, so the result is
  guaranteed-parseable - then validates the model's own output (no
  duplicate/hallucinated/omitted player_ids) before returning it. Defaults
  week/season/season_type from Sleeper's live NFL state when not specified.

- `frontend/` - Vite + React + TypeScript + Tailwind app with three pages:
  - **Rosters** - create a team (paste-as-text or Sleeper import), view/edit
    the starting lineup slots, and add/edit/remove individual players
  - **Chat** - a conversation UI against `/chat`, with a team selector
    (or "General" for no roster context) and Markdown-rendered answers with
    cited sources
  - **Lineup** - pick a team (+ optional week/season override) and get the
    full `/lineup` recommendation, grouped by slot with per-pick reasoning
    and a bench list

  Talks to the backend via `frontend/src/lib/api.ts` (typed fetch wrappers
  mirroring `app/schemas/*.py`); CORS is enabled backend-side via
  `FRONTEND_ORIGIN` (defaults to the Vite dev server at `localhost:5173`).

Not yet implemented: Docker/CI/CD/Kubernetes/cloud deployment.

### Note: ESPN API is unofficial

Undocumented and can change without notice. Kept isolated behind
`app/services/espn.py`'s own typed exceptions (`EspnNotFoundError`,
`EspnAPIError`) so breakage stays contained. Also note ESPN's `/scoreboard`
`year` param is silently ignored - the season is actually selected via the
`dates` param (a bare year, e.g. `dates=2025`), which is what
`get_scoreboard()` uses.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in ANTHROPIC_API_KEY (required for /chat and /lineup)
```

## Run

```bash
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs` for interactive API docs.

Then, in a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. It expects the backend at `http://localhost:8000`
by default - override with `VITE_API_BASE_URL` if needed.

## Try the Sleeper integration

```bash
curl http://127.0.0.1:8000/sleeper/state
curl http://127.0.0.1:8000/sleeper/users/sleeperuser
curl "http://127.0.0.1:8000/sleeper/players/search?q=mahomes"
```
