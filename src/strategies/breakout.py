from models import Signal, SignalAction
from .base import StrategyBase


class BreakoutStrategy(StrategyBase):
    """
    Breakout 策略：

    当前收盘价突破过去 lookback 天最高价 → BUY
    当前收盘价跌破过去 lookback 天最低价 → SELL
    否则 HOLD
    """

    def __init__(
        self,
        name: str,
        symbols: list[str],
        weight: float = 1.0,
        lookback: int = 20,
        quantity: int = 1,
        duration: str = "3 M",
        bar_size: str = "1 day",
    ):
        super().__init__(name=name, symbols=symbols, weight=weight)

        self.lookback = lookback
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

                current_close = float(df["close"].iloc[-1])

                previous_window = df.iloc[-self.lookback - 1 : -1]
                previous_high = float(previous_window["close"].max())
                previous_low = float(previous_window["close"].min())

                if current_close > previous_high:
                    action = SignalAction.BUY
                    quantity = self.quantity
                    confidence = 0.7
                    reason = (
                        f"Breakout BUY: close={current_close:.2f} "
                        f"> previous {self.lookback}d high={previous_high:.2f}"
                    )

                elif current_close < previous_low:
                    action = SignalAction.SELL
                    quantity = self.quantity
                    confidence = 0.7
                    reason = (
                        f"Breakout SELL: close={current_close:.2f} "
                        f"< previous {self.lookback}d low={previous_low:.2f}"
                    )

                else:
                    action = SignalAction.HOLD
                    quantity = 0
                    confidence = 0.0
                    reason = (
                        f"Breakout HOLD: close={current_close:.2f}, "
                        f"range=[{previous_low:.2f}, {previous_high:.2f}]"
                    )

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
                        reason=f"Breakout error: {exc}",
                    )
                )

        return signals