import logging

from django.test import SimpleTestCase

from drops.logging_filters import RedactCapabilitiesFilter


class LoggingFilterTests(SimpleTestCase):
    def test_capability_segments_are_redacted(self):
        record = logging.LogRecord(
            "test",
            logging.WARNING,
            __file__,
            1,
            "Not Found: /d/super-secret-student-token/",
            (),
            None,
        )
        RedactCapabilitiesFilter().filter(record)
        self.assertEqual(record.getMessage(), "Not Found: /d/[redacted]/")

    def test_unrelated_paths_are_unchanged(self):
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "GET /healthz", (), None)
        RedactCapabilitiesFilter().filter(record)
        self.assertEqual(record.getMessage(), "GET /healthz")
