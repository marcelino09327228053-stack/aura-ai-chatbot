import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.faq_generator import generate_faq_items


class AiFaqGeneratorTests(unittest.TestCase):
    @patch("app.services.faq_generator.ai_gateway.generate_sync")
    def test_ai_generation_removes_navigation_and_validates_json(self, generate):
        generate.return_value = {"reply": """```json
        [
          {"question":"What services do you provide?","answer":"We provide logistics."},
          {"question":"Where are you located?","answer":"Davao City."}
        ]
        ```"""}

        items = generate_faq_items(
            "<nav>Skip to Main Content</nav><h1>Example Company</h1><p>Logistics in Davao City.</p>",
            2,
        )

        self.assertEqual(len(items), 2)
        prompt = generate.call_args.args[0]
        profile_section = prompt.rsplit("<company_profile>", 1)[1]
        self.assertNotIn("Skip to Main Content", profile_section)
        self.assertIn("Example Company", profile_section)


if __name__ == "__main__":
    unittest.main()
