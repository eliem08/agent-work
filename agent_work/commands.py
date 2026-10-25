"""Stateless commands: read a JSON request, print a JSON decision (also served by the web app)."""

import json

from .core import Market


def add_commands(sub):
    m = sub.add_parser("match", help="rank registered agents for a job")
    m.add_argument("market", help="JSON with 'agents' and a 'job'")
    m.add_argument("--top", type=int, default=5)


def run(a):
    with open(a.market, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("agents"), list) or not isinstance(data.get("job"), dict):
        raise ValueError("market must be an object with an 'agents' list and a 'job' object")
    mk = Market()
    for ag in data["agents"]:
        mk.register_agent(ag["name"], ag["skills"], float(ag["price"]), float(ag["eta_hours"]))
    j = data["job"]
    job = mk.post_job(
        j.get("client", "client"), j["title"], j["skills"], float(j["budget"]), float(j["deadline_hours"])
    )
    ranked = [{"agent": n, "score": s} for n, s in mk.match(job.job_id, a.top)]
    print(json.dumps(ranked, indent=2))
    return 0 if ranked else 1
