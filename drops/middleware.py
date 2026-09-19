import logging
import secrets

from django.utils.deprecation import MiddlewareMixin

error_logger = logging.getLogger("taskdropbox.errors")


class CorrelationIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.correlation_id = secrets.token_hex(8)

    def process_response(self, request, response):
        correlation_id = getattr(request, "correlation_id", None)
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id
        return response

    def process_exception(self, request, exception):
        error_logger.exception(
            "unexpected_error correlation=%s",
            getattr(request, "correlation_id", "unavailable"),
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        return None


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self'; style-src 'self'; "
            "script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        )
        if request.path.startswith(("/create", "/d/", "/a/", "/manage/", "/receipt/")):
            response.headers["Cache-Control"] = "no-store"
        return response
