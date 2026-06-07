import pandas as pd

from .base import BrokerBase


class MockBroker(BrokerBase):
    def __init__(self):
        self.cash = 100000.0
        self.positions = {}
        self.orders = []

    def connect(self) -> None:
        print("[MockBroker] connected")

    def disconnect(self) -> None:
        print("[MockBroker] disconnected")

    def get_accounts(self) -> list[str]:
        return ["DU_MOCK_ACCOUNT"]

    def get_market_price(self, symbol: str) -> float:
        fake_prices = {
            "AAPL": 200.0,
            "SPY": 500.0,
            "QQQ": 430.0,
        }
        return fake_prices.get(symbol, 100.0)

    def get_historical_bars(
        self,
        symbol: str,
        duration: str = "3 M",
        bar_size: str = "1 day",
    ) -> pd.DataFrame:
        # 生成一段假的上涨价格，用来测试 MA cross 流程
        dates = pd.date_range(end=pd.Timestamp.today(), periods=80, freq="D")

        base = self.get_market_price(symbol)

        closes = []
        for i in range(len(dates)):
            # 前半段慢涨，后半段加速上涨，让短均线可能上穿长均线
            if i < 40:
                closes.append(base - 20 + i * 0.2)
            else:
                closes.append(base - 12 + i * 0.5)

        df = pd.DataFrame(
            {
                "date": dates,
                "open": closes,
                "high": [c * 1.01 for c in closes],
                "low": [c * 0.99 for c in closes],
                "close": closes,
                "volume": [1000000] * len(dates),
            }
        )

        return df

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