from models import Signal, SignalAction
from .base import StrategyBase


class IdleStrategy(StrategyBase):
    """
    Idle 策略：
    - 不买
    - 不卖
    - 只读取价格
    - 只输出 HOLD 信号
    用来确认机器人主循环、broker、config、多策略系统都能正常跑。
    """

    def generate_signals(self, broker):
        signals = []

        for symbol in self.symbols:
            try:
                price = broker.get_market_price(symbol)
                reason = f"Idle heartbeat. Latest price={price}"
            except Exception as exc:
                reason = f"Idle heartbeat. Price unavailable: {exc}"

            signals.append(
                Signal(
                    strategy_name=self.name,
                    symbol=symbol,
                    action=SignalAction.HOLD,
                    quantity=0,
                    confidence=0.0,
                    reason=reason,
                )
            )

        return signals