"""Managed AI Gateway subscription, isolation, and idempotency tests."""

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
        if sqlite_backend._conn is not None:
            sqlite_backend._conn.close()
        sqlite_backend._conn = None
        sqlite_backend.SQLITE_PATH = str(cls.db_path)
        init_db()
        os.environ["GEMINI_API_KEY"] = "server-only-test-key"

    @classmethod
    def tearDownClass(cls):
        os.environ["GEMINI_API_KEY"] = ""
        if sqlite_backend._conn is not None:
            sqlite_backend._conn.close()
            sqlite_backend._conn = None
        cls.db_path.unlink(missing_ok=True)

    def setUp(self):
        subscription_repository.activate_subscription(1, "pro", 10)

    def test_subscription_activation_enables_managed_ai_and_records_usage(self):
        answer = ai_service.AIResult("Gateway answer", input_tokens=120, output_tokens=40)
        with patch("app.services.ai_service.generate_reply", return_value=answer):
            result = asyncio.run(
                ai_gateway.generate("hello", 1, None, request_id="gateway-test-1")
            )
        self.assertEqual(result["reply"], "Gateway answer")
        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(result["input_tokens"], 120)
        self.assertEqual(result["allowance_deducted"], 1)
        status = subscription_service.get_subscription_status(1)
        self.assertEqual(status["ai_usage_consumed"], 1)
        self.assertEqual(status["remaining_allowance"], 9)

    def test_request_id_replay_does_not_charge_twice(self):
        with patch(
            "app.services.ai_service.generate_reply",
            return_value=ai_service.AIResult("once", 10, 10),
        ) as provider:
            first = asyncio.run(ai_gateway.generate("hello", 1, None, "same-request"))
            replay = asyncio.run(ai_gateway.generate("hello", 1, None, "same-request"))
        self.assertFalse(first["idempotent_replay"])
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(
            subscription_service.get_subscription_status(1)["ai_usage_consumed"], 1
        )

    def test_request_id_cannot_cross_customer_boundary(self):
        conn = sqlite_backend.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO companies (company_name, company_profile) VALUES (?, '')",
            ("Second customer",),
        )
        company_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO subscriptions (company_id, plan, status) VALUES (?, 'pro', 'active')",
            (company_id,),
        )
        conn.commit()
        subscription_repository.activate_subscription(company_id, "pro", 10)
        with patch(
            "app.services.ai_service.generate_reply",
            return_value=ai_service.AIResult("isolated", 10, 10),
        ):
            asyncio.run(ai_gateway.generate("hello", 1, None, "tenant-bound-request"))
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    ai_gateway.generate(
                        "hello", company_id, None, "tenant-bound-request"
                    )
                )
        self.assertEqual(raised.exception.status_code, 409)

    def test_inactive_or_exhausted_subscription_is_blocked(self):
        subscription_repository.activate_subscription(1, "pro", 1)
        with patch(
            "app.services.ai_service.generate_reply",
            return_value=ai_service.AIResult("last credit", 10, 10),
        ):
            asyncio.run(ai_gateway.generate("hello", 1, None, "last-credit"))
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(ai_gateway.generate("again", 1, None, "over-limit"))
        self.assertEqual(raised.exception.status_code, 402)


if __name__ == "__main__":
    unittest.main()
