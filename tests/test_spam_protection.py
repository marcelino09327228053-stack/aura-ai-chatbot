import os
import sys
import tempfile
import unittest
from pathlib import Path

test_db = Path(tempfile.gettempdir()) / "mb_future_spam_test.db"
test_db.unlink(missing_ok=True)
os.environ["SQLITE_PATH"] = str(test_db)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import init_db
from app.services.spam_protection import check_message


class SpamProtectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_four_identical_messages_trigger_temporary_block(self):
        for offset in range(3):
            result = check_message(1, "facebook", "sender-1", "Buy now!", now=100 + offset)
            self.assertFalse(result["blocked"])
        result = check_message(1, "facebook", "sender-1", "  BUY NOW! ", now=103)
        self.assertTrue(result["blocked"])
        self.assertTrue(result["new_block"])

    def test_normal_messages_are_not_blocked(self):
        for offset, text in enumerate(("Hello", "What do you sell?", "Where are you located?")):
            self.assertFalse(check_message(1, "facebook", "sender-2", text, now=200 + offset)["blocked"])


if __name__ == "__main__":
    unittest.main()
