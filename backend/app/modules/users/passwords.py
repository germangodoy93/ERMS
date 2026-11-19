from app.core.config import Settings
from app.core.exceptions import BusinessRuleError
from app.core.security import password_policy_errors


def ensure_password_policy(settings: Settings, password: str, *, email: str) -> None:
    errors = password_policy_errors(password, email=email, min_length=settings.password_min_length)
    if errors:
        raise BusinessRuleError(
            "La contraseña no cumple la política de seguridad.",
            errors=[
                {"field": "password", "message": msg, "type": "password_policy"} for msg in errors
            ],
        )
