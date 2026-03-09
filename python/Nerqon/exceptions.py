"""
Nerqon SDK — Exception classes
===================================

These exceptions are raised by the client when API calls fail.
They contain structured error information from the Nerqon API.
"""


class NerqonError(Exception):
    """Base exception for all Nerqon SDK errors."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response or {}
        super().__init__(self.message)

    def __repr__(self):
        return f"{self.__class__.__name__}(message={self.message!r}, status_code={self.status_code})"


class AuthenticationError(NerqonError):
    """Raised when API key is invalid or missing (HTTP 401/403)."""
    pass


class RateLimitError(NerqonError):
    """Raised when rate limit is exceeded (HTTP 429)."""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class NotFoundError(NerqonError):
    """Raised when a resource is not found (HTTP 404)."""
    pass


class ValidationError(NerqonError):
    """Raised when request parameters are invalid (HTTP 422)."""
    pass


class DimensionMismatchError(ValidationError):
    """Raised when embedding dimensions don't match the namespace configuration."""
    pass


class ServerError(NerqonError):
    """Raised when the Nerqon server returns a 5xx error."""
    pass


class ConnectionError(NerqonError):
    """Raised when the SDK cannot connect to the Nerqon API."""
    pass
