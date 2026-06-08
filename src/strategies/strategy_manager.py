from .idle_strategy import IdleStrategy
from .ma_cross import MaCrossStrategy
from .momentum import MomentumStrategy
from .mean_reversion import MeanReversionStrategy
from .breakout import BreakoutStrategy
from .quality_trend_rotation import QualityTrendRotationStrategy
from .volatility_reversion import VolatilityReversionStrategy


class StrategyManager:
    def __init__(self, strategy_configs: list[dict]):
        self.strategies = []

        for cfg in strategy_configs:
            if not cfg.get("enabled", False):
                continue

            name = cfg["name"]
            symbols = cfg.get("symbols", [])
            weight = float(cfg.get("weight", 1.0))
            params = cfg.get("params", {})

            if name == "idle":
                self.strategies.append(
                    IdleStrategy(
                        name=name,
                        symbols=symbols,
                        weight=weight,
                    )
                )

            elif name == "ma_cross":
                self.strategies.append(
                    MaCrossStrategy(
                        name=name,
                        symbols=symbols,
                        weight=weight,
                        fast_ma=int(params.get("fast_ma", 10)),
                        slow_ma=int(params.get("slow_ma", 30)),
                        quantity=int(params.get("quantity", 1)),
                        duration=params.get("duration", "3 M"),
                        bar_size=params.get("bar_size", "1 day"),
                    )
                )

            elif name == "momentum":
                self.strategies.append(
                    MomentumStrategy(
                        name=name,
                        symbols=symbols,
                        weight=weight,
                        lookback=int(params.get("lookback", 20)),
                        buy_threshold=float(params.get("buy_threshold", 0.05)),
                        sell_threshold=float(params.get("sell_threshold", -0.05)),
                        quantity=int(params.get("quantity", 1)),
                        duration=params.get("duration", "3 M"),
                        bar_size=params.get("bar_size", "1 day"),
                    )
                )

            elif name == "mean_reversion":
                self.strategies.append(
                    MeanReversionStrategy(
                        name=name,
                        symbols=symbols,
                        weight=weight,
                        ma_window=int(params.get("ma_window", 20)),
                        buy_deviation=float(params.get("buy_deviation", -0.03)),
                        sell_deviation=float(params.get("sell_deviation", 0.03)),
                        quantity=int(params.get("quantity", 1)),
                        duration=params.get("duration", "3 M"),
                        bar_size=params.get("bar_size", "1 day"),
                    )
                )

            elif name == "breakout":
                self.strategies.append(
                    BreakoutStrategy(
                        name=name,
                        symbols=symbols,
                        weight=weight,
                        lookback=int(params.get("lookback", 20)),
                        quantity=int(params.get("quantity", 1)),
                        duration=params.get("duration", "3 M"),
                        bar_size=params.get("bar_size", "1 day"),
                    )
                )

            elif name == "quality_trend_rotation":
                self.strategies.append(
                    QualityTrendRotationStrategy(
                        name=name,
                        symbols=symbols,
                        weight=weight,
                        top_n=int(params.get("top_n", 2)),
                        fast_lookback=int(params.get("fast_lookback", 63)),
                        slow_lookback=int(params.get("slow_lookback", 126)),
                        long_ma=int(params.get("long_ma", 200)),
                        vol_window=int(params.get("vol_window", 20)),
                        volatility_penalty=float(params.get("volatility_penalty", 0.5)),
                        min_score=float(params.get("min_score", 0.02)),
                        quantity=int(params.get("quantity", 1)),
                        duration=params.get("duration", "1 Y"),
                        bar_size=params.get("bar_size", "1 day"),
                    )
                )

            elif name == "volatility_reversion":
                self.strategies.append(
                    VolatilityReversionStrategy(
                        name=name,
                        symbols=symbols,
                        weight=weight,
                        window=int(params.get("window", 20)),
                        std_dev=float(params.get("std_dev", 2.5)),
                        atr_window=int(params.get("atr_window", 14)),
                        quantity=int(params.get("quantity", 1)),
                        duration=params.get("duration", "6 M"),
                        bar_size=params.get("bar_size", "1 day"),
                    )
                )

            else:
                raise ValueError(f"Unknown strategy: {name}")

    def generate_all_signals(self, broker):
        all_signals = []

        for strategy in self.strategies:
            signals = strategy.generate_signals(broker)
            all_signals.extend(signals)

        return all_signals