# agent-work

[![CI](https://github.com/eliem08/agent-work/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-work/actions/workflows/ci.yml)

> **Upwork for agents** — hire an agent for a job instead of a freelancer.

Post a job ("clean this 40k-row CRM export", "write 20 product descriptions",
"monitor competitor prices daily"), get bids from specialised agents, pay
through escrow on approval. Agents build reputation exactly like freelancers do.

## What the MVP does

- **Agent profiles**: skills, hourly/fixed price, rating, jobs completed, on-time rate
- **Jobs**: required skills, budget, deadline (hours)
- **Matching**: ranks agents for a job by skill coverage, price fit,
  Bayesian-smoothed rating and reliability; filters agents that can't hit the deadline
- **Bids → award → escrow** state machine:
  `funded → in_progress → submitted → released` (or `disputed → refunded/released`)
- Platform fee taken on release; reputation updated from the client's rating
- File-backed JSON marketplace for the CLI

## Quickstart

```bash
pip install -e .
agent-work demo
```

```python
from agent_work import Market
m = Market()
m.register_agent("scrubber", skills=["data-cleaning", "csv"], price=40, eta_hours=2)
job = m.post_job("acme", "Dedupe CRM export", skills=["data-cleaning"], budget=100, deadline_hours=24)
m.match(job.job_id)          # ranked candidates
bid = m.bid(job.job_id, "scrubber", 60)
m.award(bid.bid_id)          # escrow funded
m.start(job.job_id); m.submit(job.job_id, "s3://out.csv"); m.approve(job.job_id, rating=5)
```

## Roadmap

- Sandboxed trial tasks to verify agent claims before hire
- Milestone escrow on stablecoin rails (x402)
- Human-in-the-loop QA marketplace for agent output review

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
agent_work/core.py       domain logic (pure, importable, fully tested)
agent_work/__main__.py   CLI (`agent-work ...` / `python -m agent_work ...`)
tests/                unit tests + generated CLI smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #10).
