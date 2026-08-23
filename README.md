# Guardian-AI

Guardian-AI is a pricing decision intelligence demo. It combines the existing regret engine with a RAG explain layer, Exasol persistence, Exasol-backed evidence retrieval, optional free-tier LLM providers, and a browser dashboard.

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
          Groq/Gemini or Deterministic Generator
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

Guardian-AI supports Exasol as the persistent store. Set `EXASOL_DSN`, `EXASOL_USER`, and `EXASOL_PASSWORD`; the app creates required schema/tables on startup when `GUARDIAN_AUTO_MIGRATE=true`.

Persistent objects:

- `GUARDIAN_AI.DECISIONS`: scored decision records and explanation payloads
- `GUARDIAN_AI.KNOWLEDGE_CHUNKS`: chunked policy/incident knowledge with serialized 768-dim embeddings

When Exasol credentials are not configured, the app falls back to memory for local tests.

## RAG Explain Layer

Knowledge files live under `regret_engine/knowledge/`. The active corpus includes pricing policy, guardrail rules, incident reports, review SOP, escalation rules, business constraints, and good/bad decision examples. Demo decisions and gold RAG evaluation cases live under `regret_engine/data/`.

Fixture layout:

- `regret_engine/knowledge/pricing_policy.md`
- `regret_engine/knowledge/guardrail_rules.md`
- `regret_engine/knowledge/incident_reports.md`
- `regret_engine/knowledge/review_sop.md`
- `regret_engine/knowledge/escalation_rules.md`
- `regret_engine/knowledge/business_constraints.md`
- `regret_engine/knowledge/decision_examples.md`
- `regret_engine/data/mock_decisions.json`
- `regret_engine/data/decision_labels.json`
- `regret_engine/data/gold_eval.json`
- `contracts/decision_contract.md`

The RAG pipeline:

```text
Markdown docs -> chunking -> 768-dim embeddings -> Exasol chunk table -> Python cosine top-k retrieval -> grounded explanation
```

Default embeddings use a deterministic hash provider so tests never call external APIs. Set `GUARDIAN_EMBEDDING_PROVIDER=gemini` and `GEMINI_API_KEY` to use Gemini embeddings.

The explanation generator uses `LLM_CHAIN`, defaulting to:

```text
groq,gemini,deterministic
```

Groq and Gemini are used only when keys are present. Deterministic fallback keeps the demo working offline. The generator cites only retrieved repository evidence. If retrieval fails or the question asks for unsupported fields, it returns:

```text
This information is not found in the uploaded documents
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
EXASOL_DSN                   host:8563
EXASOL_USER                  Exasol username
EXASOL_PASSWORD              Exasol password
EXASOL_SCHEMA                GUARDIAN_AI by default
EXASOL_ENCRYPTION            true by default
EXASOL_COMPRESSION           true by default
GUARDIAN_AUTO_MIGRATE        true by default; creates Exasol schema objects
GUARDIAN_STORAGE_BACKEND     auto, exasol, or memory
GUARDIAN_VECTOR_BACKEND      auto, exasol, or memory
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
exaplus -c "$EXASOL_DSN" -u "$EXASOL_USER" -p "$EXASOL_PASSWORD" -f regret_engine/db/exasol_schema.sql
```

Or run the bundled setup script, which applies schema and ingests the knowledge corpus into Exasol:

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
- provided corpus and JSON fixtures
- RAG retrieval
- grounded explanation behavior
- gold-set RAG evaluation and refusal behavior
- API analytics and dashboard route

## Limitations

- Training data is synthetic.
- Exasol is used only when `EXASOL_DSN`, `EXASOL_USER`, and `EXASOL_PASSWORD` are configured.
- Evidence embeddings are stored in Exasol as JSON text and ranked with Python cosine similarity.
- Groq/Gemini are optional and skipped when keys are missing.
- Confidence is an explainability score derived from model context and evidence coverage, not model calibration.
