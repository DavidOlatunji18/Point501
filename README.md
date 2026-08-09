# Fantasy Football AI Assistant

FastAPI backend that pulls live NFL/fantasy data from Sleeper, stores up to
3 user rosters, retrieves relevant stats/news via RAG, and answers
natural-language fantasy questions through the Anthropic API.

## Status

**Phase 4 (this commit): RAG ingestion pipeline for fantasy news/analysis.**

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

Not yet implemented (next phase):
- `/chat` (RAG + roster context + Anthropic) and `/lineup` (optimizer)

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
cp .env.example .env  # then fill in ANTHROPIC_API_KEY when we get to /chat
```

## Run

```bash
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs` for interactive API docs.

## Try the Sleeper integration

```bash
curl http://127.0.0.1:8000/sleeper/state
curl http://127.0.0.1:8000/sleeper/users/sleeperuser
curl "http://127.0.0.1:8000/sleeper/players/search?q=mahomes"
```
