"""Provider transport contract tests without external API charges."""
from datetime import datetime, timedelta, timezone
from email.message import Message
from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from app.services import ai_gateway, ai_service

class ProviderContractTests(unittest.TestCase):
    def http_error(self, retry_after: str):
        headers = Message(); headers["Retry-After"] = retry_after
        return HTTPError("https://provider.invalid", 429, "rate limited", headers, BytesIO(b'{"error":"rate limited"}'))

    def test_rest_adapter_preserves_numeric_retry_after(self):
        with patch("app.services.ai_service.urlopen", side_effect=self.http_error("7")):
            with self.assertRaises(ai_service.ProviderHTTPError) as raised:
                ai_service._post_json("https://provider.invalid", {}, {})
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.retry_after, 7)

    def test_rest_adapter_supports_http_date_retry_after(self):
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=5)
        with patch("app.services.ai_service.urlopen", side_effect=self.http_error(retry_at.strftime("%a, %d %b %Y %H:%M:%S GMT"))):
            with self.assertRaises(ai_service.ProviderHTTPError) as raised:
                ai_service._post_json("https://provider.invalid", {}, {})
        self.assertGreaterEqual(raised.exception.retry_after, 3)
        self.assertLessEqual(raised.exception.retry_after, 5)

    def test_gateway_recognizes_sdk_style_429_and_headers(self):
        class SDKError(RuntimeError):
            status_code = 429
            response = type("Response", (), {"headers": {"Retry-After": "3"}})()
        error = SDKError("provider throttled")
        self.assertEqual(ai_gateway._error_status(error), 429)
        self.assertEqual(ai_gateway._retry_after(error), 3)

if __name__ == "__main__": unittest.main()
