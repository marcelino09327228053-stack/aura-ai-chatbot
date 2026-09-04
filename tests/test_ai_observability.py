"""AI Gateway structured metrics tests."""
import unittest
from app.services.ai_observability import emit, metrics_snapshot, prometheus_text, reset_metrics

class AIObservabilityTests(unittest.TestCase):
    def setUp(self): reset_metrics()
    def test_metrics_capture_events_latency_and_queue_gauge(self):
        emit("request_success", latency_ms=125.5, queue_size=3, provider="gemini")
        snapshot = metrics_snapshot()
        self.assertEqual(snapshot["counters"]["request_success"], 1)
        self.assertEqual(snapshot["gauges"]["queue_size"], 3)
        output = prometheus_text()
        self.assertIn('event="request_success"', output)
        self.assertIn("aura_ai_gateway_request_latency_ms_sum 125.5", output)
    def test_secret_named_fields_are_not_serialized(self):
        emit("provider_selected", api_key="never-log", authorization="secret", provider="openai")
        self.assertNotIn("never-log", prometheus_text())

if __name__ == "__main__": unittest.main()
