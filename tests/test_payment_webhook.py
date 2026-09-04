"""Signed, idempotent subscription payment webhook tests."""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from fastapi import HTTPException
from app.database.connection import init_db
from app.infrastructure.database import sqlite_backend
from app.services.payment_webhook_service import process_event

class PaymentWebhookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(tempfile.gettempdir()) / "aura_payment_webhook_test.db"; cls.path.unlink(missing_ok=True)
        if sqlite_backend._conn is not None: sqlite_backend._conn.close()
        sqlite_backend._conn=None; sqlite_backend.SQLITE_PATH=str(cls.path); init_db()
        os.environ["PAYMENT_WEBHOOK_SECRET"]="webhook-test-secret"; os.environ["PAYMENT_WEBHOOK_PROVIDER"]="testpay"
    @classmethod
    def tearDownClass(cls):
        os.environ.pop("PAYMENT_WEBHOOK_SECRET",None); os.environ.pop("PAYMENT_WEBHOOK_PROVIDER",None)
        if sqlite_backend._conn is not None: sqlite_backend._conn.close(); sqlite_backend._conn=None
        cls.path.unlink(missing_ok=True)
    def payload(self, event_id="pay-001"):
        return {"event_id":event_id,"provider":"testpay","company_id":1,"plan":"test",
                "amount_minor":150000,"currency":"PHP","status":"succeeded",
                "occurred_at":datetime.now(timezone.utc).isoformat()}
    def signed(self,payload):
        raw=json.dumps(payload).encode(); sig=hmac.new(b"webhook-test-secret",raw,hashlib.sha256).hexdigest(); return raw,sig
    def test_signed_success_activates_and_duplicate_does_not_reset_usage(self):
        raw,sig=self.signed(self.payload()); first=process_event(raw,sig)
        self.assertTrue(first["activated"]); self.assertFalse(first["duplicate"])
        conn=sqlite_backend.get_connection(); conn.cursor().execute("UPDATE subscriptions SET ai_usage_consumed_minor=12 WHERE company_id=1"); conn.commit()
        second=process_event(raw,sig); self.assertTrue(second["duplicate"])
        self.assertEqual(second["subscription"]["ai_usage_consumed_minor"],12)
    def test_invalid_signature_is_rejected(self):
        raw,_=self.signed(self.payload("pay-bad-signature"))
        with self.assertRaises(HTTPException) as raised: process_event(raw,"wrong")
        self.assertEqual(raised.exception.status_code,401)
    def test_wrong_amount_is_rejected(self):
        payload=self.payload("pay-wrong-amount"); payload["amount_minor"]=1; raw,sig=self.signed(payload)
        with self.assertRaises(HTTPException) as raised: process_event(raw,sig)
        self.assertEqual(raised.exception.status_code,400)

if __name__ == "__main__": unittest.main()
