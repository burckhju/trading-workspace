"""Dependencies for FT-011 -> FT-012 LearningEvidence materialization."""

from typing import Annotated, cast

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.learning.api.dependencies import UtcClock, UuidFactory
from app.features.learning.application.ft011_evidence_history_service import (
    Ft011EvidenceHistoryService,
)
from app.features.learning.application.ft011_materialization_service import (
    MaterializeFt011LearningEvidenceService,
)
from app.features.learning.application.ft011_materialization_status_service import (
    Ft011MaterializationStatusService,
)
from app.features.learning.persistence.ft011_materialization_repository import (
    SqlAlchemyFt011MaterializationRepository,
)
from app.features.learning.persistence.lesson_evidence_read_repository import (
    SqlAlchemyLessonEvidenceReadRepository,
)
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
    SqlAlchemyLearningTradeLinkUnitOfWork,
)
from app.features.post_trade.api.dependencies import (
    build_inspected_ft012_handoff_service,
    get_exit_review_service,
)
from app.features.post_trade.application.materialization_handoff import InspectedFt012HandoffService
from app.features.post_trade.persistence.materialization_guard import (
    SqlAlchemyMaterializationSourceGuard,
)


def _handoff_reader(
    session: AsyncSession, *, guarded: bool = False
) -> InspectedFt012HandoffService:
    return build_inspected_ft012_handoff_service(
        session,
        guard=SqlAlchemyMaterializationSourceGuard(session) if guarded else None,
    )


def get_ft011_materialization_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> MaterializeFt011LearningEvidenceService:
    learning_uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return MaterializeFt011LearningEvidenceService(
        uow=learning_uow,
        repository=SqlAlchemyFt011MaterializationRepository(session),
        handoff_reader=_handoff_reader(session, guarded=True),
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )


def get_ft011_materialization_status_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> Ft011MaterializationStatusService:
    return Ft011MaterializationStatusService(
        repository=SqlAlchemyFt011MaterializationRepository(session),
        handoff_reader=_handoff_reader(session),
    )


def get_ft011_evidence_history_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> Ft011EvidenceHistoryService:
    return Ft011EvidenceHistoryService(
        repository=SqlAlchemyFt011MaterializationRepository(session),
        inspector=get_exit_review_service(session),
        lessons=SqlAlchemyLessonEvidenceReadRepository(session),
        clock=UtcClock(),
    )
