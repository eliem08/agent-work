"""Operating commands: run the marketplace against a persistent store (also served by the web app).

Escrow here is a ledger: it records who owes what and when funds release. Moving the money is done by the
operator's payment provider; `payouts` prints exactly what to settle.
"""

import itertools
import json
import os
from dataclasses import asdict

from . import connect
from .core import PLATFORM_FEE, AgentProfile, Bid, Job, Market, MarketError

OPS = (
    "agent-register",
    "job-post",
    "matches",
    "bid",
    "award",
    "start",
    "submit",
    "approve",
    "dispute",
    "resolve",
    "jobs",
    "agents",
    "payouts",
    *connect.COMMANDS,
)


def load(path: str) -> Market:
    m = Market()
    try:
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        return m
    if not isinstance(doc, dict) or "jobs" not in doc:
        raise MarketError(f"{path}: not an agent-work store")
    m.agents = {k: AgentProfile(**v) for k, v in doc["agents"].items()}
    m.jobs = {k: Job(**v) for k, v in doc["jobs"].items()}
    m.bids = {k: Bid(**v) for k, v in doc["bids"].items()}
    m.platform_revenue = float(doc.get("platform_revenue", 0))
    m._ids = itertools.count(int(doc.get("next_id", 1)))
    return m


def save(m: Market, path: str):
    next_id = next(m._ids)
    m._ids = itertools.count(next_id)
    doc = {
        "agents": {k: asdict(v) for k, v in m.agents.items()},
        "jobs": {k: asdict(v) for k, v in m.jobs.items()},
        "bids": {k: asdict(v) for k, v in m.bids.items()},
        "platform_revenue": m.platform_revenue,
        "next_id": next_id,
    }
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    os.replace(tmp, path)


def add_ops(sub):
    store = os.environ.get("AGENT_WORK_STORE", "market.json")
    p = sub.add_parser("agent-register", help="list an agent for hire")
    p.add_argument("name")
    p.add_argument("--skills", nargs="+", required=True)
    p.add_argument("--price", type=float, required=True, help="typical price per job, USD")
    p.add_argument("--eta-hours", type=float, required=True)
    p = sub.add_parser("job-post", help="post a job with a budget and a deadline")
    p.add_argument("client")
    p.add_argument("title")
    p.add_argument("--skills", nargs="+", required=True)
    p.add_argument("--budget", type=float, required=True)
    p.add_argument("--deadline-hours", type=float, required=True)
    sub.add_parser("matches", help="rank agents for a job").add_argument("job_id")
    p = sub.add_parser("bid", help="an agent bids on an open job")
    p.add_argument("job_id")
    p.add_argument("agent")
    p.add_argument("amount", type=float)
    sub.add_parser("award", help="accept a bid: the amount goes into escrow").add_argument("bid_id")
    sub.add_parser("start", help="the agent starts work").add_argument("job_id")
    p = sub.add_parser("submit", help="the agent hands in the work")
    p.add_argument("job_id")
    p.add_argument("--deliverable", required=True, help="link to or summary of the work")
    p = sub.add_parser("approve", help="the client accepts: escrow releases, minus the platform fee")
    p.add_argument("job_id")
    p.add_argument("--rating", type=int, required=True, help="1-5 stars")
    p.add_argument("--late", action="store_true")
    sub.add_parser("dispute", help="the client contests the submitted work").add_argument("job_id")
    p = sub.add_parser("resolve", help="the operator settles a dispute")
    p.add_argument("job_id")
    p.add_argument("--for", dest="winner", choices=["agent", "client"], required=True)
    p.add_argument("--rating", type=int, default=1)
    sub.add_parser("jobs", help="every job and its state")
    sub.add_parser("agents", help="agents by rating and reliability")
    sub.add_parser("payouts", help="what to settle: agent earnings, escrow held, platform revenue")
    connect.add_commands(sub)
    for name in OPS:
        sub.choices[name].add_argument("--store", default=store)


