# DecisionGuard — Data Layer & Real-Time Guardrail

**Track:** AI for Decision Making — Exasol AI Build Challenge 2026

DecisionGuard watches AI-driven business decisions (like an automated
pricing bot) as they happen, catches the bad ones in real time, and
quantifies how bad they were. This repository contains the **data
layer and guardrail component**: the piece that generates live pricing
decisions, checks each one instantly against Exasol, and flags
anomalies with a graded severity score and a plain-English reason.

---

## Use Case

Companies increasingly let automated systems make live business
decisions — dynamic pricing, auto-approvals, auto-restocking — with
nobody watching whether those decisions are actually *good*. A bug or
adversarial input can cause a pricing bot to crash prices below cost,
or drift prices far above competitors, for hours before anyone
notices. By the time a human catches it, the financial damage is
already done.

This component simulates that exact scenario — a live pricing bot —
and sits a real-time guardrail directly on top of it, backed by
Exasol's fast in-memory analytics engine. Every decision is checked
against recent history, cost constraints, and competitor pricing the
instant it's made, in single-digit-to-low-double-digit milliseconds,
and flagged with a severity score if it looks dangerous.

---

## System Flow

```
                    ┌─────────────────────┐
                    │   Bot Simulator      │
                    │  (generates pricing  │
                    │   decisions live)    │
                    └──────────┬───────────┘
                               │ writes decision
                               ▼
                    ┌─────────────────────┐
                    │   Exasol Database    │
                    │  (decisions,         │
                    │   market_context,    │
                    │   outcomes)          │
                    └──────────┬───────────┘
                               │ reads recent history
                               ▼
                    ┌─────────────────────┐
                    │   Guardrail Engine   │
                    │  1. Cost floor check │
                    │  2. Competitor ceiling│
                    │  3. Z-score deviation│
                    │  4. Burst pattern    │
                    └──────────┬───────────┘
                               │ flags + severity
                               ▼
                    ┌─────────────────────┐
                    │   Exasol Database    │
                    │  (decision updated:  │
                    │   flagged, reason,   │
                    │   severity)          │
                    └──────────┬───────────┘
                               │ served via
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Layer      │
                    │  /decisions/latest   │
                    │  /decisions/flagged  │
                    │  /stats              │
                    └──────────┬───────────┘
                               │ consumed by
                               ▼
                    ┌─────────────────────┐
                    │  Dashboard / RAG     │
                    │  Explain Layer       │
                    │  (rest of the team)  │
                    └─────────────────────┘
```

---

## Folder Structure

Create this structure before you begin:

```
decisionguard-dataguardrail/
├── venv/                     (created by you — virtual environment)
├── sql/
│   └── schema.sql            (table definitions)
├── scripts/
│   ├── run_schema.py         (creates tables in Exasol)
│   ├── seed_data.py          (loads 90 days of historical data)
│   ├── bot_simulator.py      (live decision generator + guardrail)
│   ├── test_guardrail.py     (standalone check test)
│   └── test_burst.py         (burst-detection specific test)
├── app/
│   ├── __init__.py           (empty — makes `app` a package)
│   ├── main.py                (FastAPI app)
│   ├── db.py                  (shared Exasol connection)
│   ├── guardrail.py           (detection logic)
│   └── models.py              (Pydantic schemas for API responses)
├── requirements.txt
├── .env                        (Exasol credentials — do NOT commit this)
└── README.md
```

---

## Step 1 — Install Docker Desktop (Windows)

Exasol Personal's native local install currently only supports macOS.
On Windows, use the dockerized Exasol database image instead.

1. Download and install **Docker Desktop** from docker.com.
2. During install, accept the prompt to enable **WSL2** if asked.
3. Launch Docker Desktop and wait until it shows "Docker Desktop is
   running" (check the whale icon in your system tray).

Verify it's working:
```powershell
docker --version
```

---

## Step 2 — Pull and run the Exasol Docker image

```powershell
docker pull exasol/docker-db:latest
docker run -d -p 8563:8563 -p 6583:6583 --name exasol-db --privileged exasol/docker-db:latest
```

**What you'll see:** the `pull` command downloads the image (a few GB —
can take a few minutes depending on your connection). The `run`
command starts the container in the background and prints a long
container ID.

Give the container 1–2 minutes to fully initialize on first start, then verify:
```powershell
docker ps
```
You should see `exasol-db` listed with status `Up`.

> If `docker pull` fails with an HTTPS/authorization error, this is
> usually caused by a proxy, VPN, or campus network issue — restart
> Docker Desktop, or try switching to a mobile hotspot and retrying,
> then configure Docker's proxy settings permanently if needed.

---

## Step 3 — Clone the repo and set up the Python environment

```powershell
git clone <your-repo-url>
cd decisionguard-dataguardrail

python -m venv venv
venv\Scripts\activate
```
You should see `(venv)` appear at the start of your terminal prompt.

If activation is blocked by PowerShell's execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then retry `venv\Scripts\activate`.

---

## Step 4 — Install dependencies

`requirements.txt`:
```
pyexasol
fastapi
uvicorn
pandas
numpy
python-dotenv
pydantic
requests
```

Install:
```powershell
pip install -r requirements.txt
```

---

## Step 5 — Configure your `.env` file

