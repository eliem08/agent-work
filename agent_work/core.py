"""Agent labour marketplace: matching, bidding, escrow and reputation."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

__all__ = ["AgentProfile", "Job", "Bid", "Market", "MarketError", "PLATFORM_FEE"]

PLATFORM_FEE = 0.10
PRIOR_RATING, PRIOR_WEIGHT = 4.0, 5  # Bayesian smoothing toward 4.0 stars


class MarketError(Exception):
    pass


@dataclass
class AgentProfile:
    name: str
    skills: list
    price: float
    eta_hours: float
    ratings: list = field(default_factory=list)
    on_time: int = 0
    completed: int = 0
    earnings: float = 0.0

    @property
    def rating(self) -> float:
        return (PRIOR_RATING * PRIOR_WEIGHT + sum(self.ratings)) / (PRIOR_WEIGHT + len(self.ratings))

    @property
    def reliability(self) -> float:
        return (self.on_time + 1) / (self.completed + 2)


@dataclass
class Job:
    job_id: str
    client: str
    title: str
    skills: list
    budget: float
    deadline_hours: float
    state: str = "open"
    awarded_bid: str | None = None
    escrow: float = 0.0
    deliverable: str | None = None


@dataclass
class Bid:
    bid_id: str
    job_id: str
    agent: str
    amount: float


TRANSITIONS = {
    "start": ("funded", "in_progress"),
    "submit": ("in_progress", "submitted"),
    "approve": ("submitted", "released"),
    "dispute": ("submitted", "disputed"),
}


class Market:
    def __init__(self):
        self.agents: dict[str, AgentProfile] = {}
        self.jobs: dict[str, Job] = {}
        self.bids: dict[str, Bid] = {}
        self.platform_revenue = 0.0
        self._ids = itertools.count(1)

    def register_agent(self, name, skills, price, eta_hours) -> AgentProfile:
        self.agents[name] = AgentProfile(name, list(skills), price, eta_hours)
        return self.agents[name]

    def post_job(self, client, title, skills, budget, deadline_hours) -> Job:
        jid = f"J{next(self._ids)}"
        self.jobs[jid] = Job(jid, client, title, list(skills), budget, deadline_hours)
        return self.jobs[jid]

    def match(self, job_id: str, top: int = 5) -> list[tuple[str, float]]:
        job = self.jobs[job_id]
        out = []
        for a in self.agents.values():
            if a.eta_hours > job.deadline_hours:
                continue
            coverage = len(set(job.skills) & set(a.skills)) / len(job.skills) if job.skills else 1
            if coverage == 0:
                continue
            price_fit = 1.0 if a.price <= job.budget else max(0.0, 1 - (a.price - job.budget) / job.budget)
            score = 0.4 * coverage + 0.2 * price_fit + 0.25 * (a.rating / 5) + 0.15 * a.reliability
            out.append((a.name, round(score, 4)))
        return sorted(out, key=lambda x: -x[1])[:top]

    def bid(self, job_id, agent, amount) -> Bid:
        job = self.jobs[job_id]
        if job.state != "open":
            raise MarketError("job not open for bids")
        if agent not in self.agents:
            raise MarketError("unknown agent")
        bid = Bid(f"B{next(self._ids)}", job_id, agent, amount)
        self.bids[bid.bid_id] = bid
        return bid

    def award(self, bid_id: str) -> Job:
        bid = self.bids[bid_id]
        job = self.jobs[bid.job_id]
        if job.state != "open":
            raise MarketError("job already awarded")
        if bid.amount > job.budget:
            raise MarketError("bid exceeds budget")
        job.awarded_bid, job.escrow, job.state = bid_id, bid.amount, "funded"
        return job

    def _move(self, job_id, action):
        job = self.jobs[job_id]
        src, dst = TRANSITIONS[action]
        if job.state != src:
            raise MarketError(f"cannot {action} a job in state {job.state!r}")
        job.state = dst
        return job

    def start(self, job_id):
        return self._move(job_id, "start")

    def submit(self, job_id, deliverable):
        job = self._move(job_id, "submit")
        job.deliverable = deliverable
        return job

    def approve(self, job_id, rating: int, on_time: bool = True):
        job = self._move(job_id, "approve")
        self._payout(job, rating, on_time)
        return job

    def dispute(self, job_id):
        return self._move(job_id, "dispute")

    def resolve(self, job_id, in_favour_of: str, rating: int = 1):
        job = self.jobs[job_id]
        if job.state != "disputed":
            raise MarketError("job not disputed")
        if in_favour_of == "agent":
            job.state = "released"
            self._payout(job, rating, True)
        else:
            job.state, job.escrow = "refunded", 0.0
            agent = self.agents[self.bids[job.awarded_bid].agent]
            agent.ratings.append(rating)
            agent.completed += 1
        return job

    def _payout(self, job, rating, on_time):
        agent = self.agents[self.bids[job.awarded_bid].agent]
        fee = job.escrow * PLATFORM_FEE
        agent.earnings += job.escrow - fee
        self.platform_revenue += fee
        job.escrow = 0.0
        agent.ratings.append(rating)
        agent.completed += 1
        agent.on_time += on_time
