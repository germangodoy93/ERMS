"""Operational commands.

    python -m app.cli bootstrap --org-name "Mi Taller SAS" --org-slug mi-taller \
        --admin-email admin@mitaller.co --admin-name "Nombre Apellido"

Creates the organization, its Bogotá branch, the four system roles and the first
administrator. The password is read from the ERMS_ADMIN_PASSWORD environment variable or
asked interactively (never passed as an argument, so it does not end up in shell history).
The administrator must change it on first login.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import hash_password
from app.modules.audit.service import AuditService
from app.modules.organizations.models import Branch, Organization
from app.modules.roles.catalog import RoleCode
from app.modules.roles.service import create_system_roles
from app.modules.users.models import User
from app.modules.users.passwords import ensure_password_policy
from app.shared.context import utcnow


def _read_password() -> str:
    password = os.environ.get("ERMS_ADMIN_PASSWORD")
    if password:
        return password
    if not sys.stdin.isatty():
        sys.exit("Set ERMS_ADMIN_PASSWORD or run interactively.")
    first = getpass.getpass("Contraseña temporal del administrador: ")
    if first != getpass.getpass("Repita la contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    return first


def bootstrap(args: argparse.Namespace) -> None:
    settings = get_settings()
    email = args.admin_email.strip().lower()
    password = _read_password()
    ensure_password_policy(settings, password, email=email)

    with get_session_factory()() as session, session.begin():
        if session.scalar(select(Organization).where(Organization.slug == args.org_slug)):
            sys.exit(f"La organización '{args.org_slug}' ya existe; no se modificó nada.")
        if session.scalar(select(User).where(User.email == email)):
            sys.exit(f"Ya existe un usuario con el correo {email}; no se modificó nada.")

        organization = Organization(name=args.org_name, slug=args.org_slug, tax_id=args.org_nit)
        session.add(organization)
        session.flush()
        session.add(
            Branch(organization_id=organization.id, name=args.branch_name, city=args.branch_city)
        )
        roles = create_system_roles(session, organization.id)
        admin = User(
            organization_id=organization.id,
            email=email,
            full_name=args.admin_name,
            password_hash=hash_password(password),
            password_changed_at=utcnow(),
            must_change_password=True,
            roles=[roles[RoleCode.ADMIN]],
        )
        session.add(admin)
        session.flush()
        AuditService(session).record(
            "organization.bootstrapped",
            entity_type="organization",
            entity_id=organization.id,
            organization_id=organization.id,
            actor_user_id=None,
            changes={"admin_email": email, "branch": args.branch_name},
        )

    print(f"Organización '{args.org_name}' creada. Administrador: {email}")
    print("El administrador deberá cambiar la contraseña en el primer inicio de sesión.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="ERMS operations")
    commands = parser.add_subparsers(dest="command", required=True)

    boot = commands.add_parser("bootstrap", help="Crear organización, sede y primer administrador")
    boot.add_argument("--org-name", required=True)
    boot.add_argument("--org-slug", required=True)
    boot.add_argument("--org-nit", default=None)
    boot.add_argument("--branch-name", default="Sede Bogotá")
    boot.add_argument("--branch-city", default="Bogotá")
    boot.add_argument("--admin-email", required=True)
    boot.add_argument("--admin-name", required=True)
    boot.set_defaults(handler=bootstrap)

    args = parser.parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
