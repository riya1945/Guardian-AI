# Guardian-AI

Guardian-AI, also called RaGeX in the demo, is an AI pricing guardrail system. It combines a live pricing simulator, Exasol-backed guardrail checks, a regret engine, grounded RAG explanations, and a dashboard.

## Final Submission

This repository is the public submission package. It contains source code, sample data, Exasol schema, deployment config, pitch deck, screenshots, and a run guide.

Submission materials:

- Source code: top-level simulator/guardrail files and `regret_engine/`
- Pitch deck: `submission/pitch/RaGeX_Pricing_Guardrail_Pitch.pptx`
- Pitch deck PDF: `submission/pitch/RaGeX_Pricing_Guardrail_Pitch.pdf`
- Screenshots: `submission/screenshots/`
- Sample integration payload: `submission/samples/guardrail_decision_payload.json`
- Configuration notes: `submission/configuration-notes.md`
- Demo video: https://drive.google.com/drive/folders/1Q3yXdWEE_vN5B5YmSyDkjWvCQJievem8?usp=sharing
- Dashboard style: dark navy RaGeX console matching the pitch deck design system

## Problem

Automated pricing systems can make high-impact decisions faster than human teams can review them. A bad model release, stale competitor signal, or data pipeline bug can push prices below cost, above competitor ceilings, or into sudden drift. Existing dashboards usually show outcomes after damage has happened; they do not combine live guardrails, regret scoring, and evidence-backed explanation in one review workflow.

## Solution

Guardian-AI watches pricing decisions as they happen. It accepts simulator or live guardrail decisions, stores them in Exasol, scores counterfactual regret in INR, retrieves relevant policy and incident evidence, generates grounded explanations, and displays everything in a live dashboard for review.

Core workflow:

```text
Pricing decision -> Exasol persistence -> Guardrail status -> Regret engine -> RAG evidence -> Dashboard review
```

## How Exasol Is Used

Exasol is the analytical and persistence layer for the demo.

- Exasol stores seeded historical pricing data used by the simulator and guardrail.
- Exasol stores live pricing decisions, guardrail status, regret output, and explanation payloads.
- Exasol stores RAG knowledge chunks and serialized 768-dimensional embeddings.
- PyExasol powers schema setup, seed loading, live reads, and writes.
- Fast Exasol reads support rolling guardrail checks such as floor breach, ceiling breach, z-score deviation, and burst patterns.
- Render deployment uses a reachable Exasol cloud database so the public dashboard remains persistent across service restarts.

For local development, Exasol Personal can run the same schema and seed scripts. For the hosted demo, the app uses the same Exasol-compatible connection path through environment variables.

## Team Components

- `divija`: Data layer, Exasol schema, seed data, bot simulator, live guardrail checks.
- `riya`: Regret engine, reward model, off-policy counterfactual scoring.
- `ranbir`: RAG explain layer, evidence retrieval, dashboard, Render integration endpoint.

## Live Demo

Dashboard:

```text
https://guardian-ai-ragex.onrender.com/dashboard
```

Guardrail integration endpoint:

```text
https://guardian-ai-ragex.onrender.com/integrations/guardrail-decision
```

Health check:

```text
https://guardian-ai-ragex.onrender.com/health
```

## Architecture

```text
Bot Simulator
  -> Exasol decision tables
  -> Guardrail flags
  -> Integration endpoint
  -> Regret scoring
  -> RAG evidence retrieval
  -> Grounded explanation
  -> Dashboard
```

## Data Layer And Guardrail

Top-level files provide Divija's Exasol data layer and real-time guardrail demo:

- `schema.sql`: market, decision, and outcome tables
- `run_schema.py`: schema setup
- `seed_data.py`: deterministic synthetic historical data
- `bot_simulator.py`: live pricing bot with anomaly injection
- `app/guardrail.py`: floor, ceiling, z-score, and burst checks
- `main.py`: FastAPI endpoints for latest decisions, flagged decisions, and stats

