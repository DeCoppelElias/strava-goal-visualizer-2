import logging
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s"


class RequestIdFilter(logging.Filter):
    """Inject the current request id onto every log record so LOG_FORMAT can print it."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging() -> None:
    """Configure root logging with the request-id-aware plain-text format."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    request_id_filter = RequestIdFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(request_id_filter)
