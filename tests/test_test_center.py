"""Web Test Center safety tests."""
import os
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.services import test_center_service

class TestCenterTests(unittest.TestCase):
    def test_disabled_in_production(self):
        with patch.dict(os.environ,{"AURA_ENV":"production"}), self.assertRaises(HTTPException) as raised:
            test_center_service.ensure_available()
        self.assertEqual(raised.exception.status_code,404)
    def test_live_test_requires_billable_confirmation(self):
        with patch.dict(os.environ,{"AURA_ENV":"development"}), self.assertRaises(HTTPException) as raised:
            test_center_service.run_live_provider_test(False)
        self.assertEqual(raised.exception.status_code,400)

if __name__ == "__main__": unittest.main()
