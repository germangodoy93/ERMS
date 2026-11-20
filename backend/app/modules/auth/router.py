from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Response, status

from app.core.config import Settings, get_settings
from app.core.email import Mailer, get_mailer
from app.core.exceptions import InvalidCredentialsError, RateLimitedError
from app.core.rate_limit import FailureLimiter
from app.modules.auth.dependencies import CurrentPrincipal, get_auth_service
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthResult, AuthService
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/auth", tags=["auth"])

Service = Annotated[AuthService, Depends(get_auth_service)]
Context = Annotated[RequestContext, Depends(get_request_context)]
AppSettings = Annotated[Settings, Depends(get_settings)]
REFRESH_COOKIE = "erms_refresh"


def _cookie_path(settings: Settings) -> str:
    return f"{settings.api_prefix}/auth"


def _set_refresh_cookie(response: Response, settings: Settings, result: AuthResult) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=result.refresh_token,
        expires=result.refresh_expires_at,
        path=_cookie_path(settings),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _token_response(result: AuthResult) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token,
        expires_at=result.access_expires_at,
        must_change_password=result.must_change_password,
    )


_login_limiter: FailureLimiter | None = None


def get_login_limiter(settings: Settings) -> FailureLimiter:
    global _login_limiter
    if _login_limiter is None:
        _login_limiter = FailureLimiter(
            settings.login_ip_max_failures, settings.login_ip_window_minutes * 60
        )
    return _login_limiter


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(
    body: LoginRequest,
    response: Response,
    service: Service,
    context: Context,
    settings: AppSettings,
) -> TokenResponse:
    limiter = get_login_limiter(settings)
    key = context.ip_address or "unknown"
    wait = limiter.retry_after(key)
    if wait:
        raise RateLimitedError(
            "Demasiados intentos fallidos desde esta red. Intente de nuevo más tarde.",
            retry_after=wait,
        )
    try:
        result = service.login(body.email, body.password, context)
    except InvalidCredentialsError:
        limiter.record_failure(key)
        raise
    _set_refresh_cookie(response, settings, result)
    return _token_response(result)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar el access token usando la cookie de sesión (rota el refresh token)",
)
def refresh(
    response: Response,
    service: Service,
    context: Context,
    settings: AppSettings,
    refresh_token: Annotated[
        str | None, Cookie(alias=REFRESH_COOKIE, include_in_schema=False)
    ] = None,
) -> TokenResponse:
    result = service.refresh(refresh_token, context)
    _set_refresh_cookie(response, settings, result)
    return _token_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
def logout(
    response: Response,
    service: Service,
    context: Context,
    settings: AppSettings,
    refresh_token: Annotated[
        str | None, Cookie(alias=REFRESH_COOKIE, include_in_schema=False)
    ] = None,
) -> None:
    service.logout(refresh_token, context)
    response.delete_cookie(
        REFRESH_COOKIE,
        path=_cookie_path(settings),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar enlace de restablecimiento (misma respuesta exista o no el correo)",
)
def forgot_password(
    body: ForgotPasswordRequest,
    background: BackgroundTasks,
    service: Service,
    context: Context,
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> dict[str, str]:
    email = service.request_password_reset(body.email, context)
    if email is not None:
        background.add_task(mailer.send, email)
    return {
        "detail": "Si el correo está registrado, recibirá un enlace para restablecer la contraseña."
    }


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Restablecer la contraseña con el token recibido por correo",
)
def reset_password(body: ResetPasswordRequest, service: Service, context: Context) -> None:
    service.reset_password(body.token, body.new_password, context)


@router.post(
    "/password/change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar la contraseña propia (cierra las demás sesiones)",
)
def change_password(
    body: ChangePasswordRequest, principal: CurrentPrincipal, service: Service, context: Context
) -> None:
    service.change_password(
        principal.user, principal.session_id, body.current_password, body.new_password, context
    )


@router.get("/me", response_model=MeResponse, summary="Usuario actual, roles y permisos")
def me(principal: CurrentPrincipal, service: Service) -> MeResponse:
    return service.me(principal.user)
