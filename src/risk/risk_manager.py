class RiskManager:
    def __init__(self, config: dict):
        self.config = config
        self.daily_order_count = 0

    def validate_order(self, symbol: str, side: str, quantity: int, price: float):
        trading = self.config["trading"]

        if not trading.get("enabled", False):
            raise RuntimeError("Trading is disabled.")

        if symbol not in trading["allowed_symbols"]:
            raise RuntimeError(f"Symbol not allowed: {symbol}")

        if quantity <= 0:
            raise RuntimeError("Quantity must be positive.")

        if side == "SELL" and not trading.get("allow_short", False):
            raise RuntimeError("Short selling is disabled.")

        order_value = quantity * price
        if order_value > trading["max_order_value"]:
            raise RuntimeError(
                f"Order value too large: {order_value} > {trading['max_order_value']}"
            )

        if self.daily_order_count >= trading["max_daily_orders"]:
            raise RuntimeError("Max daily orders reached.")

        self.daily_order_count += 1