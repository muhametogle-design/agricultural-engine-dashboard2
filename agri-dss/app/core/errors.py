"""Typed application errors, surfaced as RFC-7807-style problem details."""
from __future__ import annotations


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, detail: dict | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class DomainValidationError(AppError):
    status_code = 422
    code = "domain_validation"


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"


class NoCoverageError(AppError):
    """Spatial service returned no data for the requested location."""

    status_code = 422
    code = "no_coverage"


class ConfigError(AppError):
    status_code = 500
    code = "configuration_error"
