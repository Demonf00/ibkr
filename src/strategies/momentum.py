from models import Signal, SignalAction
from .base import StrategyBase


class MomentumStrategy(StrategyBase):
    """
    Momentum 策略：

    如果最近 lookback 天涨幅 > buy_threshold，则 BUY
    如果最近 lookback 天跌幅 < sell_threshold，则 SELL
    否则 HOLD
    """

    def __init__(
        self,
        name: str,
        symbols: list[str],
        weight: float = 1.0,
        lookback: int = 20,
        buy_threshold: float = 0.05,
        sell_threshold: float = -0.05,
        quantity: int = 1,
        duration: str = "3 M",
        bar_size: str = "1 day",
    ):
        super().__init__(name=name, symbols=symbols, weight=weight)

        self.lookback = lookback
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.quantity = quantity
        self.duration = duration
        self.bar_size = bar_size

    def generate_signals(self, broker):
        signals = []

        for symbol in self.symbols:
            try:
                df = broker.get_historical_bars(
                    symbol=symbol,
                    duration=self.duration,
                    bar_size=self.bar_size,
                )

                if "close" not in df.columns:
                    raise ValueError(f"No close column for {symbol}")

                if len(df) < self.lookback + 1:
                    signals.append(
                        Signal(
                            strategy_name=self.name,
                            symbol=symbol,
                            action=SignalAction.HOLD,
                            quantity=0,
                            confidence=0.0,
                            reason=f"Not enough bars. Need {self.lookback + 1}, got {len(df)}",
                        )
                    )
                    continue

                old_price = float(df["close"].iloc[-self.lookback - 1])
                current_price = float(df["close"].iloc[-1])

                ret = (current_price - old_price) / old_price

                if ret >= self.buy_threshold:
                    action = SignalAction.BUY
                    quantity = self.quantity
                    confidence = min(abs(ret) / self.buy_threshold, 1.0)
                    reason = f"Momentum BUY: {self.lookback}d return={ret:.2%}"

                elif ret <= self.sell_threshold:
                    action = SignalAction.SELL
                    quantity = self.quantity
                    confidence = min(abs(ret) / abs(self.sell_threshold), 1.0)
                    reason = f"Momentum SELL: {self.lookback}d return={ret:.2%}"

                else:
                    action = SignalAction.HOLD
                    quantity = 0
                    confidence = 0.0
                    reason = f"Momentum HOLD: {self.lookback}d return={ret:.2%}"

                signals.append(
                    Signal(
                        strategy_name=self.name,
                        symbol=symbol,
                        action=action,
                        quantity=quantity,
                        confidence=confidence,
                        reason=reason,
                    )
                )

            except Exception as exc:
                signals.append(
                    Signal(
                        strategy_name=self.name,
                        symbol=symbol,
                        action=SignalAction.HOLD,
                        quantity=0,
                        confidence=0.0,
                        reason=f"Momentum error: {exc}",
                    )
                )

        return signals