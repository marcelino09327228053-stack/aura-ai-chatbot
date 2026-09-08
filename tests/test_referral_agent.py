"""Referral attribution, commission and persistent AI-credit behavior."""
import tempfile
import unittest
from pathlib import Path

from app.database.connection import init_db
from app.database import payment_event_repository, subscription_repository, user_repository, company_repository
from app.infrastructure.database import sqlite_backend
from app.referrals import repository, service


class ReferralAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(tempfile.gettempdir()) / "mb_referral_agent_test.db"
        cls.path.unlink(missing_ok=True)
        if sqlite_backend._conn is not None: sqlite_backend._conn.close()
        sqlite_backend._conn = None; sqlite_backend.SQLITE_PATH = str(cls.path); init_db()

    @classmethod
    def tearDownClass(cls):
        if sqlite_backend._conn is not None: sqlite_backend._conn.close(); sqlite_backend._conn = None
        cls.path.unlink(missing_ok=True)

    def setUp(self):
        conn=sqlite_backend.get_connection(); c=conn.cursor()
        for table in ("referral_payout_items","referral_payouts","referral_commission_ledger",
                      "customer_referral_attributions","referral_clicks","referral_agents",
                      "payment_webhook_events"):
            c.execute(f"DELETE FROM {table}")
        c.execute("DELETE FROM companies WHERE id!=1"); c.execute("DELETE FROM users")
        c.execute("DELETE FROM platform_pricing_rules")
        c.execute("""INSERT INTO platform_pricing_rules(monthly_platform_price_minor,
          initial_ai_credit_minor,minimum_ai_topup_minor,referral_commission_minor,
          ai_usage_markup_bps,currency,created_by) VALUES(100000,50000,50000,30000,0,'PHP','test')""")
        c.execute("UPDATE subscriptions SET plan='free',status='inactive',monthly_ai_allowance_minor=0,ai_usage_consumed_minor=0,ai_credit_balance_minor=0 WHERE company_id=1")
        conn.commit()

    def user_company(self, email):
        user=user_repository.create_user(email,"unused-hash")
        company=company_repository.create_company(user["id"],email.split("@")[0])
        subscription_repository.create_subscription(company["id"],"free")
        return user,company

    def approved_agent(self, email="agent@example.com"):
        user,_=self.user_company(email); agent,created=repository.apply_for_agent(user["id"])
        self.assertTrue(created); agent=repository.set_agent_status(agent["id"],"approved")
        return user,agent

    def test_application_unique_code_and_signed_capture(self):
        user,agent=self.approved_agent()
        again,created=repository.apply_for_agent(user["id"])
        self.assertFalse(created); self.assertEqual(agent["referral_code"],again["referral_code"])
        token,_=service.capture_token(agent["referral_code"])
        self.assertEqual(service.agent_id_from_token(token),agent["id"])
        self.assertIsNone(service.agent_id_from_token(token+"tampered"))

    def test_first_attribution_is_permanent_and_self_referral_is_blocked(self):
        agent_user,agent=self.approved_agent(); _,agent2=self.approved_agent("agent2@example.com")
        customer,company=self.user_company("customer@example.com")
        first,created=repository.create_attribution(company["id"],customer["id"],agent["id"])
        self.assertTrue(created)
        second,created=repository.create_attribution(company["id"],customer["id"],agent2["id"])
        self.assertFalse(created); self.assertEqual(first["referral_agent_id"],second["referral_agent_id"])
        row,created=repository.create_attribution(1,agent_user["id"],agent["id"])
        self.assertFalse(created); self.assertIsNone(row)

    def test_payment_idempotency_reactivation_price_snapshot_topup_and_refund(self):
        _,agent=self.approved_agent(); customer,company=self.user_company("buyer@example.com")
        repository.create_attribution(company["id"],customer["id"],agent["id"])
        args=("pay-1","test-provider",company["id"],"test",150000,"PHP",50000,"hash-1")
        payment_event_repository.activate_from_event(*args,"initial_subscription")
        payment_event_repository.activate_from_event(*args,"initial_subscription")
        rows=repository.list_commissions(); self.assertEqual(len(rows),1); self.assertEqual(rows[0]["commission_amount_minor"],30000)
        subscription_repository.deduct_allowance(company["id"],1200)
        before=subscription_repository.get_subscription_by_company(company["id"])["remaining_ai_credit_minor"]
        payment_event_repository.activate_from_event("renew-1","test-provider",company["id"],"test",100000,"PHP",0,"hash-r","subscription_renewal")
        self.assertEqual(subscription_repository.get_subscription_by_company(company["id"])["remaining_ai_credit_minor"],before)
        repository.create_pricing_rule({"monthly_platform_price_minor":100000,"initial_ai_credit_minor":50000,
          "minimum_ai_topup_minor":50000,"referral_commission_minor":40000,"ai_usage_markup_bps":0,"currency":"PHP"},"test-owner")
        payment_event_repository.activate_from_event("renew-2","test-provider",company["id"],"test",100000,"PHP",0,"hash-r2","subscription_renewal")
        amounts=[x["commission_amount_minor"] for x in repository.list_commissions() if x["entry_type"]=="commission"]
        self.assertIn(30000,amounts); self.assertIn(40000,amounts)
        count=len(repository.list_commissions())
        payment_event_repository.activate_from_event("topup-1","test-provider",company["id"],"test",50000,"PHP",50000,"hash-t","ai_topup")
        self.assertEqual(len(repository.list_commissions()),count)
        self.assertEqual(subscription_repository.get_subscription_by_company(company["id"])["remaining_ai_credit_minor"],before+50000)
        payment_event_repository.activate_from_event("refund-1","test-provider",company["id"],"test",100000,"PHP",0,"hash-f","refund","renew-2")
        reversal=[x for x in repository.list_commissions() if x["entry_type"]=="reversal"]
        self.assertEqual(reversal[0]["commission_amount_minor"],-40000)

    def test_suspended_agent_is_isolated_from_new_commissions(self):
        _,agent=self.approved_agent(); customer,company=self.user_company("buyer2@example.com")
        repository.create_attribution(company["id"],customer["id"],agent["id"])
        repository.set_agent_status(agent["id"],"suspended")
        payment_event_repository.activate_from_event("pay-s","test-provider",company["id"],"test",100000,"PHP",0,"hash-s","subscription_renewal")
        self.assertEqual(repository.list_commissions(),[])
        self.assertIsNone(repository.dashboard_for_user(customer["id"]))
        self.assertIsNotNone(repository.dashboard_for_user(agent["user_id"]))


if __name__ == "__main__": unittest.main()
