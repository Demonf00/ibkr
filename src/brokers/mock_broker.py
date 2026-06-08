import os
import pandas as pd
import yfinance as yf

from .base import BrokerBase


class MockBroker(BrokerBase):
    def __init__(self):
        self.cash = 100000.0
        self.positions = {}
        self.orders = []
        # 本地缓存，避免重复下载
        self._history_cache = {}

    def connect(self) -> None:
        print("[MockBroker] connected (using yfinance for real historical data)")

    def disconnect(self) -> None:
        print("[MockBroker] disconnected")

    def get_accounts(self) -> list[str]:
        return ["DU_MOCK_ACCOUNT"]
        
    def get_position(self, symbol: str) -> int:
        return self.positions.get(symbol, 0)

    def get_market_price(self, symbol: str) -> float:
        # 如果缓存里有，直接取最后一天收盘价
        if symbol in self._history_cache:
            return float(self._history_cache[symbol]["close"].iloc[-1])
        
        # 否则去 yfinance 拿最新价
        ticker = yf.Ticker(symbol)
        todays_data = ticker.history(period="1d")
        if not todays_data.empty:
            return float(todays_data["Close"].iloc[-1])
        return 100.0

    def get_historical_bars(
        self,
        symbol: str,
        duration: str = "1 y", # 默认给够 1 年数据，满足 200ma
        bar_size: str = "1d",
    ) -> pd.DataFrame:
        
        # 简单转换 IBKR 的 duration 到 yfinance 的 period
        period_map = {
            "1 m": "1mo", "3 m": "3mo", "6 m": "6mo", 
            "1 y": "1y", "2 y": "2y", "5 y": "5y"
        }
        yf_period = period_map.get(duration.lower(), "1y")

        cache_key = f"{symbol}_{yf_period}"
        if cache_key in self._history_cache:
            return self._history_cache[cache_key]

        print(f"[MockBroker] Downloading real data for {symbol} ({yf_period})...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=yf_period)

        if df.empty:
            raise ValueError(f"No historical bars returned from yfinance for {symbol}")

        # 标准化列名为小写，适配你的策略
        df = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })
        
        self._history_cache[cache_key] = df
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