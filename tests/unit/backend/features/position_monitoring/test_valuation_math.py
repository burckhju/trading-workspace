from decimal import Decimal


def test_long_bid_mark_math_is_gross_and_transparent() -> None:
    open_quantity = 100
    bid = Decimal("2.40")
    remaining_cost_basis = Decimal("200.00")

    market_value = Decimal(open_quantity) * bid
    unrealized_gross_pnl = market_value - remaining_cost_basis

    assert market_value == Decimal("240.00")
    assert unrealized_gross_pnl == Decimal("40.00")
