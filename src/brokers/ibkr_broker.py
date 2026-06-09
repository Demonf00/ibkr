import time
import pandas as pd
from ib_async import IB, Stock, MarketOrder, util

from .base import BrokerBase


class IbkrBroker(BrokerBase):
    def __init__(
        self,
        host: str,
        port: int,
        client_id: int,
        expected_account_prefix: str = "DU",
    ):
        self.ib = IB()
        self.host = host
        self.port = int(port)
        self.client_id = int(client_id)
        self.expected_account_prefix = expected_account_prefix

        self._history_cache = {}
        self._cache_date = None

    def connect(self) -> None:
        print(f"[IbkrBroker] connecting to {self.host}:{self.port}, clientId={self.client_id}")
        self.ib.connect(self.host, self.port, clientId=self.client_id)

        accounts = self.get_accounts()
        print(f"[IbkrBroker] accounts: {accounts}")

        if self.expected_account_prefix:
            ok = any(acc.startswith(self.expected_account_prefix) for acc in accounts)
            if not ok:
                self.disconnect()
                raise RuntimeError(
                    f"Account safety check failed. "
                    f"Expected prefix={self.expected_account_prefix}, got={accounts}"
                )
        
        self.ib.reqMarketDataType(3) # 3 代表 Delayed (延时数据)

    def disconnect(self) -> None:
        if self.ib.isConnected():
            self.ib.disconnect()
            print("[IbkrBroker] disconnected")

    def get_accounts(self) -> list[str]:
        return list(self.ib.managedAccounts())

    def _stock_contract(self, symbol: str):
        contract = Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        return contract

    def get_market_price(self, symbol: str) -> float:
        contract = self._stock_contract(symbol)
        
        # 尝试直接请求切片数据
        self.ib.reqMktData(contract, "", False, False)
        
        price = None
        # 动态等待，最多等 2 秒 (20 * 0.1s)，拿到非 NaN 价格立刻 break
        for _ in range(20):
            self.ib.sleep(0.1)  # 维持 event loop 运转
            ticker = self.ib.ticker(contract)
            if ticker and ticker.marketPrice() == ticker.marketPrice(): # 过滤 NaN
                if ticker.marketPrice() > 0:
                    price = ticker.marketPrice()
                    break

        self.ib.cancelMktData(contract)

        if price is None or price <= 0:
            raise ValueError(f"Invalid market price for {symbol}: possibly delayed or no market data.")

        return float(price)

    def get_historical_bars(
        self,
        symbol: str,
        duration: str = "3 M",
        bar_size: str = "1 day",
    ) -> pd.DataFrame:
        
        # 1. 获取当前美东日历日期
        current_date = pd.Timestamp.now(tz="America/New_York").date()

        # 2. 如果发生跨日（比如第二天开盘），清空昨天的缓存
        if self._cache_date != current_date:
            self._history_cache.clear()
            self._cache_date = current_date

        cache_key = f"{symbol}_{duration}_{bar_size}"

        # 3. 命中缓存，直接返回 copy（防止策略层意外修改数据）
        if cache_key in self._history_cache:
            return self._history_cache[cache_key].copy()

        # 4. 未命中缓存：执行限流保护
        # 强制 sleep 1秒，确保即使第一次启动疯狂拉取数据，也不会瞬间打满 60次/10min 的限制
        self.ib.sleep(1.0) 
        
        print(f"[IbkrBroker] Fetching fresh historical data from API for {symbol}...")
        
        contract = self._stock_contract(symbol)
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )

        df = util.df(bars)

        if df is None or df.empty:
            raise ValueError(f"No historical bars returned for {symbol}")
            
        # 标准化列名以适配策略
        df.columns = [c.lower() for c in df.columns]

        # 5. 写入缓存并返回
        self._history_cache[cache_key] = df
        return df.copy()

    def place_market_order(self, symbol: str, side: str, quantity: int):
        contract = self._stock_contract(symbol)

        order = MarketOrder(side, quantity)
        trade = self.ib.placeOrder(contract, order)

        self.ib.sleep(2)

        return trade
    
    def get_position(self, symbol: str) -> int:
        positions = self.ib.positions()
        for p in positions:
            if p.contract.symbol == symbol and p.account.startswith(self.expected_account_prefix):
                return int(p.position)
        return 0