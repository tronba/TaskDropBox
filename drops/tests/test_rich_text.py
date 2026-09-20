from django.test import SimpleTestCase

from drops.rich_text import plain_text_to_html, rich_text_to_plain_text, sanitize_rich_text


class RichTextTests(SimpleTestCase):
    def test_sanitizer_keeps_only_supported_formatting(self):
        value = (
            '<p class="x" onclick="alert(1)">Hello <b>world</b>'
            '<img src="x" onerror="alert(2)"><script>alert(3)</script></p>'
        )
        cleaned = sanitize_rich_text(value)
        self.assertEqual(cleaned, "<p>Hello <strong>world</strong></p>")
        self.assertNotIn("onclick", cleaned)
        self.assertNotIn("<script", cleaned)
        self.assertNotIn("<img", cleaned)
        self.assertNotIn("alert(3)", cleaned)

    def test_plain_text_conversion_escapes_markup_and_preserves_paragraphs(self):
        self.assertEqual(
            plain_text_to_html("One < two\nline\n\nNext"),
            "<p>One &lt; two<br>line</p><p>Next</p>",
        )

    def test_rich_text_has_portable_plain_text_representation(self):
        value = "<p>Opening</p><ul><li>First</li><li>Second</li></ul>"
        rendered = rich_text_to_plain_text(value)
        self.assertIn("Opening", rendered)
        self.assertIn("- First", rendered)
        self.assertIn("- Second", rendered)
