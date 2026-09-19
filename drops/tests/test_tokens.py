from django.test import SimpleTestCase, override_settings

from drops.tokens import (
    digest_token,
    extract_key,
    new_admin_token,
    new_student_token,
    student_code_words,
)


@override_settings(BASE_URL="http://10.20.0.10")
class TokenTests(SimpleTestCase):
    def test_student_and_admin_tokens_are_independent(self):
        student = new_student_token()
        admin = new_admin_token()
        self.assertNotEqual(student, admin)
        self.assertNotEqual(digest_token(student), digest_token(admin))
        parts = student.split("-")
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(part in student_code_words() for part in parts))
        self.assertGreaterEqual(len(admin), 40)

    def test_extract_key_accepts_raw_key_and_matching_url(self):
        self.assertEqual(extract_key("abc_DEF-123", "d"), "abc_DEF-123")
        self.assertEqual(extract_key("http://10.20.0.10/d/abc_DEF-123/", "d"), "abc_DEF-123")

    def test_extract_key_rejects_wrong_origin_route_and_query(self):
        self.assertIsNone(extract_key("http://evil.test/d/key/", "d"))
        self.assertIsNone(extract_key("http://10.20.0.10/a/key/", "d"))
        self.assertIsNone(extract_key("http://10.20.0.10/d/key/?leak=yes", "d"))