Local simulator setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run_schema.py
python seed_data.py
python bot_simulator.py
```

Simulator handoff payload is posted to:

```text
POST /integrations/guardrail-decision
```

Expected payload:

```json
{
  "decision_id": "uuid-or-trace-id",
  "sku_id": "SKU-0001",
  "event_time": "2026-08-23 15:30:00",
  "old_price": 499.0,
  "new_price": 699.0,
  "reason_code": "ANOMALY_INJECTED_SPIKE",
  "flagged": true,
  "flag_reason": "Price exceeds competitor ceiling",
  "confidence": 0.91,
  "severity": 0.8,
  "demand_signal": 0.82,
  "competitor_price": 510.0,
  "inventory_level": 120
}
```

## Regret Engine

The regret engine lives under `regret_engine/`. It trains or loads a reward model from synthetic pricing history and estimates regret as:

```text
best predicted counterfactual revenue - selected predicted revenue
```

Core outputs include selected price, best counterfactual price, predicted demand, predicted revenue, regret amount, regret percentage, risk level, confidence, factors, assumptions, and uncertainties.

Backward-compatible endpoint:

```text
POST /calculate-regret
```

## RAG Explain Layer

Knowledge files live under `regret_engine/knowledge/`. The corpus includes pricing policy, guardrail rules, incident reports, review SOP, escalation rules, business constraints, and examples of good and bad decisions.

RAG flow:

```text
Markdown docs -> chunking -> 768-dim embeddings -> Exasol vector table -> cosine retrieval -> grounded explanation
```

Default embeddings use deterministic hashing so local tests and Render startup do not fail on quota. Set `GUARDIAN_EMBEDDING_PROVIDER=gemini` and `GEMINI_API_KEY` to use Gemini embeddings.

Generation uses `LLM_CHAIN`, defaulting to:

```text
groq,gemini,deterministic
```

Groq and Gemini are optional. Deterministic fallback keeps the demo running without paid providers.

## Dashboard

Run service:

```bash
cd regret_engine
pip install -r requirements.txt
cd ..
uvicorn regret_engine.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

Dashboard shows total decisions, average regret, average confidence, high-risk decisions, evidence coverage, regret over time, risk breakdown, confidence versus regret, decision explorer, and detail view with factors, counterfactual, evidence, and uncertainty.

The dashboard uses the RaGeX deck design system: dark navy surfaces, cyan for data and Exasol, violet for RAG and evidence, and green, amber, red only for decision severity. The frontend polls `GET /dashboard/feed`, a consolidated endpoint that returns health, analytics, and decision records in one response.

## API Endpoints

```text
GET  /health
POST /calculate-regret
POST /decision
POST /integrations/guardrail-decision
GET  /integrations/contracts
GET  /decisions
GET  /decisions/{decision_id}
POST /explain/{decision_id}
GET  /decisions/{decision_id}/evidence
GET  /analytics
GET  /rag/evaluation
GET  /dashboard
GET  /dashboard/metrics
GET  /dashboard/interventions
GET  /dashboard/leaderboard
GET  /dashboard/model
GET  /dashboard/ab
GET  /dashboard/settings
GET  /dashboard/feed
```

## Persistence

Ranbir's service supports Exasol as persistent storage. Set `EXASOL_DSN`, `EXASOL_USER`, and `EXASOL_PASSWORD`; startup creates required schema objects when `GUARDIAN_AUTO_MIGRATE=true`.

Persistent objects:

- `GUARDIAN_AI.DECISIONS`: scored decision records and explanation payloads
- `GUARDIAN_AI.KNOWLEDGE_CHUNKS`: chunked policy and incident knowledge with serialized 768-dim embeddings

If Exasol credentials are not configured, the app falls back to memory for local tests.

## Environment

Copy `.env.example` to `.env`. Keep secrets local or in Render environment variables only.

Important variables:

```text
EXASOL_DSN                   host:8563 for RAG/dashboard service
EXASOL_HOST                  host for local simulator
EXASOL_PORT                  port for local simulator
EXASOL_USER                  Exasol username
EXASOL_PASSWORD              Exasol password or token
EXASOL_SCHEMA                GUARDIAN_AI by default
EXASOL_ENCRYPTION            true by default
EXASOL_COMPRESSION           true by default
EXASOL_CERTIFICATE_VALIDATION false for local starter self-signed TLS, true for trusted certs
GUARDIAN_AUTO_MIGRATE        true by default
GUARDIAN_STORAGE_BACKEND     auto, exasol, or memory
GUARDIAN_VECTOR_BACKEND      auto, exasol, or memory
GUARDIAN_EMBEDDING_PROVIDER  hash or gemini
GUARDIAN_EMBEDDING_DIM       768
INTEGRATION_URL              Render guardrail handoff endpoint
LLM_CHAIN                    groq,gemini,deterministic
GROQ_API_KEY                 optional
GROQ_MODEL                   openai/gpt-oss-20b by default
GEMINI_API_KEY               optional
GEMINI_CHAT_MODEL            gemini-2.5-flash-lite by default
GEMINI_EMBEDDING_MODEL       gemini-embedding-001 by default
```

## Render Deployment

This repo includes `render.yaml` for service `guardian-ai-ragex`.

Render settings:

```text
Build command: pip install -r regret_engine/requirements.txt
Start command: uvicorn regret_engine.api.main:app --host 0.0.0.0 --port $PORT
Health check: /health
```

Set secrets in Render environment variables, not git:

```text
EXASOL_DSN
EXASOL_USER
EXASOL_PASSWORD
GROQ_API_KEY
GEMINI_API_KEY
```

The deployed service currently runs at:

```text
https://guardian-ai-ragex.onrender.com
```

## Tests

Run regret/RAG/API tests:

```bash
pytest regret_engine/tests
```

Data-layer tests require a reachable Exasol instance:

```bash
python run_schema.py
python seed_data.py
python test_guardrail.py
python test_burst.py
```
