"""Dependencies for FT-011 -> FT-012 LearningEvidence materialization."""

from typing import Annotated, cast

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.learning.api.dependencies import UtcClock, UuidFactory
from app.features.learning.application.ft011_materialization_service import (
    MaterializeFt011LearningEvidenceService,
)
from app.features.learning.application.ft011_materialization_status_service import (
    Ft011MaterializationStatusService,
)
from app.features.learning.persistence.ft011_materialization_repository import (
    SqlAlchemyFt011MaterializationRepository,
)
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
    SqlAlchemyLearningTradeLinkUnitOfWork,
)
from app.features.post_trade.application.handoff_service import Ft012HandoffService
from app.features.post_trade.persistence.unit_of_work import (
    PostTradeLearningUnitOfWork,
    SqlAlchemyPostTradeLearningUnitOfWork,
)


def _handoff_reader(session: AsyncSession) -> Ft012HandoffService:
    post_trade_uow = cast(
        PostTradeLearningUnitOfWork,
        SqlAlchemyPostTradeLearningUnitOfWork(session),
    )
    return Ft012HandoffService(uow=post_trade_uow)


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
        handoff_reader=_handoff_reader(session),
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
