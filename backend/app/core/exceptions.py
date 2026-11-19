"""Centralised error handling producing RFC 9457 Problem Details responses.

Every error returned by the API has the same shape:
    {"type", "title", "status", "detail", "code", "instance", "errors"?}
Domain modules raise subclasses of `AppError`; they never build HTTP responses.
"""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"


class AppError(Exception):
    """Base class for expected, domain-level errors."""

    status_code: int = HTTPStatus.BAD_REQUEST
    code: str = "bad_request"
    title: str = "Solicitud inválida"

    def __init__(self, detail: str, *, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.errors = errors


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"
    title = "Recurso no encontrado"


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "conflict"
    title = "Conflicto con el estado actual"


class PermissionDeniedError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    code = "permission_denied"
    title = "Permiso denegado"


class AuthenticationError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "not_authenticated"
    title = "No autenticado"


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"
    title = "Credenciales inválidas"


class PasswordChangeRequiredError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    code = "password_change_required"
    title = "Debe cambiar su contraseña"


class BusinessRuleError(AppError):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "business_rule_violation"
    title = "Operación no permitida"


def problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://erms.local/problems/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "instance": request.url.path,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM_CONTENT_TYPE)


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 - registered only for AppError
    response = problem_response(
        request,
        status=exc.status_code,
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
        errors=exc.errors,
    )
    if isinstance(exc, AuthenticationError):
        response.headers["WWW-Authenticate"] = "Bearer"
    return response


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = [
        {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    return problem_response(
        request,
        status=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="validation_error",
        title="Datos de entrada inválidos",
        detail="Uno o más campos no cumplen las validaciones.",
        errors=errors,
    )


async def _http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    status = HTTPStatus(exc.status_code)
    return problem_response(
        request,
        status=status.value,
        code=status.name.lower(),
        title=status.phrase,
        detail=str(exc.detail),
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", extra={"path": request.url.path})
    return problem_response(
        request,
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        code="internal_error",
        title="Error interno",
        detail="Ocurrió un error inesperado. El incidente fue registrado.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
