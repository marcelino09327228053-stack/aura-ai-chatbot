import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import customer_memory_service


class CustomerMemoryServiceTests(unittest.TestCase):
    @patch("app.services.customer_memory_service.get_preferences", return_value={})
    @patch("app.services.customer_memory_service.memory_repository.upsert_memory")
    def test_saves_explicit_sir_preference(self, upsert_mock, _get_mock):
        customer_memory_service.update_explicit_preferences(2, "facebook:page:user", "Sir ako.")
        upsert_mock.assert_any_call(2, "facebook:page:user", "preferred_title", "Sir")

    @patch("app.services.customer_memory_service.get_preferences", return_value={})
    @patch("app.services.customer_memory_service.memory_repository.upsert_memory")
    def test_saves_explicit_name_and_language(self, upsert_mock, _get_mock):
        customer_memory_service.update_explicit_preferences(
            2, "customer-1", "Ang pangalan ko ay carlo. Mag-English tayo."
        )
        upsert_mock.assert_any_call(2, "customer-1", "preferred_name", "Carlo")
        upsert_mock.assert_any_call(2, "customer-1", "preferred_language", "English")

    @patch("app.services.customer_memory_service.get_preferences", return_value={})
    @patch("app.services.customer_memory_service.memory_repository.delete_memory")
    def test_forgets_title_when_customer_requests_it(self, delete_mock, _get_mock):
        customer_memory_service.update_explicit_preferences(
            2, "customer-1", "Huwag mo na akong tawaging Sir."
        )
        delete_mock.assert_any_call(2, "customer-1", "preferred_title")

    def test_builds_small_preference_context(self):
        context = customer_memory_service.build_customer_memory_context(
            {
                "preferred_name": "Carlo",
                "preferred_title": "Sir",
                "preferred_language": "Filipino",
            }
        )
        self.assertIn("Preferred customer name: Carlo", context)
        self.assertIn("Preferred customer title: Sir", context)
        self.assertIn("Preferred response language: Filipino", context)


if __name__ == "__main__":
    unittest.main()
