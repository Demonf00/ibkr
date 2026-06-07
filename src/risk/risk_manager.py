from models import OrderRequest, SignalAction


class RiskManager:
    def __init__(self, config: dict):
        self.config = config
        self.daily_order_count_by_strategy: dict[str, int] = {}

    def _source_strategies(self, order: OrderRequest) -> list[str]:
        if order.source_strategies:
            return order.source_strategies
        return [order.strategy_name]

    def _strategy_limit(self, strategy_name: str) -> int:
        strategy_limits = self.config.get("strategy_limits", {})
        default_limit = self.config["trading"].get("max_daily_orders", 5)

        return int(
            strategy_limits.get(strategy_name, {}).get(
                "max_daily_orders",
                default_limit,
            )
        )

    def validate_order(self, order: OrderRequest, price: float) -> None:
        trading = self.config["trading"]

        if not trading.get("enabled", False):
            raise RuntimeError("Trading is disabled in config.")

        if order.symbol not in trading["allowed_symbols"]:
            raise RuntimeError(f"Symbol not allowed: {order.symbol}")

        if order.quantity <= 0:
            raise RuntimeError("Quantity must be positive.")

        if order.side == SignalAction.SELL and not trading.get("allow_short", False):
            raise RuntimeError("Short selling is disabled.")

        order_value = order.quantity * price

        if order_value > trading["max_order_value"]:
            raise RuntimeError(
                f"Order value too large: {order_value} > {trading['max_order_value']}"
            )

        for strategy_name in self._source_strategies(order):
            current_count = self.daily_order_count_by_strategy.get(strategy_name, 0)
            limit = self._strategy_limit(strategy_name)

            if current_count >= limit:
                raise RuntimeError(
                    f"Max daily orders reached for strategy={strategy_name}: "
                    f"{current_count}/{limit}"
                )

    def record_order(self, order: OrderRequest) -> None:
        for strategy_name in self._source_strategies(order):
            self.daily_order_count_by_strategy[strategy_name] = (
                self.daily_order_count_by_strategy.get(strategy_name, 0) + 1
            )