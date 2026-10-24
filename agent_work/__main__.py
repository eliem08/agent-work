import argparse
import sys

from .core import Market


def demo():
    m = Market()
    m.register_agent("scrubber-pro", ["data-cleaning", "csv", "dedupe"], price=60, eta_hours=2)
    m.register_agent("cheap-cleaner", ["data-cleaning"], price=20, eta_hours=6)
    m.register_agent("copy-bot", ["copywriting"], price=30, eta_hours=1)
    job = m.post_job("acme", "Dedupe 40k-row CRM export", ["data-cleaning", "dedupe"], budget=80, deadline_hours=4)
    print(f"Job {job.job_id}: {job.title} (budget ${job.budget}, {job.deadline_hours}h)")
    for name, score in m.match(job.job_id):
        print(f"  candidate {name:<14} score {score:.3f}")
    bid = m.bid(job.job_id, "scrubber-pro", 60)
    m.award(bid.bid_id)
    print(f"  awarded to scrubber-pro, escrow ${job.escrow}")
    m.start(job.job_id)
    m.submit(job.job_id, "s3://acme/crm-clean.csv")
    m.approve(job.job_id, rating=5)
    a = m.agents["scrubber-pro"]
    print(f"  released: agent earned ${a.earnings:.2f}, platform ${m.platform_revenue:.2f}, rating {a.rating:.2f}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="agent-work")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    ap.parse_args(argv)
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
