# Point501

A fantasy football assistant that connects to your real Sleeper roster and uses
an AI agent to answer start/sit, waiver, and strategy questions grounded in
live player data, matchup context, and ingested fantasy news — not just the
model's general knowledge.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?logo=tailwindcss&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Sonnet%205%20%2F%20Opus%205-D97757)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector%20store-6E56CF)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white)
![CI](https://github.com/DavidOlatunji18/Point501/actions/workflows/ci.yml/badge.svg)

## Screenshots

*(Coming soon)*

## Features

- **Live roster sync** — import a team directly from Sleeper (username +
  league) or paste one in manually; re-sync Sleeper-sourced teams on demand
  after waiver moves or trades
- **AI lineup builder** — a single Claude call assigns every starting slot
  and bench spot using this week's matchups, byes, injuries, and season
  stats, with slot-eligibility rules (e.g. FLEX) enforced server-side
- **Conversational Q&A** — an agentic chat endpoint that decides for itself
  when to look up a player, check a schedule, pull box score stats, or check
  waiver-wire trends, grounded in your actual roster instead of guessing
- **Retrieval-augmented answers** — a ChromaDB vector store over
  ingested fantasy news/analysis (manually pasted or pulled automatically
  from RSS feeds on a schedule) so the assistant can cite real, current
  analysis
- **Cost/latency-aware model routing** — chat starts on a fast model and
  only escalates to a stronger, more thorough model when a question actually
  requires multi-step research

## Architecture

```
React + TypeScript (Vite, Tailwind CSS v4)
        │
        ▼
FastAPI backend
  ├── Sleeper API      → live rosters, players, injuries, trending adds/drops
  ├── ESPN API         → schedules, byes, box scores
  ├── SQLite/SQLAlchemy → team/roster storage
  ├── ChromaDB + sentence-transformers → article embeddings for RAG
  ├── APScheduler       → periodic RSS ingestion of fantasy news
  └── Anthropic Claude   → lineup generation & agentic chat (tool use)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4 |
| Backend | FastAPI, SQLAlchemy (SQLite locally, Postgres in containers) |
| AI | Anthropic Claude (Sonnet 5 / Opus 5), agentic tool use |
| Retrieval | ChromaDB, sentence-transformers embeddings |
| Data sources | Sleeper API, ESPN (unofficial) API |
| Scheduling | APScheduler (automated news ingestion) |
| Infrastructure | Docker, Docker Compose, Kubernetes, GitHub Actions CI/CD |

## Getting Started

### Prerequisites

- Python 3.13+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

## Infrastructure

The app is containerized and has real Kubernetes manifests, both run and
verified locally rather than on a permanently-live cloud cluster — this
isn't a publicly hosted product, so the infra exists to be demoed, not to
run 24/7. The manifests are written to be AWS-ready (see the note in
`k8s/postgres-deployment.yaml` on swapping in RDS) without taking on a
recurring cloud bill.

### Docker Compose

Runs the full stack (Postgres included) locally in containers:

```bash
docker compose up --build
```

Backend at `http://localhost:8000`, frontend at `http://localhost:5173`.

### Kubernetes (local, via kind)

```bash
kind create cluster
# install an ingress controller (kind's documented recipe):
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

docker build -t point501-backend:local .
docker build -t point501-frontend:local --build-arg VITE_API_BASE_URL=/api ./frontend
kind load docker-image point501-backend:local
kind load docker-image point501-frontend:local

cp k8s/db-secret.example.yaml k8s/db-secret.yaml
cp k8s/anthropic-secret.example.yaml k8s/anthropic-secret.yaml   # then fill in a real key

kubectl apply -k k8s/
```

### CI/CD

`.github/workflows/ci.yml` runs on every push: backend tests (pytest),
frontend lint + build, then builds and pushes both Docker images to GHCR,
then spins up an ephemeral `kind` cluster inside the runner, deploys the
just-pushed images with the same manifests above, and verifies both
services respond before tearing the cluster down. No persistent
infrastructure, no cloud cost — every run is a real, from-scratch proof
that the containers and manifests work together.

## Project Structure

```
app/
  routers/     FastAPI route handlers
  services/     Sleeper/ESPN clients, RAG pipeline, chat agent, lineup builder
  models/       SQLAlchemy models
  schemas/      Pydantic request/response schemas
  core/         Settings/config
tests/         pytest suite (roster parsing, FLEX-slot validation, health check)
frontend/
  src/pages/       Route-level pages (Rosters, Lineup, Chat, Login/Signup)
  src/components/  Shared UI components
  src/context/     Client-side state (teams, lineup, chat, user)
k8s/            Kubernetes manifests (kustomize-based)
Dockerfile               Backend image
frontend/Dockerfile      Frontend image (multi-stage, served via nginx)
docker-compose.yml       Full local stack (backend + frontend + Postgres)
.github/workflows/ci.yml CI: tests, lint/build, image build+push, ephemeral kind deploy
```
