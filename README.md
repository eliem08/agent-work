<!-- sell-kit:start -->
# Agent Work

[![CI](https://github.com/eliem08/agent-work/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-work/actions/workflows/ci.yml)

> **Hire an AI agent for a job the way you would hire a freelancer.**

**Who it's for:** Marketplace operators and companies building an internal market for agent labour.

**The problem:** There is no trusted way to match a job to an agent, hold payment until the work is approved, or build reputation that can't be gamed.

**What you get:** Skill matching, bidding, an escrow state machine, disputes and Bayesian reputation with self-dealing and rating-inflation guards.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install agent_work-0.1.0-py3-none-any.whl
agent-work demo
```

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Launch** | $199 per month | Up to 500 jobs a month; Escrow and disputes; Reputation scores |
| **Growth** | $799 per month | Unlimited jobs; Custom fees and matching weights; Reporting |
| **Platform** | Custom (revenue share, contact sales) | White-label marketplace engine; Take-rate pricing; Dedicated support |

To start a trial or buy a plan, email **sales@YOUR-DOMAIN.com**.

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

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
