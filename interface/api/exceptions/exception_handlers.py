import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from application.exceptions import ApplicationError
from interface.api.exceptions.error import AppError
from interface.api.exceptions.error import from_application_error
from interface.api.exceptions.error_code import ErrorCode
from interface.api.exceptions.problem import ProblemDetails
from interface.api.logging_utils import log_api_event

logger = logging.getLogger(__name__)


def _problem_json(
    request: Request,
    *,
    status: int,
    title: str,
    code: str | None = None,
    detail: str | None = None,
    fields: dict | None = None,
) -> JSONResponse:
    pd = ProblemDetails(
        title=title,
        status=status,
        detail=detail,
        instance=getattr(request.state, "request_id", None),
        code=code,
        fields=fields,
    )
    return JSONResponse(
        content=jsonable_encoder(pd.model_dump()),
        status_code=status,
        media_type="application/problem+json",
    )


# ---- handlers ----


async def app_error_handler(request: Request, exc: Exception) -> Response:
    if isinstance(exc, ApplicationError) and not isinstance(exc, AppError):
        exc = from_application_error(exc)
    if not isinstance(exc, AppError):
        return await unhandled_exception_handler(request, exc)

    log_api_event(
        "request_failed",
        request=request,
        level=logging.ERROR,
        message="Request failed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.http_status,
            "error_type": type(exc).__name__,
            "error_message": exc.message,
            "input_summary": getattr(request.state, "input_summary", None),
            "error": {
                "code": exc.code,
                "details": exc.details,
            },
        },
    )

    headers = {}
    if exc.http_status in (429, 503) and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    return JSONResponse(
        ProblemDetails(
            title=exc.code,
            status=exc.http_status,
            detail=exc.message,
            code=exc.code,
            fields=exc.details or None,
        ).model_dump(),
        status_code=exc.http_status,
        media_type="application/problem+json",
        headers=headers,
    )


async def validation_error_handler(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, RequestValidationError):
        return await unhandled_exception_handler(request, exc)
    log_api_event(
        "request_failed",
        request=request,
        level=logging.ERROR,
        message="Request failed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": 422,
            "error_type": type(exc).__name__,
            "error_message": "Request validation failed",
            "input_summary": getattr(request.state, "input_summary", None),
        },
    )
    return _problem_json(
        request,
        status=422,
        title="Request validation failed",
        code=ErrorCode.VALIDATION,
        detail="Invalid request payload or parameters.",
        fields={"errors": exc.errors()},
    )


async def pydantic_validation_error_handler(
    request: Request, exc: Exception
) -> Response:
    if not isinstance(exc, PydanticValidationError):
        return await unhandled_exception_handler(request, exc)
    log_api_event(
        "request_failed",
        request=request,
        level=logging.ERROR,
        message="Request failed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": 422,
            "error_type": type(exc).__name__,
            "error_message": "Request validation failed",
            "input_summary": getattr(request.state, "input_summary", None),
        },
    )
    return _problem_json(
        request,
        status=422,
        title="Request validation failed",
        code=ErrorCode.VALIDATION,
        detail="Invalid request payload or parameters.",
        fields={"errors": exc.errors()},
    )


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, StarletteHTTPException):
        return await unhandled_exception_handler(request, exc)
    log_api_event(
        "request_failed",
        request=request,
        level=logging.ERROR,
        message="Request failed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "error_type": type(exc).__name__,
            "error_message": exc.detail
            if isinstance(exc.detail, str)
            else "HTTP error",
            "input_summary": getattr(request.state, "input_summary", None),
        },
    )

    return _problem_json(
        request,
        status=exc.status_code,
        title="HTTP error",
        detail=exc.detail if isinstance(exc.detail, str) else None,
    )


def get_clean_traceback(exc: Exception) -> str:
    tb = traceback.extract_tb(exc.__traceback__)
    clean_frames = [
        f
        for f in tb
        if "backend-api" in f.filename and "site-packages" not in f.filename
    ]

    if not clean_frames:
        clean_frames = tb[-2:]

    formatted = "".join(traceback.format_list(clean_frames))
    return f"\n{formatted}{type(exc).__name__}: {str(exc)}"


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    clean_tb = get_clean_traceback(exc)
    log_api_event(
        "request_failed",
        request=request,
        level=logging.ERROR,
        message="Request failed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "error_type": type(exc).__name__,
            "error_message": "Unexpected error.",
            "error_summary": clean_tb,
            "input_summary": getattr(request.state, "input_summary", None),
        },
    )
    return _problem_json(
        request,
        status=500,
        title="Internal Server Error",
        code=ErrorCode.INTERNAL,
        detail="Unexpected error.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, app_error_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(
        PydanticValidationError, pydantic_validation_error_handler
    )
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
