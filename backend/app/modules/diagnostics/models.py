"""Diagnostic of a work order: one session per order, one result per test, and the one-time
pairing codes that let the Windows agent report into that session only."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DiagnosticSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diagnostic_sessions"
    __table_args__ = (UniqueConstraint("work_order_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    started_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agent_elevated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    agent_reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DiagnosticResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "diagnostic_results"
    __table_args__ = (
        UniqueConstraint("session_id", "test_code"),
        CheckConstraint(
            "result IN ('OK', 'WARNING', 'FAIL', 'NOT_TESTED', 'NOT_SUPPORTED')",
            name="result_valid",
        ),
        CheckConstraint("source IN ('MANUAL', 'AGENT', 'AI_SUGGESTION')", name="source_valid"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False
    )
    test_code: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AgentPairing(UUIDPrimaryKeyMixin, Base):
    """One-time code (shown to the technician) exchanged for a short-lived agent token that
    can only report results into one diagnostic session, once. Both are stored hashed."""

    __tablename__ = "agent_pairings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
