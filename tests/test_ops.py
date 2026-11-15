import contextlib
import io
import os
import tempfile
import unittest

from agent_work.__main__ import main
from agent_work.ops import load


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class MarketOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = ["--store", os.path.join(self.tmp.name, "market.json")]

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, *argv):
        code, out = run(*argv, *self.s)
        self.assertEqual(code, 0, out)
        return out

    def hire(self):
        self.ok("agent-register", "scribe", "--skills", "writing", "seo", "--price", "80", "--eta-hours", "6")
        self.ok("job-post", "acme", "3 SEO posts", "--skills", "writing", "--budget", "120", "--deadline-hours", "12")
        self.assertIn("scribe", self.ok("matches", "J1"))
        self.ok("bid", "J1", "scribe", "100")
        self.assertIn("$100.00 held in escrow", self.ok("award", "B2"))
        self.ok("start", "J1")
        self.ok("submit", "J1", "--deliverable", "https://example.com/posts")

    def test_hire_deliver_approve_pays_agent_and_platform(self):
        self.hire()
        self.assertIn("$90.00 to the agent, $10.00 platform fee", self.ok("approve", "J1", "--rating", "5"))
        m = load(self.s[1])  # every command is a fresh process in real use: state must come from the store
        self.assertEqual((m.agents["scribe"].earnings, m.platform_revenue, m.jobs["J1"].escrow), (90.0, 10.0, 0.0))
        self.assertIn("pay scribe", self.ok("payouts"))
        self.assertEqual(run("approve", "J1", "--rating", "5", *self.s)[0], 1)  # cannot be paid twice

    def test_dispute_resolved_for_the_client_refunds_and_dents_the_rating(self):
        self.hire()
        self.ok("dispute", "J1")
        self.assertIn("refunded", self.ok("resolve", "J1", "--for", "client"))
        m = load(self.s[1])
        self.assertEqual((m.agents["scribe"].earnings, m.platform_revenue), (0.0, 0.0))
        self.assertLess(m.agents["scribe"].rating, 4.0)

    def test_ids_never_collide_after_a_restart(self):
        self.ok("job-post", "a", "one", "--skills", "x", "--budget", "10", "--deadline-hours", "1")
        self.ok("job-post", "a", "two", "--skills", "x", "--budget", "10", "--deadline-hours", "1")
        self.assertEqual(sorted(load(self.s[1]).jobs), ["J1", "J2"])

    def test_bad_requests_are_refused_without_corrupting_the_store(self):
        self.ok("agent-register", "scribe", "--skills", "w", "--price", "80", "--eta-hours", "6")
        for argv in (
            ["agent-register", "scribe", "--skills", "w", "--price", "1", "--eta-hours", "1"],  # duplicate
            ["job-post", "a", "t", "--skills", "w", "--budget", "-5", "--deadline-hours", "1"],
            ["matches", "J9"],
            ["award", "B9"],
            ["bid", "J9", "scribe", "5"],
        ):
            with self.subTest(argv=argv):
                self.assertEqual(run(*argv, *self.s)[0], 1)
        self.assertEqual(load(self.s[1]).agents["scribe"].price, 80)


if __name__ == "__main__":
    unittest.main()
