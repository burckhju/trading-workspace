from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.product.domain.models import OptionDirection, WarrantTermsVersion


def test_ratio_semantics_requires_positive_value() -> None:
    with pytest.raises(ValueError, match="ratio"):
        WarrantTermsVersion(
            id=uuid4(),
            warrant_id=uuid4(),
            version_no=1,
            effective_from=datetime.now(UTC),
            effective_to=None,
            option_direction=OptionDirection.CALL,
            strike=Decimal("100"),
            maturity_date=date(2027, 1, 1),
            ratio=Decimal("0"),
            created_at=datetime.now(UTC),
        )


def test_terms_allow_ratio_point_one() -> None:
    terms = WarrantTermsVersion(
        id=uuid4(),
        warrant_id=uuid4(),
        version_no=1,
        effective_from=datetime.now(UTC),
        effective_to=None,
        option_direction=OptionDirection.PUT,
        strike=Decimal("150"),
        maturity_date=date(2027, 6, 18),
        ratio=Decimal("0.1"),
        created_at=datetime.now(UTC),
    )
    assert terms.ratio == Decimal("0.1")
