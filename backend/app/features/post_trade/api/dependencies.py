"""Request-scoped dependencies for FT-011 Post Trade."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.post_trade.application.exit_review_service import (
    ExitReviewService,
)
from app.features.post_trade.application.handoff_service import (
    Ft012HandoffService,
)
from app.features.post_trade.application.observation_service import (
    PostTradeObservationService,
)
from app.features.post_trade.application.query_service import (
    PostTradeQueryService,
)
from app.features.post_trade.application.read_adapters import (
    SqlAlchemyHistoricalPlanningContextReader,
    SqlAlchemyHistoricalProductContextReader,
    SqlAlchemyObservationMarketDataReader,
    SqlAlchemyTradeExitContextReader,
    SqlAlchemyUnderlyingListingResolver,
)
from app.features.post_trade.persistence.unit_of_work import (
    SqlAlchemyPostTradeLearningUnitOfWork,
)


def get_post_trade_observation_service(
    session: Annotated[
        AsyncSession,
        Depends(get_database_session),
    ],
) -> PostTradeObservationService:
    return PostTradeObservationService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(session),
        trade_reader=SqlAlchemyTradeExitContextReader(session),
        planning_reader=SqlAlchemyHistoricalPlanningContextReader(session),
        product_reader=SqlAlchemyHistoricalProductContextReader(session),
        listing_resolver=SqlAlchemyUnderlyingListingResolver(session),
        market_data_reader=SqlAlchemyObservationMarketDataReader(session),
    )


def get_exit_review_service(
    session: Annotated[
        AsyncSession,
        Depends(get_database_session),
    ],
) -> ExitReviewService:
    return ExitReviewService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(session),
        trade_reader=SqlAlchemyTradeExitContextReader(session),
        planning_reader=SqlAlchemyHistoricalPlanningContextReader(session),
        market_data_reader=SqlAlchemyObservationMarketDataReader(session),
    )


def get_ft012_handoff_service(
    session: Annotated[
        AsyncSession,
        Depends(get_database_session),
    ],
) -> Ft012HandoffService:
    return Ft012HandoffService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(session),
    )


def get_post_trade_query_service(
    session: Annotated[
        AsyncSession,
        Depends(get_database_session),
    ],
) -> PostTradeQueryService:
    return PostTradeQueryService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(session),
        trade_reader=SqlAlchemyTradeExitContextReader(session),
        planning_reader=SqlAlchemyHistoricalPlanningContextReader(session),
        product_reader=SqlAlchemyHistoricalProductContextReader(session),
    )
