"""Request-scoped dependencies for FT-012 Learning."""

from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.learning.application.execute_as_trade_service import (
    ExecuteExternalObservationAsTradeService,
)
from app.features.learning.application.external_trade_creator import SqlAlchemyExternalTradeCreator
from app.features.learning.application.learning_evidence_query_service import (
    LearningEvidenceQueryService,
)
from app.features.learning.application.lesson_query_service import LessonQueryService
from app.features.learning.application.lesson_review_service import LessonReviewService
from app.features.learning.application.lesson_service import LessonService
from app.features.learning.application.lesson_suggestion_service import LessonSuggestionService
from app.features.learning.application.read_adapters import (
    SqlAlchemyProductReader,
    SqlAlchemyTradeReader,
)
from app.features.learning.application.review_suggestion_query_service import (
    ReviewSuggestionQueryService,
)
from app.features.learning.application.trade_link_projection_service import (
    TradeLinkProjectionService,
)
from app.features.learning.application.trade_link_query_service import TradeLinkQueryService
from app.features.learning.application.trade_link_service import (
    ExternalObservationTradeLinkService,
)
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
    SqlAlchemyLearningTradeLinkUnitOfWork,
)


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidFactory:
    def new_uuid(self) -> UUID:
        return uuid4()


def get_trade_link_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ExternalObservationTradeLinkService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return ExternalObservationTradeLinkService(
        uow=uow,
        trade_reader=SqlAlchemyTradeReader(session),
        product_reader=SqlAlchemyProductReader(session),
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )


def get_trade_link_projection_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TradeLinkProjectionService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return TradeLinkProjectionService(
        uow=uow,
        trade_reader=SqlAlchemyTradeReader(session),
        product_reader=SqlAlchemyProductReader(session),
    )


def get_trade_link_query_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TradeLinkQueryService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    projection = TradeLinkProjectionService(
        uow=uow,
        trade_reader=SqlAlchemyTradeReader(session),
        product_reader=SqlAlchemyProductReader(session),
    )
    return TradeLinkQueryService(
        uow=uow,
        projection_service=projection,
    )


def get_execute_as_trade_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ExecuteExternalObservationAsTradeService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    trade_link_service = ExternalObservationTradeLinkService(
        uow=uow,
        trade_reader=SqlAlchemyTradeReader(session),
        product_reader=SqlAlchemyProductReader(session),
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )
    return ExecuteExternalObservationAsTradeService(
        session=session,
        uow=uow,
        external_trade_creator=SqlAlchemyExternalTradeCreator(session),
        trade_link_service=trade_link_service,
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )


def get_learning_evidence_query_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LearningEvidenceQueryService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return LearningEvidenceQueryService(uow=uow)


def get_lesson_query_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LessonQueryService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return LessonQueryService(uow=uow)


def get_lesson_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LessonService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return LessonService(
        uow=uow,
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )


def get_lesson_review_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LessonReviewService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return LessonReviewService(
        uow=uow,
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )


def get_lesson_suggestion_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LessonSuggestionService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return LessonSuggestionService(
        uow=uow,
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )


def get_review_suggestion_query_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ReviewSuggestionQueryService:
    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(session),
    )
    return ReviewSuggestionQueryService(uow=uow)
