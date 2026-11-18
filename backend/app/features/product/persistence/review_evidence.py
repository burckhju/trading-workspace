"""Append-only original documents; a failed refresh never erases a prior source."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProductReviewDocumentModel(Base):
    __tablename__ = "product_review_documents"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "warrant_id",
            "kind",
            "revision_number",
            name="uq_product_review_document_revision",
        ),
        CheckConstraint("revision_number >= 1", name="product_review_revision_positive"),
        CheckConstraint("kind IN ('KID', 'LISTING_TERMS')", name="product_review_document_kind"),
        Index(
            "ix_product_review_document_history",
            "workspace_id",
            "warrant_id",
            "kind",
            "recorded_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    warrant_id: Mapped[UUID] = mapped_column(ForeignKey("warrants.id", ondelete="RESTRICT"))
    terms_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrant_terms_versions.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(30))
    revision_number: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_reference: Mapped[str] = mapped_column(String(2000))
    document_sha256: Mapped[str] = mapped_column(String(64))
    document: Mapped[bytes] = mapped_column(LargeBinary)
    binding: Mapped[dict[str, Any]] = mapped_column(JSON)
    facts: Mapped[dict[str, Any]] = mapped_column(JSON)
    parser_version: Mapped[str] = mapped_column(String(80))


class ProductReviewAcquisitionModel(Base):
    """Operational retry budget, independent from immutable evidence revisions."""

    __tablename__ = "product_review_acquisition"
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), primary_key=True
    )
    warrant_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrants.id", ondelete="RESTRICT"), primary_key=True
    )
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(100))
