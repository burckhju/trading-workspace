"""Existing FT-011 owner and FT-012 UOW for journal commands/readback."""

from typing import Annotated, cast

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.learning.api.dependencies import UtcClock, UuidFactory
from app.features.learning.application.journal_service import JournalService
from app.features.learning.application.read_adapters import SqlAlchemyTradeReader
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
    SqlAlchemyLearningTradeLinkUnitOfWork,
)
from app.features.post_trade.api.dependencies import (
    get_exit_review_service,
    get_ft012_handoff_service,
)


def get_journal_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> JournalService:
    return JournalService(
        uow=cast(LearningTradeLinkUnitOfWork, SqlAlchemyLearningTradeLinkUnitOfWork(session)),
        trade_reader=SqlAlchemyTradeReader(session),
        handoff_reader=get_ft012_handoff_service(session),
        inspector=get_exit_review_service(session),
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )
