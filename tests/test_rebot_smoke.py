from brokers.mock_broker import MockBroker
from execution.cost_model import TradingCostModel
from execution.order_manager import OrderManager
from execution.signal_aggregator import SignalAggregator
from risk.risk_manager import RiskManager
from strategies.strategy_manager import StrategyManager


def test_one_robot_cycle_with_mock_broker():
    config = {
        "runtime": {
            "dry_run": True,
        },
        "trading": {
            "enabled": True,
            "allowed_symbols": ["SPY", "QQQ"],
            "max_order_value": 1000,
            "max_daily_orders": 3,
            "allow_short": False,
            "allow_options": False,
        },
        "cost_model": {
            "commission_per_share": 0.005,
            "min_commission": 1.0,
            "slippage_bps": 2.0,
        },
        "aggregate": {
            "buy_threshold": 0.35,
            "sell_threshold": -0.35,
            "default_quantity": 1,
            "cost_gate_enabled": False,
            "min_edge_buffer_bps": 5.0,
        },
        "strategy_limits": {
            "ma_cross": {"max_daily_orders": 3},
            "momentum": {"max_daily_orders": 3},
        },
        "strategies": [
            {
                "name": "ma_cross",
                "enabled": True,
                "weight": 0.5,
                "symbols": ["SPY", "QQQ"],
                "params": {
                    "fast_ma": 10,
                    "slow_ma": 30,
                    "quantity": 1,
                    "duration": "3 M",
                    "bar_size": "1 day",
                },
            },
            {
                "name": "momentum",
                "enabled": True,
                "weight": 0.5,
                "symbols": ["SPY", "QQQ"],
                "params": {
                    "lookback": 20,
                    "buy_threshold": 0.05,
                    "sell_threshold": -0.05,
                    "quantity": 1,
                    "duration": "3 M",
                    "bar_size": "1 day",
                },
            },
        ],
    }

    broker = MockBroker()
    broker.connect()

    strategy_manager = StrategyManager(config["strategies"])
    risk_manager = RiskManager(config)

    cost_model = TradingCostModel(
        commission_per_share=config["cost_model"]["commission_per_share"],
        min_commission=config["cost_model"]["min_commission"],
        slippage_bps=config["cost_model"]["slippage_bps"],
    )

    strategy_weights = {
        s["name"]: s["weight"]
        for s in config["strategies"]
        if s["enabled"]
    }

    aggregator = SignalAggregator(
        strategy_weights=strategy_weights,
        cost_model=cost_model,
        buy_threshold=config["aggregate"]["buy_threshold"],
        sell_threshold=config["aggregate"]["sell_threshold"],
        default_quantity=config["aggregate"]["default_quantity"],
        cost_gate_enabled=config["aggregate"]["cost_gate_enabled"],
        min_edge_buffer_bps=config["aggregate"]["min_edge_buffer_bps"],
    )

    order_manager = OrderManager(
        broker=broker,
        risk_manager=risk_manager,
        dry_run=True,
    )

    raw_signals = strategy_manager.generate_all_signals(broker)
    assert len(raw_signals) > 0

    final_signals = aggregator.aggregate(raw_signals, broker)
    assert len(final_signals) > 0

    for signal in final_signals:
        order_manager.handle_signal(signal)

    # dry_run=True，所以不应该真的下 mock order
    assert broker.orders == []

    broker.disconnect()