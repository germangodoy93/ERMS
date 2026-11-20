"""Consecutive document numbers per organization, type and year (ADR-024).

A single atomic upsert: concurrent requests never get the same number, including the first
number of the year.
"""

import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.organizations.models import Branch
from app.shared.context import BOGOTA, utcnow


def next_document_number(
    session: Session, organization_id: uuid.UUID, doc_type: str, prefix: str
) -> str:
    year = utcnow().astimezone(BOGOTA).year
    value = session.execute(
        text(
            "INSERT INTO document_sequences (organization_id, doc_type, year, last_value) "
            "VALUES (:org, :doc, :year, 1) "
            "ON CONFLICT (organization_id, doc_type, year) "
            "DO UPDATE SET last_value = document_sequences.last_value + 1 "
            "RETURNING last_value"
        ),
        {"org": organization_id, "doc": doc_type, "year": year},
    ).scalar_one()
    return f"{prefix}-{year}-{value:06d}"


def default_branch(session: Session, organization_id: uuid.UUID) -> Branch | None:
    """Single-branch operation today: the oldest active branch."""
    return session.scalar(
        select(Branch)
        .where(Branch.organization_id == organization_id, Branch.is_active.is_(True))
        .order_by(Branch.created_at)
        .limit(1)
    )
