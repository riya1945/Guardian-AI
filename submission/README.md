# Guardian-AI / RaGeX Final Submission

This folder contains final submission materials for the Exasol AI Build Challenge demo.

## Included Materials

- `../README.md`: project overview, problem, solution, architecture, setup, deployment, and Exasol usage.
- `pitch/RaGeX_Pricing_Guardrail_Pitch.pptx`: editable pitch deck.
- `pitch/RaGeX_Pricing_Guardrail_Pitch.pdf`: PDF export of the pitch deck.
- `screenshots/main-dashboard.png`: live dashboard overview.
- `screenshots/dashboard-with-detail.png`: dashboard with decision detail and grounded explanation.
- `screenshots/mobile-dashboard.png`: mobile-width dashboard view.
- `samples/guardrail_decision_payload.json`: sample simulator-to-dashboard integration payload.

## Live Links

Dashboard:

```text
https://guardian-ai-ragex.onrender.com/dashboard
```

Health check:

```text
https://guardian-ai-ragex.onrender.com/health
```

Guardrail integration endpoint:

```text
https://guardian-ai-ragex.onrender.com/integrations/guardrail-decision
```

## Demo Video

Root README includes the hosted demo video link. This folder also includes the generated local demo video:

```text
demo-video/ragex-demo-3min.mp4
```

## Submission Notes

- Repository visibility: public.
- Default deployed backend: Render web service.
- Persistent database: Exasol Cloud / Exasol-compatible connection through PyExasol.
- Vector backend: Exasol-backed 768-dimensional Python vector retrieval.
- LLM stack: Groq first, Gemini fallback, deterministic fallback.
- Secrets are excluded from git and supplied through platform environment variables.
