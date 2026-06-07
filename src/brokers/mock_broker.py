class MockBroker:
    def __init__(self):
        self.cash = 100000
        self.positions = {}
        self.orders = []

    def get_market_price(self, symbol: str) -> float:
        fake_prices = {
            "AAPL": 200.0,
            "SPY": 500.0,
            "QQQ": 430.0,
        }
        return fake_prices.get(symbol, 100.0)

    def place_market_order(self, symbol: str, side: str, quantity: int):
        price = self.get_market_price(symbol)
        order = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "status": "FILLED_MOCK",
        }

        self.orders.append(order)

        if side == "BUY":
            self.positions[symbol] = self.positions.get(symbol, 0) + quantity
            self.cash -= price * quantity
        elif side == "SELL":
            self.positions[symbol] = self.positions.get(symbol, 0) - quantity
            self.cash += price * quantity

        return order