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

    @patch("app.services.company_profile_manager.ai_service.generate_reply")
    @patch("app.services.company_profile_manager.ai_provider_repository.get_key")
    @patch("app.services.company_profile_manager.ai_service.get_selected_model")
    @patch("app.services.company_profile_manager.ai_service.get_provider_status")
    def test_uses_connected_provider_without_inventing_client_side_key(
        self, statuses, selected_model, get_key, generate_reply
    ):
        statuses.return_value = [{"id": "gemini", "configured": True}]
        selected_model.return_value = "gemini-test"
        get_key.return_value = "encrypted-server-key"
        generate_reply.return_value = (
            '{"arranged_profile":"Company Overview\\nTest",'
            '"missing_information":[],"conflicts":[]}'
        )
        result = review_company_profile("Test", 7)
        self.assertEqual(result["provider"], "gemini")
        generate_reply.assert_called_once()
        self.assertEqual(generate_reply.call_args.args[3], "encrypted-server-key")
        prompt = generate_reply.call_args.args[0]
        self.assertIn("Build arranged_profile ONLY", prompt)
        self.assertIn("Treat the draft as a complete replacement", prompt)
        self.assertNotIn("saved_company_profile", prompt)
        self.assertIn("<draft_company_profile>\nTest", prompt)


if __name__ == "__main__":
    unittest.main()
