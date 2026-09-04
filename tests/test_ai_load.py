"""Small repeatable capacity test for Gateway concurrency controls."""
import asyncio
import unittest
from scripts.load_test_ai_gateway import run_load

class AILoadTests(unittest.TestCase):
    def test_synthetic_load_respects_global_and_customer_limits(self):
        result = asyncio.run(run_load(60, 6, 2, 8, 2))
        self.assertTrue(result["limits_respected"])
        self.assertEqual(result["rejected"], 0)
        self.assertLessEqual(result["max_global_concurrency"], 8)
        self.assertLessEqual(result["max_customer_concurrency"], 2)

if __name__ == "__main__": unittest.main()
