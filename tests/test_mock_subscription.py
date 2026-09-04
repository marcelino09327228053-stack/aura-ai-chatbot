"""Mock successful-payment activation tests."""
import tempfile
import unittest
from pathlib import Path
from app.database import subscription_repository
from app.database.connection import init_db
from app.infrastructure.database import sqlite_backend
from app.services.mock_payment_service import process_successful_payment

class MockSubscriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(tempfile.gettempdir()) / "aura_mock_subscription_test.db"; cls.db_path.unlink(missing_ok=True)
        if sqlite_backend._conn is not None: sqlite_backend._conn.close()
        sqlite_backend._conn = None; sqlite_backend.SQLITE_PATH = str(cls.db_path); init_db()
    @classmethod
    def tearDownClass(cls):
        if sqlite_backend._conn is not None: sqlite_backend._conn.close(); sqlite_backend._conn = None
        cls.db_path.unlink(missing_ok=True)
    def setUp(self):
        conn = sqlite_backend.get_connection(); conn.cursor().execute("DELETE FROM mock_payment_events")
        conn.cursor().execute("""UPDATE subscriptions SET plan='free', status='inactive', billing_cycle_start=NULL, billing_cycle_end=NULL, expires_at=NULL, plan_price_minor=0, monthly_ai_allowance_minor=0, ai_usage_consumed_minor=0 WHERE company_id=1"""); conn.commit()
    def test_success_event_activates_test_plan_and_assigns_allowance(self):
        self.assertEqual(subscription_repository.get_subscription_by_company(1)["status"], "inactive")
        result = process_successful_payment("mock-pay-success-001", 1, "test"); after = result["subscription"]
        self.assertFalse(result["duplicate"]); self.assertEqual(result["event"]["amount_minor"], 150000); self.assertEqual(result["event"]["status"], "completed")
        self.assertEqual(after["status"], "active"); self.assertEqual(after["monthly_ai_allowance_minor"], 50000); self.assertEqual(after["remaining_allowance_minor"], 50000)
        self.assertIsNotNone(after["billing_cycle_start"]); self.assertIsNotNone(after["billing_cycle_end"])
    def test_duplicate_event_is_replayed_without_resetting_allowance(self):
        first = process_successful_payment("mock-pay-duplicate", 1, "test"); subscription_repository.deduct_allowance(1, 12)
        second = process_successful_payment("mock-pay-duplicate", 1, "test")
        self.assertFalse(first["duplicate"]); self.assertTrue(second["duplicate"])
        self.assertEqual(first["subscription"]["billing_cycle_start"], second["subscription"]["billing_cycle_start"])
        self.assertEqual(second["subscription"]["ai_usage_consumed_minor"], 12); self.assertEqual(second["subscription"]["remaining_allowance_minor"], 49988)

if __name__ == "__main__": unittest.main()