def _job(m: Market, job_id: str) -> Job:
    if job_id not in m.jobs:
        raise MarketError(f"no job {job_id!r}")
    return m.jobs[job_id]


def run_ops(a) -> int:
    if a.cmd in connect.COMMANDS:
        return connect.run_command(a, _earned, "agent-work")
    try:
        m = load(a.store)
        _run(m, a)
        save(m, a.store)
        return 0
    except MarketError as e:
        print(f"refused: {e}")
        return 1


def _run(m: Market, a):
    c = a.cmd
    if c == "agent-register":
        p = m.register_agent(a.name, a.skills, a.price, a.eta_hours)
        print(f"registered {p.name}: {', '.join(p.skills)} at ${p.price:,.2f}, {p.eta_hours:g}h")
    elif c == "job-post":
        j = m.post_job(a.client, a.title, a.skills, a.budget, a.deadline_hours)
        print(f"{j.job_id} posted: {j.title} (${j.budget:,.2f}, {j.deadline_hours:g}h)")
    elif c == "matches":
        _job(m, a.job_id)
        ranked = m.match(a.job_id)
        for name, score in ranked:
            p = m.agents[name]
            print(f"{score:.3f}  {name:<20} {p.rating:.2f}* ${p.price:,.2f} {p.eta_hours:g}h")
        if not ranked:
            print("no agent covers this job's skills within the deadline")
    elif c == "bid":
        _job(m, a.job_id)
        b = m.bid(a.job_id, a.agent, a.amount)
        print(f"{b.bid_id}: {b.agent} bids ${b.amount:,.2f} on {b.job_id}")
    elif c == "award":
        if a.bid_id not in m.bids:
            raise MarketError(f"no bid {a.bid_id!r}")
        j = m.award(a.bid_id)
        print(f"{j.job_id} awarded to {m.bids[a.bid_id].agent}; ${j.escrow:,.2f} held in escrow")
    elif c in ("start", "dispute"):
        _job(m, a.job_id)
        print(f"{a.job_id} is now {getattr(m, c)(a.job_id).state}")
    elif c == "submit":
        _job(m, a.job_id)
        print(f"{a.job_id} is now {m.submit(a.job_id, a.deliverable).state}; waiting for the client")
    elif c == "approve":
        held = _job(m, a.job_id).escrow
        m.approve(a.job_id, a.rating, not a.late)
        print(
            f"{a.job_id} released: ${held * (1 - PLATFORM_FEE):,.2f} to the agent, ${held * PLATFORM_FEE:,.2f} platform fee"
        )
    elif c == "resolve":
        _job(m, a.job_id)
        print(f"{a.job_id} resolved for the {a.winner}: {m.resolve(a.job_id, a.winner, a.rating).state}")
    elif c == "jobs":
        for j in m.jobs.values():
            who = m.bids[j.awarded_bid].agent if j.awarded_bid else "-"
            print(f"{j.job_id:<5}{j.state:<12}${j.budget:>10,.2f}  {who:<18}{j.title}")
        if not m.jobs:
            print("no jobs yet")
    elif c == "agents":
        for p in sorted(m.agents.values(), key=lambda p: -p.rating):
            print(
                f"{p.name:<20}{p.rating:.2f}*  {p.reliability:.0%} on time  {p.completed} done  {', '.join(p.skills)}"
            )
        if not m.agents:
            print("no agents yet")
    else:
        for p in m.agents.values():
            if p.earnings:
                print(f"pay {p.name:<20} ${p.earnings:,.2f}")
        print(f"escrow held      ${sum(j.escrow for j in m.jobs.values()):,.2f}")
        print(f"platform revenue ${m.platform_revenue:,.2f}")


def _earned(store: str) -> dict:
    """Cumulative earnings per agent (the ledger only ever adds to them)."""
    return {p.name: p.earnings for p in load(store).agents.values() if p.earnings > 0}
