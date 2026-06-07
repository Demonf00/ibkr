import pytest

from execution.cost_model import TradingCostModel


def test_cost_model_estimates_min_commission_and_slippage():
    model = TradingCostModel(
        commission_per_share=0.005,
        min_commission=1.0,
        slippage_bps=2.0,
    )

    cost = model.estimate(price=100.0, quantity=10)

    assert cost["commission"] == pytest.approx(1.0)
    assert cost["slippage"] == pytest.approx(0.2)
    assert cost["total_cost"] == pytest.approx(1.2)
    assert cost["cost_bps"] == pytest.approx(12.0)


def test_cost_model_zero_trade_value():
    model = TradingCostModel()

    cost = model.estimate(price=0.0, quantity=10)

    assert cost["commission"] == 0.0
    assert cost["slippage"] == 0.0
    assert cost["total_cost"] == 0.0
    assert cost["cost_bps"] == 0.0