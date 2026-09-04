"""Managed AI Gateway subscription, cost, isolation, and idempotency tests."""
import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from app.database.connection import init_db
from app.database import subscription_repository
from app.infrastructure.database import sqlite_backend
from app.services import ai_gateway, ai_service, subscription_service

class ManagedAIGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(tempfile.gettempdir()) / "aura_managed_gateway_test.db"
        cls.db_path.unlink(missing_ok=True)
        if sqlite_backend._conn is not None: sqlite_backend._conn.close()
        sqlite_backend._conn = None
        sqlite_backend.SQLITE_PATH = str(cls.db_path)
        init_db()
        os.environ["GEMINI_API_KEY"] = "server-only-test-key"
        cls.old_pricing = dict(ai_gateway.AI_MODEL_COSTS_USD)
        ai_gateway.AI_MODEL_COSTS_USD["test-model"] = {"input_per_million": 1.0, "output_per_million": 2.0}

    @classmethod
    def tearDownClass(cls):
        os.environ["GEMINI_API_KEY"] = ""
        ai_gateway.AI_MODEL_COSTS_USD.clear(); ai_gateway.AI_MODEL_COSTS_USD.update(cls.old_pricing)
        if sqlite_backend._conn is not None: sqlite_backend._conn.close(); sqlite_backend._conn = None
        cls.db_path.unlink(missing_ok=True)

    def setUp(self):
        subscription_repository.activate_subscription(1, "test", 150000, 50000, "PHP")

    def run_gateway(self, prompt, company_id, request_id, answer):
        with patch("app.services.ai_service.get_server_model", return_value="test-model"), patch("app.services.ai_service.generate_reply", return_value=answer) as provider:
            result = asyncio.run(ai_gateway.generate(prompt, company_id, None, request_id))
        return result, provider

    def test_actual_cost_is_deducted_from_monthly_allowance(self):
        result, _ = self.run_gateway("hello", 1, "gateway-cost-test", ai_service.AIResult("Gateway answer", 1000, 500))
        self.assertEqual(result["provider_cost_usd"], 0.002)
        self.assertEqual(result["allowance_deducted_minor"], 12)
        status = subscription_service.get_subscription_status(1)
        self.assertEqual(status["ai_usage_consumed_minor"], 12)
        self.assertEqual(status["remaining_allowance_minor"], 49988)

    def test_request_id_replay_does_not_charge_twice(self):
        answer = ai_service.AIResult("once", 1000, 500)
        with patch("app.services.ai_service.get_server_model", return_value="test-model"), patch("app.services.ai_service.generate_reply", return_value=answer) as provider:
            first = asyncio.run(ai_gateway.generate("hello", 1, None, "same-request"))
            replay = asyncio.run(ai_gateway.generate("hello", 1, None, "same-request"))
        self.assertFalse(first["idempotent_replay"]); self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(subscription_service.get_subscription_status(1)["ai_usage_consumed_minor"], 12)

    def test_request_id_cannot_cross_customer_boundary(self):
        conn = sqlite_backend.get_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO companies (company_name, company_profile) VALUES (?, '')", ("Second customer",)); company_id = cursor.lastrowid
        cursor.execute("INSERT INTO subscriptions (company_id, plan, status) VALUES (?, 'test', 'inactive')", (company_id,)); conn.commit()
        subscription_repository.activate_subscription(company_id, "test", 150000, 50000, "PHP")
        self.run_gateway("hello", 1, "tenant-bound-request", ai_service.AIResult("isolated", 10, 10))
        with self.assertRaises(HTTPException) as raised: asyncio.run(ai_gateway.generate("hello", company_id, None, "tenant-bound-request"))
        self.assertEqual(raised.exception.status_code, 409)

    def test_inactive_subscription_is_blocked_before_provider_call(self):
        conn = sqlite_backend.get_connection(); conn.cursor().execute("UPDATE subscriptions SET status='inactive' WHERE company_id=1"); conn.commit()
        with patch("app.services.ai_service.generate_reply") as provider, self.assertRaises(HTTPException) as raised: asyncio.run(ai_gateway.generate("hello", 1, None, "inactive-test"))
        self.assertEqual(raised.exception.status_code, 402); provider.assert_not_called()

    def test_paid_usage_stops_when_allowance_would_be_exceeded(self):
        conn = sqlite_backend.get_connection(); conn.cursor().execute("UPDATE subscriptions SET ai_usage_consumed_minor=49999 WHERE company_id=1"); conn.commit()
        with self.assertRaises(HTTPException) as raised: self.run_gateway("hello", 1, "exhausted-test", ai_service.AIResult("costs twelve", 1000, 500))
        self.assertEqual(raised.exception.status_code, 402)
        self.assertEqual(subscription_service.get_subscription_status(1)["remaining_allowance_minor"], 1)

    def test_missing_provider_usage_cannot_charge_allowance(self):
        with self.assertRaises(HTTPException) as raised: self.run_gateway("hello", 1, "missing-usage", "plain response")
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(subscription_service.get_subscription_status(1)["ai_usage_consumed_minor"], 0)

if __name__ == "__main__": unittest.main()
