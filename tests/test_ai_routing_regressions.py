"""Regression tests for managed provider routing and deploy-safe defaults."""

import os
import unittest
from unittest.mock import patch

from app.services import ai_provider_router, ai_service
from app.services.ai_provider_router import provider_health


class AIRoutingRegressionTests(unittest.TestCase):
    def setUp(self):
        provider_health.reset()

    def test_provider_without_metering_is_skipped_before_api_call(self):
        with patch.object(ai_provider_router, "AI_GATEWAY_PROVIDER_ORDER", ("gemini", "openai")), \
             patch.object(ai_provider_router, "AI_MODEL_COSTS_USD", {
                 "openai-test": {"input_per_million": 1.0, "output_per_million": 2.0}
             }), \
             patch("app.services.ai_service.get_server_api_key", return_value="test-key"), \
             patch("app.services.ai_service.get_server_model", side_effect=lambda provider: {
                 "gemini": "gemini-unmetered", "openai": "openai-test"
             }[provider]):
            candidates = ai_provider_router.route_candidates()
        self.assertEqual([item.provider for item in candidates], ["openai"])

    def test_invalid_or_negative_metering_is_rejected(self):
        for pricing in ({}, {"input_per_million": 1}, {"input_per_million": -1, "output_per_million": 1}, {"input_per_million": "bad", "output_per_million": 1}):
            self.assertFalse(ai_provider_router._valid_pricing(pricing))

    def test_duplicate_provider_order_does_not_duplicate_api_attempts(self):
        with patch.object(ai_provider_router, "AI_GATEWAY_PROVIDER_ORDER", ("gemini", "gemini")), \
             patch.object(ai_provider_router, "AI_MODEL_COSTS_USD", {
                 "test-model": {"input_per_million": 1.0, "output_per_million": 1.0}
             }), \
             patch("app.services.ai_service.get_server_api_key", return_value="test-key"), \
             patch("app.services.ai_service.get_server_model", return_value="test-model"):
            candidates = ai_provider_router.route_candidates()
        self.assertEqual(len(candidates), 1)

    def test_groq_default_uses_current_supported_model(self):
        old = os.environ.pop("GROQ_MODEL", None)
        try:
            self.assertEqual(ai_service.get_server_model("groq"), "openai/gpt-oss-120b")
        finally:
            if old is not None:
                os.environ["GROQ_MODEL"] = old


if __name__ == "__main__":
    unittest.main()
