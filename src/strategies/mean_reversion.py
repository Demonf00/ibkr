from models import Signal, SignalAction
from .base import StrategyBase


class MeanReversionStrategy(StrategyBase):
    """
    Mean Reversion 策略：

    当前价格低于 moving average 一定比例 → BUY
    当前价格高于 moving average 一定比例 → SELL
    否则 HOLD
    """

    def __init__(
        self,
        name: str,
        symbols: list[str],
        weight: float = 1.0,
        ma_window: int = 20,
        buy_deviation: float = -0.03,
        sell_deviation: float = 0.03,
        quantity: int = 1,
        duration: str = "3 M",
        bar_size: str = "1 day",
    ):
        super().__init__(name=name, symbols=symbols, weight=weight)

        self.ma_window = ma_window
        self.buy_deviation = buy_deviation
        self.sell_deviation = sell_deviation
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

                if len(df) < self.ma_window:
                    signals.append(
                        Signal(
                            strategy_name=self.name,
                            symbol=symbol,
                            action=SignalAction.HOLD,
                            quantity=0,
                            confidence=0.0,
                            reason=f"Not enough bars. Need {self.ma_window}, got {len(df)}",
                        )
                    )
                    continue

                current_price = float(df["close"].iloc[-1])
                ma = float(df["close"].rolling(self.ma_window).mean().iloc[-1])

                deviation = (current_price - ma) / ma

                if deviation <= self.buy_deviation:
                    action = SignalAction.BUY
                    quantity = self.quantity
                    confidence = min(abs(deviation) / abs(self.buy_deviation), 1.0)
                    reason = (
                        f"MeanReversion BUY: price={current_price:.2f}, "
                        f"MA({self.ma_window})={ma:.2f}, deviation={deviation:.2%}"
                    )

                elif deviation >= self.sell_deviation:
                    action = SignalAction.SELL
                    quantity = self.quantity
                    confidence = min(abs(deviation) / abs(self.sell_deviation), 1.0)
                    reason = (
                        f"MeanReversion SELL: price={current_price:.2f}, "
                        f"MA({self.ma_window})={ma:.2f}, deviation={deviation:.2%}"
                    )

                else:
                    action = SignalAction.HOLD
                    quantity = 0
                    confidence = 0.0
                    reason = (
                        f"MeanReversion HOLD: price={current_price:.2f}, "
                        f"MA({self.ma_window})={ma:.2f}, deviation={deviation:.2%}"
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
                        reason=f"MeanReversion error: {exc}",
                    )
                )

        return signals