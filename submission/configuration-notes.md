# Configuration Notes

## Local Development

Copy `.env.example` to `.env` and fill credentials locally.

```bash
cp .env.example .env
```

For the dashboard and RAG service:

```text
EXASOL_DSN=host:8563
EXASOL_USER=<user>
EXASOL_PASSWORD=<password-or-token>
EXASOL_SCHEMA=GUARDIAN_AI
GUARDIAN_STORAGE_BACKEND=auto
GUARDIAN_VECTOR_BACKEND=auto
GUARDIAN_EMBEDDING_PROVIDER=hash
LLM_CHAIN=groq,gemini,deterministic
```

For the simulator:

```text
EXASOL_HOST=localhost
EXASOL_PORT=8563
INTEGRATION_URL=https://guardian-ai-ragex.onrender.com/integrations/guardrail-decision
```

## Render Deployment

Set secrets only in Render environment variables:

```text
EXASOL_DSN
EXASOL_USER
EXASOL_PASSWORD
GROQ_API_KEY
GEMINI_API_KEY
```

Keep these non-secret values aligned with `.env.example`:

```text
GUARDIAN_AUTO_MIGRATE=true
GUARDIAN_STORAGE_BACKEND=exasol
GUARDIAN_VECTOR_BACKEND=exasol
GUARDIAN_EMBEDDING_PROVIDER=hash
GUARDIAN_EMBEDDING_DIM=768
LLM_CHAIN=groq,gemini,deterministic
```

`GUARDIAN_EMBEDDING_PROVIDER=hash` is used for the hosted demo to avoid Gemini embedding quota failures during startup. Gemini can be enabled by setting it to `gemini`.

## Exasol Use

Exasol stores:

- scored decision records
- full regret output
- grounded RAG explanation payloads
- chunked policy and incident documents
- serialized 768-dimensional embeddings

The app uses PyExasol for connection and runs automatic schema setup when `GUARDIAN_AUTO_MIGRATE=true`.
