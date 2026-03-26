from typing import Any, Mapping, Optional

from interface.api.exceptions.error_code import ErrorCode


class AppError(Exception):
    code: ErrorCode = ErrorCode.INTERNAL
    http_status: int = 500

    def __init__(
        self,
        message: str = "",
        *,
        details: Optional[Mapping[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})
        self.cause = cause


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
