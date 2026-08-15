"""Architecture compatibility contracts for FT-003 Issuer reference data."""

from dataclasses import fields

from app.features.market.persistence.models import IssuerModel
from app.features.trade_plan.domain.models import TradePlan, TradePlanVersion
from app.features.trade_plan.persistence.models import TradePlanModel, TradePlanVersionModel
from app.providers.eodhd.dto import EodhdSearchResultDto


FORBIDDEN_TRADE_PLAN_PRODUCT_FIELDS = {
    "issuer_id",
    "warrant_id",
    "trading_venue_id",
    "provider_identifier",
    "leverage",
    "spread",
    "ratio",
    "expiry",
    "order_quantity",
    "product_price",
}


def test_issuer_identity_is_global_and_provider_neutral() -> None:
    columns = set(IssuerModel.__table__.columns.keys())

    assert "id" in columns
    assert "workspace_id" not in columns
    assert "underlying_id" not in columns
    assert "trading_venue_id" not in columns
    assert "provider_id" not in columns
    assert "provider_issuer_id" not in columns


def test_trade_plan_domain_remains_product_neutral() -> None:
    domain_fields = {field.name for field in fields(TradePlan)} | {
        field.name for field in fields(TradePlanVersion)
    }

    assert domain_fields.isdisjoint(FORBIDDEN_TRADE_PLAN_PRODUCT_FIELDS)


def test_trade_plan_persistence_remains_product_neutral() -> None:
    persistence_columns = set(TradePlanModel.__table__.columns.keys()) | set(
        TradePlanVersionModel.__table__.columns.keys()
    )

    assert persistence_columns.isdisjoint(FORBIDDEN_TRADE_PLAN_PRODUCT_FIELDS)


def test_eodhd_search_contract_has_no_reliable_issuer_identity() -> None:
    provider_fields = set(EodhdSearchResultDto.model_fields)

    assert "issuer" not in provider_fields
    assert "issuer_id" not in provider_fields
    assert "lei" not in provider_fields
