# Guardian-AI

Guardian-AI is a local pricing decision intelligence demo. It combines the existing regret engine with a RAG explain layer and a browser dashboard.

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

## RAG Explain Layer

Knowledge files live under `regret_engine/knowledge/`. They are synthetic project docs for local development and are clearly labeled as demo knowledge.

The RAG pipeline:

```text
Markdown docs -> chunking -> TF-IDF embeddings -> local vector store -> top-k retrieval -> grounded explanation
```

The generator is deterministic by default. It cites only retrieved repository evidence. If retrieval fails, it returns:

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
- No persistent database is included.
- Vector retrieval is local TF-IDF, chosen to keep the repo lightweight and free-tier friendly.
- Explanation generation is deterministic, not a hosted LLM.
- Confidence is an explainability score derived from model context and evidence coverage, not model calibration.
