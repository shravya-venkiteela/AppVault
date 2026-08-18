import logging
import os
 
_SENSITIVE_ENV_VARS = ["APPVAULT_EMAIL_PASSWORD"]
 
_REDACTED = "***REDACTED***"
 
 
def _get_secrets() -> list[str]:
    return [value for var in _SENSITIVE_ENV_VARS if (value := os.environ.get(var))]
 
 
class SecretMaskingFilter(logging.Filter):
    """Redacts known secret values from a log record's plain message
    and args. Does NOT handle exception tracebacks -- see
    SecretMaskingFormatter below, which is required for that case."""
 
    def filter(self, record: logging.LogRecord) -> bool:
        secrets = _get_secrets()
        if not secrets:
            return True
 
        message = record.getMessage()
        for secret in secrets:
            message = message.replace(secret, _REDACTED)
 
        record.msg = message
        record.args = ()
        return True
 
 
class SecretMaskingFormatter(logging.Formatter):
    """A Formatter that redacts secrets from the FORMATTED exception
    traceback text. This is necessary because record.exc_text is only
    populated during formatting -- by the time a Filter runs, the
    traceback hasn't been rendered to text yet, so a Filter alone cannot
    catch a secret embedded in an exception's own message.
    (Confirmed by direct testing: a Filter-only approach let a raw
    password through inside a traceback. This Formatter override is the
    fix.)"""
 
    def formatException(self, ei) -> str:
        text = super().formatException(ei)
        for secret in _get_secrets():
            text = text.replace(secret, _REDACTED)
        return text
 
    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        for secret in _get_secrets():
            formatted = formatted.replace(secret, _REDACTED)
        return formatted
 
 
def setup_logging(debug: bool = False) -> None:
    """Configure logging for the whole app. Call once, at CLI startup."""
    level = logging.DEBUG if debug else logging.WARNING
 
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
 
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(SecretMaskingFormatter("%(levelname)s: %(message)s"))
    handler.addFilter(SecretMaskingFilter())
 
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
 