Create a file named `.env` in the project root:
```
EXASOL_HOST=localhost
EXASOL_PORT=8563
EXASOL_USER=sys
EXASOL_PASSWORD=exasol
```

---

## Step 6 — Create the schema

```powershell
python scripts/run_schema.py
```

**Expected output:**
```
Schema created successfully.
Tables: [('MARKET_CONTEXT',), ('DECISIONS',), ('OUTCOMES',)]
```

---

## Step 7 — Seed historical data

```powershell
python scripts/seed_data.py
```

**Expected output:**
```
Inserted 1800 market_context rows
Inserted 1800 decision rows
Inserted 1800 outcome rows
Sample decisions: [(...), (...), ...]
```
This generates 90 days of realistic pricing history across 20 SKUs,
which the guardrail uses as its baseline for "normal" behavior.

---

## Step 8 — Run the live bot simulator + guardrail

```powershell
python scripts/bot_simulator.py
```

**Expected output (routine decisions):**
```
Bot simulator + guardrail running. Press Ctrl+C to stop.
Type 'a' + Enter to inject a CRASH anomaly (below-cost) on the next decision.
Type 's' + Enter to inject a SPIKE anomaly (above-competitor) on the next decision.

[OK in 31.24ms] SKU-0014: 205.23 -> 205.84
[OK in 40.58ms] SKU-0008: 966.61 -> 956.55
```

Type `a` and hit Enter to inject a below-cost crash:
```
a
>> Crash anomaly armed for next decision.
[FLAGGED in 7.81ms | severity 1.0] SKU-0009: 374.91 -> 150.74 | Price 150.74 is below cost 275.2 (cost floor violation, 45.2% under)
```

Type `s` and hit Enter to inject an above-competitor spike:
```
s
>> Spike anomaly armed for next decision.
[FLAGGED in 15.94ms | severity 0.798] SKU-0010: 525.85 -> 803.78 | Price 803.78 is 39.8% above competitor price 574.86
```

Leave this running in its own terminal — it's your live demo engine.

---

## Step 9 — Run the API (in a second terminal)

Activate the venv again in the new terminal, then:
```powershell
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` in your browser to explore and test
every endpoint interactively.

**Key endpoints:**

| Endpoint | Description |
|---|---|
| `GET /decisions/latest?limit=20` | Most recent decisions |
| `GET /decisions/flagged?limit=20` | Only flagged (anomalous) decisions |
| `GET /decisions/{decision_id}` | Full detail on one decision |
| `GET /stats` | Total decisions, flagged count, catch rate |
| `GET /health` | Status check |

**Example `/stats` output:**
```json
{
  "total_decisions": 1812,
  "flagged_decisions": 4,
  "catch_rate_pct": 0.22
}
```

**Example `/decisions/flagged` output:**
```json
{
  "decisions": [
    {
      "decision_id": "9a3cc5ef-4d2b-4d28-9fbc-dfe8cb2239dc",
      "sku_id": "SKU-0009",
      "event_time": "2026-08-23 01:16:45.000000",
      "old_price": 374.91,
      "new_price": 150.74,
      "reason_code": "ANOMALY_INJECTED_CRASH",
      "flagged": true,
      "flag_reason": "Price 150.74 is below cost 275.2 (cost floor violation, 45.2% under)",
      "confidence": 0.9063,
      "severity": 1.0
    }
  ]
}
```

---

## Step 10 — Run standalone tests (optional, for verification)

Test all four guardrail checks against the 10 most recent decisions:
```powershell
python scripts/test_guardrail.py
```

Test the burst-pattern detector specifically (fires 5 rapid decisions
on one SKU, expects the 4th and 5th to flag):
```powershell
python scripts/test_burst.py
```

---

## How Exasol Is Used

Exasol is the analytics backbone this entire guardrail depends on.
Every detection check requires a fast lookup against historical or
current data:

- **Cost floor check** — pulls the SKU's latest cost from `market_context`
- **Competitor ceiling check** — pulls the SKU's latest competitor price
- **Z-score check** — pulls the last 30 routine price changes for that SKU to compute mean/stddev of "normal" behavior
- **Burst check** — counts recent decisions for that SKU within a rolling time window

These queries run against Exasol's in-memory MPP (Massively Parallel
Processing) engine, which is what keeps detection latency in the
single-to-low-double-digit millisecond range even as decision history
grows into the thousands of rows. This speed is the actual enabler of
real-time guardrailing — without a fast analytics engine underneath
it, "catch a bad decision as it happens" would degrade into a slow
batch report instead of a live safeguard.

---

## Detection Logic Summary

| Check | Triggers when | Severity formula |
|---|---|---|
| Cost floor violation | New price < current cost | `0.6 + % below cost` |
| Competitor ceiling violation | New price > 1.25 × competitor price | `0.4 + % above competitor` |
| Statistical (z-score) deviation | Price change is >3 std deviations from SKU's normal behavior | `z-score / 10` |
| Burst pattern | >3 price changes for one SKU within 10 minutes | Fixed `0.7` |

---

## Team Handoff Contract

Base URL: `http://localhost:8000`

Any other component (regret engine, RAG explain layer, dashboard)
should consume decision data via the `/decisions/*` and `/stats`
endpoints above rather than querying Exasol directly, so this
guardrail remains the single source of truth for what's been flagged
and why.
