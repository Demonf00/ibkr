import math

from models import Signal, SignalAction
from .base import StrategyBase


class QualityTrendRotationStrategy(StrategyBase):
    """
    Quality Trend Rotation:

    逻辑：
    1. 对 ETF universe 计算分数
    2. 要求 price > long_ma 才允许 BUY
    3. 分数 = 0.6 * slow_momentum + 0.4 * fast_momentum - volatility_penalty * volatility
    4. 买入 top_n
    5. 跌破 long_ma 或分数太差给 SELL/exit signal

    注意：
    SELL 在这里更像“退出/减仓信号”，不是鼓励裸 short。
    真实下单前应该加入 position-aware order manager。
    """

    def __init__(
        self,
        name: str,
        symbols: list[str],
        weight: float = 1.0,
        top_n: int = 2,
        fast_lookback: int = 63,
        slow_lookback: int = 126,
        long_ma: int = 200,
        vol_window: int = 20,
        volatility_penalty: float = 0.5,
        min_score: float = 0.02,
        quantity: int = 1,
        duration: str = "1 Y",
        bar_size: str = "1 day",
    ):
        super().__init__(name=name, symbols=symbols, weight=weight)

        self.top_n = top_n
        self.fast_lookback = fast_lookback
        self.slow_lookback = slow_lookback
        self.long_ma = long_ma
        self.vol_window = vol_window
        self.volatility_penalty = volatility_penalty
        self.min_score = min_score
        self.quantity = quantity
        self.duration = duration
        self.bar_size = bar_size

    def _score_symbol(self, broker, symbol: str) -> dict:
        df = broker.get_historical_bars(
            symbol=symbol,
            duration=self.duration,
            bar_size=self.bar_size,
        )

        if "close" not in df.columns:
            raise ValueError(f"No close column for {symbol}")

        required = max(
            self.fast_lookback,
            self.slow_lookback,
            self.long_ma,
            self.vol_window,
        ) + 2

        if len(df) < required:
            raise ValueError(f"Not enough bars for {symbol}. Need {required}, got {len(df)}")

        close = df["close"].astype(float)

        current = float(close.iloc[-1])
        fast_past = float(close.iloc[-self.fast_lookback - 1])
        slow_past = float(close.iloc[-self.slow_lookback - 1])

        fast_momentum = current / fast_past - 1.0
        slow_momentum = current / slow_past - 1.0

        ma = float(close.rolling(self.long_ma).mean().iloc[-1])

        daily_returns = close.pct_change().dropna()
        volatility = float(daily_returns.tail(self.vol_window).std() * math.sqrt(252))

        trend_ok = current > ma

        score = (
            0.4 * fast_momentum
            + 0.6 * slow_momentum
            - self.volatility_penalty * volatility
        )

        return {
            "symbol": symbol,
            "current": current,
            "long_ma": ma,
            "trend_ok": trend_ok,
            "fast_momentum": fast_momentum,
            "slow_momentum": slow_momentum,
            "volatility": volatility,
            "score": score,
        }

    def generate_signals(self, broker):
        results = []
        signals = []

        for symbol in self.symbols:
            try:
                results.append(self._score_symbol(broker, symbol))
            except Exception as exc:
                signals.append(
                    Signal(
                        strategy_name=self.name,
                        symbol=symbol,
                        action=SignalAction.HOLD,
                        quantity=0,
                        confidence=0.0,
                        reason=f"QualityTrend error: {exc}",
                    )
                )

        tradable = [
            r for r in results
            if r["trend_ok"] and r["score"] >= self.min_score
        ]

        ranked = sorted(
            tradable,
            key=lambda x: x["score"],
            reverse=True,
        )

        buy_symbols = {r["symbol"] for r in ranked[: self.top_n]}

        for r in results:
            symbol = r["symbol"]
            score = r["score"]

            # 简单 edge 估算：score 转成 bps，上限 500bps
            expected_edge_bps = min(abs(score) * 10_000, 500)

            if symbol in buy_symbols:
                action = SignalAction.BUY
                quantity = self.quantity
                confidence = min(max(score / 0.10, 0.1), 1.0)
                reason = (
                    f"QualityTrend BUY: score={score:.3f}, "
                    f"fast_mom={r['fast_momentum']:.2%}, "
                    f"slow_mom={r['slow_momentum']:.2%}, "
                    f"vol={r['volatility']:.2%}, "
                    f"price={r['current']:.2f}, ma{self.long_ma}={r['long_ma']:.2f}"
                )

            elif not r["trend_ok"] or score < 0:
                action = SignalAction.SELL
                quantity = self.quantity
                confidence = min(abs(score) / 0.10, 1.0)
                reason = (
                    f"QualityTrend SELL/EXIT: score={score:.3f}, "
                    f"trend_ok={r['trend_ok']}, "
                    f"price={r['current']:.2f}, ma{self.long_ma}={r['long_ma']:.2f}"
                )

            else:
                action = SignalAction.HOLD
                quantity = 0
                confidence = 0.0
                reason = (
                    f"QualityTrend HOLD: score={score:.3f}, "
                    f"trend_ok={r['trend_ok']}"
                )

            signals.append(
                Signal(
                    strategy_name=self.name,
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    confidence=confidence,
                    reason=reason,
                    expected_edge_bps=expected_edge_bps,
                )
            )

        return signals