import logging
import secrets

from django.conf import settings
from django.http import Http404
from django.utils import translation
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin

error_logger = logging.getLogger("taskdropbox.errors")


class DefaultLanguageMiddleware:
    """Use the SSH-controlled default unless this browser explicitly chose a language."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supported = {code for code, _ in settings.LANGUAGES}
        selected = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        language = selected if selected in supported else settings.LANGUAGE_CODE
        previous = translation.get_language()
        translation.activate(language)
        request.LANGUAGE_CODE = language
        try:
            response = self.get_response(request)
        finally:
            if previous:
                translation.activate(previous)
            else:
                translation.deactivate()
        response.headers.setdefault("Content-Language", language)
        patch_vary_headers(response, ("Cookie",))
        return response


class CorrelationIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.correlation_id = secrets.token_hex(8)

    def process_response(self, request, response):
        correlation_id = getattr(request, "correlation_id", None)
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, Http404):
            return None
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
        if request.path == "/" or request.path.startswith(
            ("/teacher/", "/create", "/d/", "/a/", "/manage/", "/receipt/", "/i18n/")
        ):
            response.headers["Cache-Control"] = "no-store"
        return response
