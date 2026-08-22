# Guardian-AI

Guardian-AI is a pricing decision intelligence demo. It combines the existing regret engine with a RAG explain layer, Supabase persistence, pgvector retrieval, optional free-tier LLM providers, and a browser dashboard.

## What Exists

The repository already had a Python regret engine trained on synthetic pricing data. The model predicts `units_sold` from SKU, price, historical demand, historical price, and calendar features. Regret is then calculated as:

```text
best predicted counterfactual revenue - selected predicted revenue
```

Revenue is treated as INR in the API output. The included dataset is synthetic and is intended for demo and test use only.

## Architecture

```text
                 Decision Input
                       |
                       v
                 Regret Engine
                       |
                       v
                Decision Record
                       |
                       v
                Explanation Query
                       |
                       v
                 RAG Retriever
                       |
                       v
                Evidence Context
                       |
                       v
          Deterministic Explanation Generator
                       |
                       v
                    Dashboard
```

## Regret Engine

Existing model artifacts live under `regret_engine/models/`. The new service wrapper keeps the original scoring behavior and adds a structured output layer with:

- selected price and best counterfactual price
- predicted demand and revenue for selected and best prices
- regret amount and regret percentage
- risk level
- confidence estimate
- key factors
- assumptions and uncertainties

Backward-compatible endpoint:

```text
POST /calculate-regret
```

## Persistence

Guardian-AI supports Supabase Postgres as the persistent store. Set `GUARDIAN_DATABASE_URL` or `SUPABASE_DB_URL` and the app will create the required tables/functions on startup when `GUARDIAN_AUTO_MIGRATE=true`.

Persistent objects:

- `guardian_decisions`: scored decision records and explanation payloads
- `guardian_knowledge_chunks`: chunked policy/incident knowledge with `vector(768)` embeddings
- `match_guardian_knowledge_chunks`: pgvector similarity search function

When no database URL is configured, the app falls back to memory for local tests.

## RAG Explain Layer

Knowledge files live under `regret_engine/knowledge/`. They are synthetic project docs for local development and are clearly labeled as demo knowledge.

The RAG pipeline:

```text
Markdown docs -> chunking -> 768-dim embeddings -> Supabase pgvector -> top-k retrieval -> grounded explanation
```

Default embeddings use a deterministic hash provider so tests never call external APIs. Set `GUARDIAN_EMBEDDING_PROVIDER=gemini` and `GEMINI_API_KEY` to use Gemini embeddings.

The explanation generator uses `LLM_CHAIN`, defaulting to:

```text
groq,gemini,deterministic
```

Groq and Gemini are used only when keys are present. Deterministic fallback keeps the demo working offline. The generator cites only retrieved repository evidence. If retrieval fails, it returns:

```text
Evidence unavailable / insufficient to provide a grounded explanation.
```

No paid LLM key is required.

## Dashboard

Dashboard is served by FastAPI:

```text
GET /dashboard
```

It shows:

- total decisions
- average regret
- average confidence
- high-risk decisions
- evidence coverage
- regret over time
- risk breakdown
- confidence versus regret
- decision explorer with risk filters
- decision detail view with factors, counterfactual, evidence, and uncertainty

Dashboard metrics are loaded from backend APIs, not hardcoded.

## API

Run backend:

```bash
cd regret_engine
pip install -r requirements.txt
cd ..
uvicorn regret_engine.api.main:app --reload
```

Open dashboard:

```text
http://127.0.0.1:8000/dashboard
```

Main endpoints:

```text
GET  /health
POST /calculate-regret
POST /decision
GET  /decisions
GET  /decisions/{decision_id}
POST /explain/{decision_id}
GET  /decisions/{decision_id}/evidence
GET  /analytics
GET  /rag/evaluation
GET  /dashboard
```

Environment variables:

```text
GUARDIAN_DATABASE_URL         Supabase Postgres connection string
GUARDIAN_AUTO_MIGRATE        true by default; creates schema.sql objects
GUARDIAN_STORAGE_BACKEND     auto, postgres, or memory
GUARDIAN_VECTOR_BACKEND      auto, supabase, or memory
GUARDIAN_EMBEDDING_PROVIDER  hash or gemini
GUARDIAN_EMBEDDING_DIM       768
LLM_CHAIN                    groq,gemini,deterministic
GROQ_API_KEY                 optional
GROQ_MODEL                   llama-3.1-8b-instant by default
GEMINI_API_KEY               optional
GEMINI_CHAT_MODEL            gemini-2.5-flash-lite by default
GEMINI_EMBEDDING_MODEL       gemini-embedding-001 by default
```

Apply schema manually if preferred:

```bash
psql "$GUARDIAN_DATABASE_URL" -f regret_engine/db/schema.sql
```

Or run the bundled setup script, which applies schema and ingests the knowledge corpus into pgvector:

```bash
python -m regret_engine.scripts.setup_persistence
```

Example decision payload:

```json
{
  "decision_id": "manual-001",
  "timestamp": "2026-08-22T10:00:00+05:30",
  "sku": "SYN0001",
  "price": 18.5,
  "previous_units": 8,
  "previous_price": 17.25,
  "rolling_7d_units": 8.4,
  "rolling_30d_units": 7.9,
  "demand_trend": 1.04,
  "demand_momentum": 0.08,
  "day_of_week": 5,
  "month": 8,
  "year": 2026,
  "is_weekend": 1,
  "historical_avg_price": 17.1
}
```

## Tests

```bash
pytest regret_engine/tests
```

Tests cover:

- existing regret endpoint compatibility
- structured decision records
- RAG retrieval
- grounded explanation behavior
- refusal on unrelated queries
- API analytics and dashboard route

## Limitations

- Training data is synthetic.
- Supabase Postgres is used only when `GUARDIAN_DATABASE_URL` or `SUPABASE_DB_URL` is configured.
- pgvector is used only when database connection succeeds; tests use in-memory vectors.
- Groq/Gemini are optional and skipped when keys are missing.
- Confidence is an explainability score derived from model context and evidence coverage, not model calibration.
