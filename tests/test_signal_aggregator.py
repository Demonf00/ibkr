from models import Signal, SignalAction
from execution.cost_model import TradingCostModel
from execution.signal_aggregator import SignalAggregator


class FixedPriceBroker:
    def get_market_price(self, symbol: str) -> float:
        prices = {
            "SPY": 500.0,
            "QQQ": 400.0,
        }
        return prices[symbol]


def make_aggregator(
    buy_threshold=0.35,
    sell_threshold=-0.35,
    cost_gate_enabled=True,
):
    cost_model = TradingCostModel(
        commission_per_share=0.0,
        min_commission=0.0,
        slippage_bps=2.0,
    )

    return SignalAggregator(
        strategy_weights={
            "ma_cross": 0.5,
            "momentum": 0.5,
            "mean_reversion": 0.5,
        },
        cost_model=cost_model,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        default_quantity=1,
        cost_gate_enabled=cost_gate_enabled,
        min_edge_buffer_bps=5.0,
    )


def test_aggregator_buy_when_weighted_score_high_enough():
    broker = FixedPriceBroker()
    aggregator = make_aggregator()

    raw = [
        Signal(
            strategy_name="ma_cross",
            symbol="SPY",
            action=SignalAction.BUY,
            quantity=1,
            confidence=1.0,
            expected_edge_bps=50.0,
        )
    ]

    final = aggregator.aggregate(raw, broker)

    assert len(final) == 1
    assert final[0].symbol == "SPY"
    assert final[0].action == SignalAction.BUY
    assert final[0].quantity == 1
    assert "ma_cross" in final[0].source_strategies


def test_aggregator_hold_when_signals_conflict():
    broker = FixedPriceBroker()
    aggregator = make_aggregator()

    raw = [
        Signal(
            strategy_name="ma_cross",
            symbol="SPY",
            action=SignalAction.BUY,
            quantity=1,
            confidence=1.0,
            expected_edge_bps=50.0,
        ),
        Signal(
            strategy_name="momentum",
            symbol="SPY",
            action=SignalAction.SELL,
            quantity=1,
            confidence=1.0,
            expected_edge_bps=50.0,
        ),
    ]

    final = aggregator.aggregate(raw, broker)

    assert final[0].action == SignalAction.HOLD


def test_aggregator_cost_gate_blocks_low_edge_trade():
    broker = FixedPriceBroker()
    aggregator = make_aggregator(cost_gate_enabled=True)

    raw = [
        Signal(
            strategy_name="ma_cross",
            symbol="SPY",
            action=SignalAction.BUY,
            quantity=1,
            confidence=1.0,
            expected_edge_bps=1.0,
        )
    ]

    final = aggregator.aggregate(raw, broker)

    assert final[0].action == SignalAction.HOLD


def test_aggregator_can_disable_cost_gate():
    broker = FixedPriceBroker()
    aggregator = make_aggregator(cost_gate_enabled=False)

    raw = [
        Signal(
            strategy_name="ma_cross",
            symbol="SPY",
            action=SignalAction.BUY,
            quantity=1,
            confidence=1.0,
            expected_edge_bps=0.0,
        )
    ]

    final = aggregator.aggregate(raw, broker)

    assert final[0].action == SignalAction.BUY