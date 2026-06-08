import math
import numpy as np
import pandas as pd

from models import Signal, SignalAction
from .base import StrategyBase

class VolatilityReversionStrategy(StrategyBase):
    """
    V-AR (Volatility-Adaptive Reversion) 策略：
    利用布林带极端偏离与 ATR 波动率过滤进行均值回归。
    
    逻辑：
    1. 计算 20 日 SMA 及标准差，构建布林带 (±2.5 std)。
    2. 计算 14 日 ATR (平均真实波幅) 衡量近期波动剧烈程度。
    3. 如果价格跌破下轨，且波动率未出现失控 (ATR 处于合理范围)，则产生 BUY 信号。
    4. 价格回归 SMA，或突破上轨时，产生 SELL 信号。
    """

    def __init__(
        self,
        name: str,
        symbols: list[str],
        weight: float = 1.0,
        window: int = 20,
        std_dev: float = 2.5,
        atr_window: int = 14,
        quantity: int = 1,
        duration: str = "6 M",
        bar_size: str = "1 day",
    ):
        super().__init__(name=name, symbols=symbols, weight=weight)
        self.window = window
        self.std_dev = std_dev
        self.atr_window = atr_window
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

                if len(df) < max(self.window, self.atr_window) + 1:
                    continue

                close = df["close"].astype(float)
                high = df["high"].astype(float)
                low = df["low"].astype(float)

                # 1. 计算布林带
                sma = close.rolling(self.window).mean()
                std = close.rolling(self.window).std()
                upper_band = sma + (self.std_dev * std)
                lower_band = sma - (self.std_dev * std)

                # 2. 计算 ATR (Average True Range)
                tr1 = high - low
                tr2 = (high - close.shift(1)).abs()
                tr3 = (low - close.shift(1)).abs()
                true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = true_range.rolling(self.atr_window).mean()

                curr_close = close.iloc[-1]
                curr_sma = sma.iloc[-1]
                curr_lower = lower_band.iloc[-1]
                curr_upper = upper_band.iloc[-1]
                
                # Z-score: 当前价格偏离均线的标准差倍数
                z_score = (curr_close - curr_sma) / std.iloc[-1]

                # 预期回归空间 (绝对值)
                expected_edge = abs(curr_sma - curr_close) / curr_close

                if curr_close < curr_lower:
                    action = SignalAction.BUY
                    # 偏离越严重，信心越高，封顶 1.0
                    confidence = min(abs(z_score) / self.std_dev, 1.0)
                    reason = f"V-AR BUY: 极端超卖, Z={z_score:.2f}, price={curr_close:.2f}, lower={curr_lower:.2f}"

                elif curr_close > curr_upper or curr_close >= curr_sma:
                    action = SignalAction.SELL
                    confidence = 0.8
                    reason = f"V-AR SELL/EXIT: 均值回归或超买, Z={z_score:.2f}, price={curr_close:.2f}"

                else:
                    action = SignalAction.HOLD
                    confidence = 0.0
                    expected_edge = 0.0
                    reason = f"V-AR HOLD: 价格在正常波动区间 (Z={z_score:.2f})"

                signals.append(
                    Signal(
                        strategy_name=self.name,
                        symbol=symbol,
                        action=action,
                        quantity=self.quantity,
                        confidence=confidence,
                        reason=reason,
                        expected_edge_bps=expected_edge * 10_000,
                    )
                )

            except Exception as exc:
                signals.append(
                    Signal(
                        strategy_name=self.name,
                        symbol=symbol,
                        action=SignalAction.HOLD,
                        reason=f"V-AR Error: {exc}",
                    )
                )

        return signals