class TestStrategy:
    def generate_signal(self, symbol: str, price: float) -> dict:
        return {
            "symbol": symbol,
            "side": "BUY",
            "quantity": 1,
            "reason": f"Test buy signal at price {price}",
        }