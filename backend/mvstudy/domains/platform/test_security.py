"""01 域安全原语测试：口令摘要与 JWT 往返，不依赖数据库。"""

from __future__ import annotations

import unittest

from .security import hash_password, issue_token, read_token, verify_password

SECRET = "unit-test-secret-0123456789abcdef"
OTHER_SECRET = "unit-test-secret-fedcba9876543210"


class PasswordTest(unittest.TestCase):
    def test_digest_hides_plaintext_and_verifies(self):
        digest = hash_password("Stud@123")
        self.assertNotIn("Stud@123", digest)
        self.assertTrue(verify_password("Stud@123", digest))
        self.assertFalse(verify_password("stud@123", digest))

    def test_same_password_produces_different_digests(self):
        self.assertNotEqual(hash_password("same"), hash_password("same"))


class TokenTest(unittest.TestCase):
    def test_round_trip_keeps_subject(self):
        self.assertEqual(read_token(issue_token("u-s01", SECRET, 60), SECRET), "u-s01")

    def test_wrong_secret_is_rejected(self):
        self.assertIsNone(read_token(issue_token("u-s01", SECRET, 60), OTHER_SECRET))

    def test_expired_token_is_rejected(self):
        self.assertIsNone(read_token(issue_token("u-s01", SECRET, -1), SECRET))

    def test_malformed_token_is_rejected(self):
        self.assertIsNone(read_token("not-a-jwt", SECRET))


if __name__ == "__main__":
    unittest.main()
