from __future__ import annotations


class SignalsPlatformClientError(Exception):
    """Base exception for restricted Signals Platform client errors."""


class SignalsPlatformAuthenticationError(SignalsPlatformClientError):
    """The restricted API token was rejected."""


class SignalsPlatformNotFoundError(SignalsPlatformClientError):
    """The requested restricted resource was not found."""


class SignalsPlatformRateLimitError(SignalsPlatformClientError):
    """The restricted API rate limit was exceeded."""


class SignalsPlatformUnavailableError(SignalsPlatformClientError):
    """The restricted API could not be reached or returned a server error."""


class SignalsPlatformResponseError(SignalsPlatformClientError):
    """The restricted API returned malformed or unexpected data."""
