from brokers.mock_broker import MockBroker
from execution.order_manager import OrderManager
from models import Signal, SignalAction
from risk.risk_manager import RiskManager


def make_config():
    return {
        "trading": {
            "enabled": True,
            "allowed_symbols": ["SPY"],
            "max_order_value": 1000,
            "max_daily_orders": 3,
            "allow_short": False,
            "allow_options": False,
        },
        "strategy_limits": {
            "ma_cross": {"max_daily_orders": 3},
        },
    }


def test_order_manager_dry_run_does_not_place_order():
    broker = MockBroker()
    risk = RiskManager(make_config())

    manager = OrderManager(
        broker=broker,
        risk_manager=risk,
        dry_run=True,
    )

    signal = Signal(
        strategy_name="aggregate",
        symbol="SPY",
        action=SignalAction.BUY,
        quantity=1,
        confidence=1.0,
        reason="test buy",
        source_strategies=["ma_cross"],
    )

    manager.handle_signal(signal)

    assert broker.orders == []


def test_order_manager_places_order_when_not_dry_run():
    broker = MockBroker()
    risk = RiskManager(make_config())

    manager = OrderManager(
        broker=broker,
        risk_manager=risk,
        dry_run=False,
    )

    signal = Signal(
        strategy_name="aggregate",
        symbol="SPY",
        action=SignalAction.BUY,
        quantity=1,
        confidence=1.0,
        reason="test buy",
        source_strategies=["ma_cross"],
    )

    manager.handle_signal(signal)

    assert len(broker.orders) == 1
    assert broker.orders[0]["symbol"] == "SPY"
    assert broker.orders[0]["side"] == "BUY"
    assert broker.orders[0]["quantity"] == 1


def test_order_manager_hold_does_nothing():
    broker = MockBroker()
    risk = RiskManager(make_config())

    manager = OrderManager(
        broker=broker,
        risk_manager=risk,
        dry_run=False,
    )

    signal = Signal(
        strategy_name="aggregate",
        symbol="SPY",
        action=SignalAction.HOLD,
        quantity=0,
        confidence=0.0,
        reason="hold",
    )

    manager.handle_signal(signal)

    assert broker.orders == []