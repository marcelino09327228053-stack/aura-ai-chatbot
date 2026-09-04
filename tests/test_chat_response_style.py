import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.chat_service import (
    _build_prompt,
    _company_representative_reply,
    _professional_plain_reply,
)
from app.services.company_profile_manager import test_company_profile as run_profile_test


class ChatResponseStyleTests(unittest.TestCase):
    def test_removes_markdown_asterisks_and_headings(self):
        result = _professional_plain_reply(
            "## **Company Name**\nOur company name is **Example Industries**.\n* Helpful service"
        )
        self.assertNotIn("*", result)
        self.assertNotIn("##", result)
        self.assertIn("Our company name is Example Industries.", result)
        self.assertIn("• Helpful service", result)

    def test_keeps_short_professional_paragraphs(self):
        result = _professional_plain_reply("First answer.\n\n\n\nSecond answer.")
        self.assertEqual(result, "First answer.\n\nSecond answer.")

    def test_customer_prompt_requires_first_person_company_voice(self):
        prompt = _build_prompt(
            "Ano ang mga serbisyo ninyo?",
            "Example Company provides construction services.",
            "auto",
        )
        self.assertIn("official representative of the company", prompt)
        self.assertIn('"kami"', prompt)
        self.assertIn('Never say "based on the company profile"', prompt)

    def test_rewrites_third_person_company_name_answer(self):
        result = _company_representative_reply(
            "Batay sa ibinigay na profile ng kumpanya, Ang pangalan ng kumpanya ay Ayala Land, Inc."
        )
        self.assertEqual(result, "Ang pangalan ng aming kumpanya ay Ayala Land, Inc.")

    def test_removes_profile_disclaimer_and_example_qualifiers(self):
        result = _company_representative_reply(
            "Batay sa profile ng kumpanya, ang aming developments ay mixed-use estates "
            "(hal. Nuvali at Alviera)."
        )
        self.assertNotIn("Batay sa profile", result)
        self.assertNotIn("hal.", result)
        self.assertIn("Nuvali at Alviera", result)

    def test_rewrites_reversed_third_person_company_name(self):
        result = _company_representative_reply(
            "Ayala Land, Inc. ang pangalan ng kumpanya."
        )
        self.assertEqual(result, "Ang pangalan ng kumpanya namin ay Ayala Land, Inc.")

    def test_rewrites_third_person_products_answer(self):
        result = _company_representative_reply(
            "Batay sa profile ng kumpanya, ang mga produkto at serbisyo ng Ayala Land ay "
            "kinabibilangan ng: residential properties, shopping centers, at offices."
        )
        self.assertNotIn("Batay sa profile", result)
        self.assertNotIn("ng Ayala Land", result)
        self.assertTrue(result.startswith("Ang mga produkto at serbisyong inaalok ng kumpanya namin ay:"))

    @patch("app.services.company_profile_manager.build_response_style_instruction")
    @patch("app.services.company_profile_manager.ai_gateway.generate_sync")
    def test_profile_test_includes_saved_response_style(
        self, reply_mock, style_mock
    ):
        reply_mock.return_value = {
            "reply": "Ang pangalan ng kumpanya namin ay Example Company.",
            "provider": "gemini",
            "model": "test-model",
        }
        style_mock.return_value = "Response style preference: Friendly and concise."
        result = run_profile_test(
            "Company name: Example Company.",
            "Ano ang pangalan ng kumpanya ninyo?",
            1,
        )
        prompt = reply_mock.call_args.args[0]
        self.assertIn("Response style preference: Friendly and concise.", prompt)
        self.assertEqual(result["reply"], "Ang pangalan ng kumpanya namin ay Example Company.")


if __name__ == "__main__":
    unittest.main()
