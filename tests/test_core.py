import unittest

from agent_work import Market, MarketError


class Tests(unittest.TestCase):
    def setUp(self):
        self.m = Market()
        self.m.register_agent("good", ["a", "b"], 50, 1)
        self.m.register_agent("partial", ["a"], 10, 1)
        self.m.register_agent("slow", ["a", "b"], 10, 100)
        self.m.register_agent("other", ["z"], 1, 1)
        self.job = self.m.post_job("c", "t", ["a", "b"], 100, 10)

    def test_match_filters_and_ranks(self):
        names = [n for n, _ in self.m.match(self.job.job_id)]
        self.assertEqual(names[0], "good")
        self.assertNotIn("slow", names)
        self.assertNotIn("other", names)

    def test_happy_path_escrow(self):
        b = self.m.bid(self.job.job_id, "good", 80)
        self.m.award(b.bid_id)
        self.m.start(self.job.job_id)
        self.m.submit(self.job.job_id, "out")
        self.m.approve(self.job.job_id, 5)
        self.assertEqual(self.job.state, "released")
        self.assertAlmostEqual(self.m.agents["good"].earnings, 72)
        self.assertAlmostEqual(self.m.platform_revenue, 8)

    def test_invalid_transitions_and_dispute_refund(self):
        b = self.m.bid(self.job.job_id, "good", 80)
        with self.assertRaises(MarketError):
            self.m.start(self.job.job_id)
        self.m.award(b.bid_id)
        with self.assertRaises(MarketError):
            self.m.bid(self.job.job_id, "partial", 5)
        self.m.start(self.job.job_id)
        self.m.submit(self.job.job_id, "junk")
        self.m.dispute(self.job.job_id)
        self.m.resolve(self.job.job_id, "client")
        self.assertEqual(self.job.state, "refunded")
        self.assertEqual(self.m.agents["good"].earnings, 0)
        self.assertLess(self.m.agents["good"].rating, 4.0)

    def test_over_budget_bid(self):
        b = self.m.bid(self.job.job_id, "good", 500)
        with self.assertRaises(MarketError):
            self.m.award(b.bid_id)

    def _deliver(self):
        b = self.m.bid(self.job.job_id, "good", 80)
        self.m.award(b.bid_id)
        self.m.start(self.job.job_id)
        self.m.submit(self.job.job_id, "done")

    def test_ratings_must_be_1_to_5_stars(self):
        self._deliver()
        for rating in (1000, 0, -5, 4.5):
            with self.subTest(rating=rating), self.assertRaises(MarketError):
                self.m.approve(self.job.job_id, rating)
        self.assertEqual(self.m.jobs[self.job.job_id].state, "submitted")
        self.assertEqual(self.m.agents["good"].ratings, [])

    def test_no_bidding_on_your_own_job_and_no_junk_bids(self):
        self.m.register_agent("c", ["a", "b"], 10, 1)
        with self.assertRaises(MarketError):
            self.m.bid(self.job.job_id, "c", 50)
        for amount in (float("nan"), -80, 0):
            with self.subTest(amount=amount), self.assertRaises(MarketError):
                self.m.bid(self.job.job_id, "good", amount)

    def test_reregistering_cannot_reset_a_reputation(self):
        self._deliver()
        self.m.approve(self.job.job_id, 1)
        with self.assertRaises(MarketError):
            self.m.register_agent("good", ["a"], 50, 1)
        self.assertEqual(self.m.agents["good"].ratings, [1])

    def test_zero_budget_jobs_are_rejected(self):
        with self.assertRaises(MarketError):
            self.m.post_job("c", "t", ["a"], 0, 10)


if __name__ == "__main__":
    unittest.main()
