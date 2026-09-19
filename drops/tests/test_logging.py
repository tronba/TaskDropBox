import logging
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from django.test import SimpleTestCase

from drops.logging_filters import RedactCapabilitiesFilter
from drops.middleware import CorrelationIdMiddleware


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

    def test_expected_not_found_is_not_logged_as_an_unexpected_error(self):
        middleware = CorrelationIdMiddleware(lambda request: None)
        request = SimpleNamespace(correlation_id="test-correlation")
        with patch("drops.middleware.error_logger.exception") as log_exception:
            middleware.process_exception(request, Http404())
        log_exception.assert_not_called()
