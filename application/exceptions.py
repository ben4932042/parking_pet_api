from typing import Any, Mapping, Optional


class ApplicationError(Exception):
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


class NotFoundError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class ValidationDomainError(ApplicationError):
    pass


class AuthenticationError(ApplicationError):
    pass
