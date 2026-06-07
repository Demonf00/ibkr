import pytest

from models import OrderRequest, SignalAction
from risk.risk_manager import RiskManager


def make_config():
    return {
        "trading": {
            "enabled": True,
            "allowed_symbols": ["SPY", "QQQ"],
            "max_order_value": 1000,
            "max_daily_orders": 1,
            "allow_short": False,
            "allow_options": False,
        },
        "strategy_limits": {
            "ma_cross": {"max_daily_orders": 1},
            "momentum": {"max_daily_orders": 1},
        },
    }


def test_valid_buy_order_passes():
    risk = RiskManager(make_config())

    order = OrderRequest(
        symbol="SPY",
        side=SignalAction.BUY,
        quantity=1,
        strategy_name="ma_cross",
    )

    risk.validate_order(order, price=500.0)


def test_trading_disabled_blocks_order():
    config = make_config()
    config["trading"]["enabled"] = False

    risk = RiskManager(config)

    order = OrderRequest(
        symbol="SPY",
        side=SignalAction.BUY,
        quantity=1,
        strategy_name="ma_cross",
    )

    with pytest.raises(RuntimeError, match="Trading is disabled"):
        risk.validate_order(order, price=500.0)


def test_symbol_not_allowed_blocks_order():
    risk = RiskManager(make_config())

    order = OrderRequest(
        symbol="AAPL",
        side=SignalAction.BUY,
        quantity=1,
        strategy_name="ma_cross",
    )

    with pytest.raises(RuntimeError, match="Symbol not allowed"):
        risk.validate_order(order, price=200.0)


def test_order_value_limit_blocks_order():
    risk = RiskManager(make_config())

    order = OrderRequest(
        symbol="SPY",
        side=SignalAction.BUY,
        quantity=3,
        strategy_name="ma_cross",
    )

    with pytest.raises(RuntimeError, match="Order value too large"):
        risk.validate_order(order, price=500.0)


def test_short_selling_disabled_blocks_sell():
    risk = RiskManager(make_config())

    order = OrderRequest(
        symbol="SPY",
        side=SignalAction.SELL,
        quantity=1,
        strategy_name="ma_cross",
    )

    with pytest.raises(RuntimeError, match="Short selling is disabled"):
        risk.validate_order(order, price=500.0)


def test_daily_limit_is_per_strategy_not_shared():
    risk = RiskManager(make_config())

    ma_order = OrderRequest(
        symbol="SPY",
        side=SignalAction.BUY,
        quantity=1,
        strategy_name="ma_cross",
    )

    momentum_order = OrderRequest(
        symbol="QQQ",
        side=SignalAction.BUY,
        quantity=1,
        strategy_name="momentum",
    )

    risk.validate_order(ma_order, price=500.0)
    risk.record_order(ma_order)

    # momentum 还应该能下，因为 daily limit 不共享
    risk.validate_order(momentum_order, price=400.0)
    risk.record_order(momentum_order)

    # ma_cross 第二单应该被挡
    with pytest.raises(RuntimeError, match="Max daily orders reached for strategy=ma_cross"):
        risk.validate_order(ma_order, price=500.0)