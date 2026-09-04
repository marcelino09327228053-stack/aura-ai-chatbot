"""Managed AI Gateway subscription, cost, isolation, and idempotency tests."""
import asyncio
import os
import tempfile
import unittest
from contextlib import suppress
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from app.database.connection import init_db
from app.database import subscription_repository
from app.infrastructure.database import sqlite_backend
from app.services import ai_gateway, ai_service, subscription_service
from app.services.ai_provider_router import RouteCandidate, provider_health
from app.services.ai_traffic import TrafficManager

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
        provider_health.reset()
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
        with patch.object(ai_gateway, "AI_GATEWAY_RETRY_BASE_SECONDS", 0), patch.object(ai_gateway, "AI_GATEWAY_RETRY_JITTER_SECONDS", 0), self.assertRaises(HTTPException) as raised: self.run_gateway("hello", 1, "missing-usage", "plain response")
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(subscription_service.get_subscription_status(1)["ai_usage_consumed_minor"], 0)

    def test_http_429_retry_after_is_respected(self):
        candidate = RouteCandidate("gemini", "test-model", 0, ai_gateway.AI_MODEL_COSTS_USD["test-model"])
        # Use an explicit coroutine to make the first call fail and the retry succeed.
        calls = 0
        async def provider_call(*args):
            nonlocal calls
            calls += 1
            if calls == 1: raise ai_service.ProviderHTTPError(429, "busy", 2.5)
            return ai_service.AIResult("ok", 10, 10)
        with patch("app.services.ai_gateway.route_candidates", return_value=[candidate]), patch("app.services.ai_gateway._call_provider", side_effect=provider_call), patch("app.services.ai_gateway.asyncio.sleep", new_callable=lambda: unittest.mock.AsyncMock()) as sleeper:
            result = asyncio.run(ai_gateway.generate("hello", 1, None, "retry-after-test"))
        self.assertEqual(result["reply"], "ok")
        sleeper.assert_awaited_once_with(2.5)

    def test_rate_limited_primary_falls_back_and_enters_cooldown(self):
        candidates = [RouteCandidate("gemini", "test-model", 0, {}), RouteCandidate("openai", "test-model", 1, {})]
        async def provider_call(prompt, provider, model):
            if provider == "gemini": raise ai_service.ProviderHTTPError(429, "busy", 10)
            return ai_service.AIResult("fallback ok", 10, 10)
        with patch("app.services.ai_gateway.route_candidates", return_value=candidates), patch("app.services.ai_gateway._call_provider", side_effect=provider_call):
            result = asyncio.run(ai_gateway.generate("hello", 1, None, "fallback-test"))
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(provider_health.status("gemini")["state"], "rate_limited")

    def test_provider_in_cooldown_is_skipped_when_alternative_exists(self):
        os.environ["OPENAI_API_KEY"] = "server-openai-test-key"
        provider_health.mark_cooldown("gemini", "temporarily_unavailable", 10)
        try:
            with patch("app.services.ai_service.get_server_model", return_value="test-model"):
                candidates = __import__("app.services.ai_provider_router", fromlist=["route_candidates"]).route_candidates()
            self.assertNotIn("gemini", [item.provider for item in candidates])
            self.assertIn("openai", [item.provider for item in candidates])
        finally: os.environ["OPENAI_API_KEY"] = ""

    def test_all_providers_unavailable_records_failure_without_charge(self):
        with patch("app.services.ai_gateway.route_candidates", return_value=[]), self.assertRaises(HTTPException) as raised:
            asyncio.run(ai_gateway.generate("hello", 1, None, "all-unavailable"))
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(subscription_service.get_subscription_status(1)["ai_usage_consumed_minor"], 0)
        self.assertEqual(__import__("app.database.ai_gateway_repository", fromlist=["get_request"]).get_request("all-unavailable")["status"], "failed")

    def test_concurrent_request_waits_in_queue(self):
        async def scenario():
            manager = TrafficManager(); manager.global_limit = manager.customer_limit = 1
            manager._global = asyncio.Semaphore(1); manager._customers = {}
            gate = asyncio.Event(); started = asyncio.Event(); call_count = 0
            async def provider_call(*args):
                nonlocal call_count
                call_count += 1
                if call_count == 1: started.set(); await gate.wait()
                return ai_service.AIResult("ok", 10, 10)
            candidate = RouteCandidate("gemini", "test-model", 0, {})
            with patch("app.services.ai_gateway.get_traffic_manager", return_value=manager), patch("app.services.ai_gateway.route_candidates", return_value=[candidate]), patch("app.services.ai_gateway._call_provider", side_effect=provider_call):
                first = asyncio.create_task(ai_gateway.generate("one", 1, None, "concurrent-one")); await started.wait()
                second = asyncio.create_task(ai_gateway.generate("two", 1, None, "concurrent-two")); await asyncio.sleep(0.01)
                self.assertEqual(manager.snapshot()["queue_size"], 1)
                gate.set(); await asyncio.gather(first, second)
        asyncio.run(scenario())
        self.assertEqual(subscription_service.get_subscription_status(1)["ai_usage_consumed_minor"], 2)

    def test_queue_timeout_returns_temporary_error(self):
        async def scenario():
            manager = TrafficManager(); manager.timeout = 0.02; manager._global = asyncio.Semaphore(1); manager._customers = {}; manager.customer_limit = 1
            gate = asyncio.Event(); started = asyncio.Event()
            async def provider_call(*args): started.set(); await gate.wait(); return ai_service.AIResult("ok", 10, 10)
            candidate = RouteCandidate("gemini", "test-model", 0, {})
            with patch("app.services.ai_gateway.get_traffic_manager", return_value=manager), patch("app.services.ai_gateway.route_candidates", return_value=[candidate]), patch("app.services.ai_gateway._call_provider", side_effect=provider_call):
                first = asyncio.create_task(ai_gateway.generate("one", 1, None, "queue-one")); await started.wait()
                with self.assertRaises(HTTPException) as raised: await ai_gateway.generate("two", 1, None, "queue-two")
                self.assertEqual(raised.exception.status_code, 503); gate.set(); await first
        asyncio.run(scenario())

    def test_per_customer_queue_limit_prevents_monopoly(self):
        async def scenario():
            manager = TrafficManager(); manager.customer_queue_limit = 1
            manager._global = asyncio.Semaphore(1); manager._customers = {}
            gate = asyncio.Event(); entered = asyncio.Event()
            async def holder():
                async with manager.slot(1): entered.set(); await gate.wait()
            async def queued():
                async with manager.slot(1): pass
            first = asyncio.create_task(holder()); await entered.wait()
            second = asyncio.create_task(queued()); await asyncio.sleep(0)
            with self.assertRaises(HTTPException) as raised:
                async with manager.slot(1): pass
            self.assertEqual(raised.exception.status_code, 429)
            second.cancel()
            with suppress(asyncio.CancelledError): await second
            gate.set(); await first
        asyncio.run(scenario())

if __name__ == "__main__": unittest.main()
