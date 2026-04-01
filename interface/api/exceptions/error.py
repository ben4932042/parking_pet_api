from typing import Any, Mapping, Optional

from application.exceptions import (
    ApplicationError,
    ConflictError as ApplicationConflictError,
    NotFoundError as ApplicationNotFoundError,
    ValidationDomainError as ApplicationValidationDomainError,
)
from interface.api.exceptions.error_code import ErrorCode


class AppError(ApplicationError):
    code: ErrorCode = ErrorCode.INTERNAL
    http_status: int = 500

    def __init__(
        self,
        message: str = "",
        *,
        details: Optional[Mapping[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message, details=details, cause=cause)


class NotFoundError(AppError):
    code = ErrorCode.NOT_FOUND
    http_status = 404


class ConflictError(AppError):
    code = ErrorCode.CONFLICT
    http_status = 409


class ValidationDomainError(AppError):
    code = ErrorCode.VALIDATION
    http_status = 422


class UnauthorizedError(AppError):
    code = ErrorCode.UNAUTHORIZED
    http_status = 401


class ForbiddenError(AppError):
    code = ErrorCode.FORBIDDEN
    http_status = 403


class RateLimitedError(AppError):
    code = ErrorCode.RATE_LIMITED
    http_status = 429


class ExternalTimeoutError(AppError):
    code = ErrorCode.EXTERNAL_TIMEOUT
    http_status = 504


def from_application_error(exc: ApplicationError) -> AppError:
    if isinstance(exc, ApplicationNotFoundError):
        return NotFoundError(
            exc.message,
            details=exc.details,
            cause=exc.cause,
        )
    if isinstance(exc, ApplicationConflictError):
        return ConflictError(
            exc.message,
            details=exc.details,
            cause=exc.cause,
        )
    if isinstance(exc, ApplicationValidationDomainError):
        return ValidationDomainError(
            exc.message,
            details=exc.details,
            cause=exc.cause,
        )
    return AppError(
        exc.message,
        details=exc.details,
        cause=exc.cause,
    )
