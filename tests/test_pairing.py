import tempfile
import unittest
from pathlib import Path

from casalocal_core.services.pairing import PairingError, PairingService


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "test.db"
        self.service = PairingService(self.database)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_pairing_issues_and_validates_token(self):
        session = self.service.start()
        token = self.service.complete(str(session["code"]), label="Home Assistant")
        self.assertTrue(self.service.validate_token(token))

    def test_pairing_code_is_one_time(self):
        session = self.service.start()
        self.service.complete(str(session["code"]))
        with self.assertRaises(PairingError):
            self.service.complete(str(session["code"]))

    def test_wrong_code_is_rejected(self):
        self.service.start()
        with self.assertRaises(PairingError):
            self.service.complete("00000000")


if __name__ == "__main__":
    unittest.main()
