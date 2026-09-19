import logging
import re

CAPABILITY_PATH = re.compile(r"/(?:d|a|receipt)/[^/?\s]+")


class RedactCapabilitiesFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        redacted = CAPABILITY_PATH.sub(lambda match: "/" + match.group(0).split("/")[1] + "/[redacted]", message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        request = getattr(record, "request", None)
        if request is not None and hasattr(request, "path"):
            request.path = CAPABILITY_PATH.sub(lambda match: "/" + match.group(0).split("/")[1] + "/[redacted]", request.path)
        return True
