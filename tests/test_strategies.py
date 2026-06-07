from brokers.mock_broker import MockBroker
from models import SignalAction
from strategies.idle_strategy import IdleStrategy
from strategies.ma_cross import MaCrossStrategy
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.breakout import BreakoutStrategy
from strategies.quality_trend_rotation import QualityTrendRotationStrategy


def assert_valid_signals(signals, expected_symbols):
    assert len(signals) == len(expected_symbols)

    for signal in signals:
        assert signal.symbol in expected_symbols
        assert signal.action in {
            SignalAction.BUY,
            SignalAction.SELL,
            SignalAction.HOLD,
        }


def test_idle_strategy_generates_hold_signals():
    broker = MockBroker()

    strategy = IdleStrategy(
        name="idle",
        symbols=["SPY", "QQQ"],
        weight=1.0,
    )

    signals = strategy.generate_signals(broker)

    assert_valid_signals(signals, {"SPY", "QQQ"})
    assert all(s.action == SignalAction.HOLD for s in signals)


def test_ma_cross_strategy_generates_valid_signals():
    broker = MockBroker()

    strategy = MaCrossStrategy(
        name="ma_cross",
        symbols=["SPY", "QQQ"],
        weight=1.0,
        fast_ma=10,
        slow_ma=30,
        quantity=1,
    )

    signals = strategy.generate_signals(broker)

    assert_valid_signals(signals, {"SPY", "QQQ"})


def test_momentum_strategy_generates_valid_signals():
    broker = MockBroker()

    strategy = MomentumStrategy(
        name="momentum",
        symbols=["SPY", "QQQ"],
        weight=1.0,
        lookback=20,
        buy_threshold=0.05,
        sell_threshold=-0.05,
        quantity=1,
    )

    signals = strategy.generate_signals(broker)

    assert_valid_signals(signals, {"SPY", "QQQ"})


def test_mean_reversion_strategy_generates_valid_signals():
    broker = MockBroker()

    strategy = MeanReversionStrategy(
        name="mean_reversion",
        symbols=["SPY", "QQQ"],
        weight=1.0,
        ma_window=20,
        buy_deviation=-0.03,
        sell_deviation=0.03,
        quantity=1,
    )

    signals = strategy.generate_signals(broker)

    assert_valid_signals(signals, {"SPY", "QQQ"})


def test_breakout_strategy_generates_valid_signals():
    broker = MockBroker()

    strategy = BreakoutStrategy(
        name="breakout",
        symbols=["SPY", "QQQ"],
        weight=1.0,
        lookback=20,
        quantity=1,
    )

    signals = strategy.generate_signals(broker)

    assert_valid_signals(signals, {"SPY", "QQQ"})


def test_quality_trend_rotation_strategy_does_not_crash():
    broker = MockBroker()

    # MockBroker 默认只有 80 根 bar，所以这里把 lookback 调小，
    # 否则 long_ma=200 会因为数据不足而只出 error/HOLD。
    strategy = QualityTrendRotationStrategy(
        name="quality_trend_rotation",
        symbols=["SPY", "QQQ", "GLD"],
        weight=1.0,
        top_n=1,
        fast_lookback=10,
        slow_lookback=30,
        long_ma=50,
        vol_window=10,
        quantity=1,
        duration="3 M",
        bar_size="1 day",
    )

    signals = strategy.generate_signals(broker)

    assert_valid_signals(signals, {"SPY", "QQQ", "GLD"})