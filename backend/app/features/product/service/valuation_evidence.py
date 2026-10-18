"""Document-backed manual facts, bound to product identity and an exact terms version."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product.persistence.models import (
    WarrantModel,
    WarrantTermsVersionModel,
    WarrantValuationEvidenceModel,
)
from app.features.product.service.errors import WarrantConcurrentModification, WarrantNotFound


class ValuationFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_type: Literal["VANILLA_WARRANT", "OTHER_STRUCTURED"] | None
    exercise_style: Literal["EUROPEAN", "AMERICAN", "OTHER"] | None
    quanto: bool | None = Field(strict=True)
    ratio_convention: Literal["UNDERLYING_UNITS_PER_WARRANT"] | None
    expiry_at: AwareDatetime | None
    document_reference: str = Field(min_length=3, max_length=500)
    source_url: AnyHttpUrl | None = Field(default=None, max_length=2000)
    reviewed_at: AwareDatetime
    note: str = Field(min_length=3, max_length=1000)

    @field_validator("source_url")
    @classmethod
    def no_credentials(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and (value.username or value.password):
            raise ValueError("Source URLs must not contain credentials")
        return value


@dataclass(frozen=True)
class ValuationEvidence:
    id: UUID
    terms_id: UUID
    revision: int
    recorded_at: datetime
    actor_id: UUID
    facts: ValuationFacts
    identity: dict[str, str | None]
    origin: str = "MANUAL_DOCUMENT_REVIEW"


@dataclass(frozen=True)
class ValuationEvidenceView:
    revision: int
    current: ValuationEvidence | None
    history: tuple[ValuationEvidence, ...]
    status: str


def evidence_identity(warrant: WarrantModel, terms_id: UUID) -> str:
    values = [
        str(warrant.id),
        warrant.isin,
        warrant.wkn,
        str(warrant.issuer_id),
        str(warrant.underlying_id),
        str(terms_id),
    ]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def to_evidence(row: WarrantValuationEvidenceModel) -> ValuationEvidence:
    return ValuationEvidence(
        row.id,
        row.terms_id,
        row.revision,
        row.recorded_at.replace(tzinfo=UTC) if row.recorded_at.tzinfo is None else row.recorded_at,
        row.actor_id,
        ValuationFacts.model_validate(row.payload["facts"]),
        row.payload["identity"],
    )


async def current_evidence(
    session: AsyncSession,
    warrant: WarrantModel,
    terms_id: UUID,
    as_of: datetime,
) -> ValuationEvidence | None:
    row = await session.scalar(
        select(WarrantValuationEvidenceModel)
        .where(
            WarrantValuationEvidenceModel.workspace_id == warrant.workspace_id,
            WarrantValuationEvidenceModel.warrant_id == warrant.id,
            WarrantValuationEvidenceModel.recorded_at <= as_of,
        )
        .order_by(WarrantValuationEvidenceModel.revision.desc())
        .limit(1)
    )
    if row is None or row.identity_key != evidence_identity(warrant, terms_id):
        return None
    return to_evidence(row)


class ValuationEvidenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def view(
        self, workspace_id: UUID, warrant_id: UUID, now: datetime
    ) -> ValuationEvidenceView:
        if now.utcoffset() is None:
            raise ValueError("Evidence clock must be timezone aware")
        warrant = await self.session.scalar(
            select(WarrantModel).where(
                WarrantModel.workspace_id == workspace_id, WarrantModel.id == warrant_id
            )
        )
        if warrant is None:
            raise WarrantNotFound("Warrant does not exist")
        rows = (
            await self.session.scalars(
                select(WarrantValuationEvidenceModel)
                .where(
                    WarrantValuationEvidenceModel.workspace_id == workspace_id,
                    WarrantValuationEvidenceModel.warrant_id == warrant_id,
                    WarrantValuationEvidenceModel.recorded_at <= now,
                )
                .order_by(WarrantValuationEvidenceModel.revision.desc())
                .limit(20)
            )
        ).all()
        terms = (
            await self.session.scalars(
                select(WarrantTermsVersionModel).where(
                    WarrantTermsVersionModel.warrant_id == warrant_id,
                    WarrantTermsVersionModel.effective_to.is_(None),
                    WarrantTermsVersionModel.effective_from <= now,
                    WarrantTermsVersionModel.created_at <= now,
                )
            )
        ).all()
        current = (
            to_evidence(rows[0])
            if rows
            and len(terms) == 1
            and rows[0].identity_key == evidence_identity(warrant, terms[0].id)
            else None
        )
        return ValuationEvidenceView(
            rows[0].revision if rows else 0,
            current,
            tuple(to_evidence(r) for r in rows),
            "CURRENT" if current else "IDENTITY_OR_TERMS_CHANGED" if rows else "MISSING",
        )

    async def record(
        self,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
        terms_id: UUID,
        expected_version: int,
        expected_revision: int,
        facts: ValuationFacts,
        actor_id: UUID,
        now: datetime,
    ) -> ValuationEvidenceView:
        if now.utcoffset() is None:
            raise ValueError("Evidence clock must be timezone aware")
        warrant = await self.session.scalar(
            select(WarrantModel)
            .where(
                WarrantModel.workspace_id == workspace_id,
                WarrantModel.id == warrant_id,
            )
            .with_for_update()
        )
        if warrant is None:
            raise WarrantNotFound("Warrant does not exist")
        if warrant.version != expected_version:
            raise WarrantConcurrentModification("Produkt wurde geändert; bitte neu laden.")
        terms = await self.session.scalar(
            select(WarrantTermsVersionModel).where(
                WarrantTermsVersionModel.id == terms_id,
                WarrantTermsVersionModel.warrant_id == warrant_id,
                WarrantTermsVersionModel.effective_to.is_(None),
                WarrantTermsVersionModel.effective_from <= now,
                WarrantTermsVersionModel.created_at <= now,
            )
        )
        if terms is None:
            raise WarrantConcurrentModification(
                "Produktbedingungen wurden geändert; bitte neu laden."
            )
        view = await self.view(workspace_id, warrant_id, now)
        if view.revision != expected_revision:
            raise WarrantConcurrentModification("Belege wurden geändert; bitte neu laden.")
        if facts.reviewed_at > now:
            raise ValueError("Belegprüfung darf nicht in der Zukunft liegen.")
        if facts.expiry_at is not None and facts.expiry_at.date() != terms.maturity_date:
            raise ValueError(
                "Bewertungsdatum muss in der angegebenen Zeitzone zur Fälligkeit passen."
            )
        if not warrant.isin:
            raise ValueError("Eine belegte Produkt-ISIN ist erforderlich.")
        self.session.add(
            WarrantValuationEvidenceModel(
                id=uuid4(),
                workspace_id=workspace_id,
                warrant_id=warrant_id,
                terms_id=terms_id,
                revision=view.revision + 1,
                identity_key=evidence_identity(warrant, terms_id),
                recorded_at=now,
                actor_id=actor_id,
                payload={
                    "facts": facts.model_dump(mode="json"),
                    "identity": {
                        "isin": warrant.isin,
                        "wkn": warrant.wkn,
                        "issuer_id": str(warrant.issuer_id),
                        "underlying_id": str(warrant.underlying_id),
                    },
                },
            )
        )
        await self.session.commit()
        return await self.view(workspace_id, warrant_id, now)
