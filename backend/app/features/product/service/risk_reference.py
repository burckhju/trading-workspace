"""Public immutable product facts for descriptive risk consumers."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantModel, WarrantTermsVersionModel
from app.features.product.service.valuation_evidence import current_evidence


@dataclass(frozen=True, slots=True)
class RiskProductReference:
    warrant_id: UUID
    underlying_id: UUID
    name: str
    isin: str | None
    wkn: str | None
    terms_id: UUID | None
    direction: str | None
    ratio: Decimal | None
    strike: Decimal | None
    strike_currency: str | None
    maturity: date | None
    exercise_style: str | None = None
    quanto: bool | None = None
    # WARRANT alone does not prove a vanilla payoff or a ratio convention.
    product_type: str | None = None
    ratio_convention: str | None = None
    issuer_id: UUID | None = None
    expiry_at: datetime | None = None
    evidence_revision: int | None = None
    evidence_origin: str | None = None
    evidence_document: str | None = None


class RiskProductReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def read(
        self, *, workspace_id: UUID, warrant_id: UUID, as_of: datetime
    ) -> RiskProductReference | None:
        warrant = await self._session.scalar(
            select(WarrantModel).where(
                WarrantModel.workspace_id == workspace_id,
                WarrantModel.id == warrant_id,
                WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
            )
        )
        if warrant is None:
            return None
        terms = (
            await self._session.scalars(
                select(WarrantTermsVersionModel).where(
                    WarrantTermsVersionModel.warrant_id == warrant_id,
                    WarrantTermsVersionModel.effective_from <= as_of,
                    WarrantTermsVersionModel.created_at <= as_of,
                    or_(
                        WarrantTermsVersionModel.effective_to.is_(None),
                        WarrantTermsVersionModel.effective_to > as_of,
                    ),
                )
            )
        ).all()
        term = terms[0] if len(terms) == 1 else None
        evidence = await current_evidence(self._session, warrant, term.id, as_of) if term else None
        facts = evidence.facts if evidence else None
        return RiskProductReference(
            warrant.id,
            warrant.underlying_id,
            warrant.display_name,
            warrant.isin,
            warrant.wkn,
            term.id if term else None,
            term.option_direction.value if term else None,
            term.ratio if term else None,
            term.strike if term else None,
            term.strike_currency_code if term else None,
            term.maturity_date if term else None,
            issuer_id=warrant.issuer_id,
            product_type=facts.product_type if facts else None,
            exercise_style=facts.exercise_style if facts else None,
            quanto=facts.quanto if facts else None,
            ratio_convention=facts.ratio_convention if facts else None,
            expiry_at=facts.expiry_at if facts else None,
            evidence_revision=evidence.revision if evidence else None,
            evidence_origin=evidence.origin if evidence else None,
            evidence_document=facts.document_reference if facts else None,
        )
