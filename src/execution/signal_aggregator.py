from collections import defaultdict

from models import Signal, SignalAction


class SignalAggregator:
    """
    把多个策略的 raw signals 聚合成每个 symbol 一个 final signal。

    BUY = +1
    HOLD = 0
    SELL = -1

    final_score = sum(direction * strategy_weight * confidence)

    例子：
    ma_cross BUY weight 0.25 confidence 0.7 => +0.175
    momentum BUY weight 0.25 confidence 1.0 => +0.25
    mean_reversion SELL weight 0.25 confidence 0.8 => -0.20
    final_score = +0.225

    超过 buy_threshold 才 BUY。
    低于 sell_threshold 才 SELL。
    中间 HOLD。
    """

    def __init__(
        self,
        strategy_weights: dict[str, float],
        cost_model,
        buy_threshold: float = 0.35,
        sell_threshold: float = -0.35,
        default_quantity: int = 1,
        cost_gate_enabled: bool = True,
        min_edge_buffer_bps: float = 5.0,
    ):
        self.strategy_weights = strategy_weights
        self.cost_model = cost_model
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.default_quantity = default_quantity
        self.cost_gate_enabled = cost_gate_enabled
        self.min_edge_buffer_bps = min_edge_buffer_bps

    def _direction(self, action: SignalAction) -> int:
        if action == SignalAction.BUY:
            return 1
        if action == SignalAction.SELL:
            return -1
        return 0

    def aggregate(self, raw_signals: list[Signal], broker) -> list[Signal]:
        grouped = defaultdict(list)

        for signal in raw_signals:
            grouped[signal.symbol].append(signal)

        final_signals = []

        for symbol, signals in grouped.items():
            score = 0.0
            contributors = []

            for signal in signals:
                direction = self._direction(signal.action)
                weight = self.strategy_weights.get(signal.strategy_name, 1.0)

                # 有些策略 confidence 可能没设，BUY/SELL 默认当 1.0 处理
                confidence = signal.confidence
                if signal.action != SignalAction.HOLD and confidence <= 0:
                    confidence = 1.0

                score += direction * weight * confidence

                if signal.action != SignalAction.HOLD:
                    contributors.append(signal)

            quantity = max(
                [s.quantity for s in contributors if s.quantity > 0],
                default=self.default_quantity,
            )

            try:
                price = broker.get_market_price(symbol)
                cost = self.cost_model.estimate(price=price, quantity=quantity)
                cost_bps = cost["cost_bps"]
            except Exception as exc:
                final_signals.append(
                    Signal(
                        strategy_name="aggregate",
                        symbol=symbol,
                        action=SignalAction.HOLD,
                        quantity=0,
                        confidence=0.0,
                        reason=f"Aggregator HOLD: cannot estimate cost/price: {exc}",
                    )
                )
                continue

            edge_estimates = [
                abs(s.expected_edge_bps)
                for s in contributors
                if s.expected_edge_bps > 0
            ]

            expected_edge_bps = max(edge_estimates) if edge_estimates else 0.0

            cost_ok = True
            if self.cost_gate_enabled and expected_edge_bps > 0:
                cost_ok = expected_edge_bps >= cost_bps + self.min_edge_buffer_bps

            if score >= self.buy_threshold and cost_ok:
                action = SignalAction.BUY
                aligned = [s for s in contributors if s.action == SignalAction.BUY]
                source_strategies = [s.strategy_name for s in aligned]

                reason = (
                    f"Aggregate BUY: score={score:.3f}, "
                    f"cost={cost_bps:.2f}bps, edge={expected_edge_bps:.2f}bps, "
                    f"sources={source_strategies}"
                )

            elif score <= self.sell_threshold and cost_ok:
                action = SignalAction.SELL
                aligned = [s for s in contributors if s.action == SignalAction.SELL]
                source_strategies = [s.strategy_name for s in aligned]

                reason = (
                    f"Aggregate SELL: score={score:.3f}, "
                    f"cost={cost_bps:.2f}bps, edge={expected_edge_bps:.2f}bps, "
                    f"sources={source_strategies}"
                )

            else:
                action = SignalAction.HOLD
                quantity = 0
                source_strategies = []
                reason = (
                    f"Aggregate HOLD: score={score:.3f}, "
                    f"cost={cost_bps:.2f}bps, edge={expected_edge_bps:.2f}bps"
                )

            final_signals.append(
                Signal(
                    strategy_name="aggregate",
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    confidence=abs(score),
                    reason=reason,
                    expected_edge_bps=expected_edge_bps,
                    source_strategies=source_strategies,
                )
            )

        return final_signals