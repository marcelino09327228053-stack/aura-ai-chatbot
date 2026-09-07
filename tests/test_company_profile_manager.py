import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.company_profile_manager import _parse_json, _prepare_draft, review_company_profile


class CompanyProfileManagerTests(unittest.TestCase):
    def test_deduplicates_repeated_website_lines_before_ai_review(self):
        cleaned = _prepare_draft(
            "Home\nProjects\nOcean View\nProjects\nOcean View\n"
            "Phone: 123\nPhone: 123\nEmail: sales@example.com"
        )
        self.assertEqual(cleaned.count("Projects"), 1)
        self.assertEqual(cleaned.count("Ocean View"), 1)
        self.assertEqual(cleaned.count("Phone: 123"), 1)
        self.assertIn("Email: sales@example.com", cleaned)

    def test_parses_arranged_profile_missing_details_and_conflicts(self):
        result = _parse_json(
            """```json
            {
              "company_name": "MB Future Tech",
              "arranged_profile": "Company Overview\\nMB Future Tech",
              "missing_information": ["Business hours"],
              "conflicts": [{
                "topic": "Opening time",
                "existing": "1:00 PM",
                "new": "5:00 PM",
                "question": "Do you want to replace it?"
              }]
            }
            ```"""
        )
        self.assertIn("MB Future Tech", result["arranged_profile"])
        self.assertEqual(result["company_name"], "MB Future Tech")
        self.assertEqual(result["missing_information"], ["Business hours"])
        self.assertEqual(result["conflicts"][0]["new"], "5:00 PM")

    @patch("app.services.company_profile_manager.ai_gateway.generate_sync")
    def test_uses_managed_gateway_without_customer_key(self, generate_reply):
        generate_reply.return_value = {
            "reply": '{"arranged_profile":"Company Overview\\nTest",'
                     '"missing_information":[],"conflicts":[]}',
            "provider": "gemini",
            "model": "gemini-test",
        }
        result = review_company_profile("Test", 7)
        self.assertNotIn("provider", result)
        self.assertNotIn("model", result)
        generate_reply.assert_called_once()
        prompt = generate_reply.call_args.args[0]
        self.assertIn("Build arranged_profile ONLY", prompt)
        self.assertIn("Treat the draft as a complete replacement", prompt)
        self.assertNotIn("saved_company_profile", prompt)
        self.assertIn("<draft_company_profile>\nTest", prompt)


if __name__ == "__main__":
    unittest.main()
