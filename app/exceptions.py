"""Свои исключения и обработчики. Любая ошибка уходит клиенту как {"error": "...", "detail": "..."}."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class AppError(Exception):
    status_code = 500
    error = "internal_error"

    def __init__(self, detail: str):
        self.detail = detail


class NotFoundError(AppError):
    status_code = 404
    error = "not_found"


class ConflictError(AppError):
    status_code = 409
    error = "conflict"


class BusinessRuleError(AppError):
    status_code = 400
    error = "business_rule"


class UnsupportedMediaError(AppError):
    status_code = 415
    error = "unsupported_media_type"


class TooManyRequestsError(AppError):
    status_code = 429
    error = "too_many_requests"


class LLMError(AppError):
    status_code = 502
    error = "bad_gateway"


def error_response(status_code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "detail": detail})


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.error, exc.detail)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    messages = [".".join(str(part) for part in err["loc"]) + ": " + err["msg"] for err in exc.errors()]
    return error_response(422, "validation_error", "; ".join(messages))


async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    # несуществующий адрес или метод
    error = "not_found" if exc.status_code == 404 else "http_error"
    return error_response(exc.status_code, error, str(exc.detail))


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(500, "internal_error", "Unexpected server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
