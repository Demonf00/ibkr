from ib_async import IB, Stock, MarketOrder, util
import pandas as pd

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

        ticker = self.ib.reqMktData(contract)
        self.ib.sleep(2)

        price = ticker.marketPrice()

        self.ib.cancelMktData(contract)

        if price is None or price != price or price <= 0:
            raise ValueError(f"Invalid market price for {symbol}: {price}")

        return float(price)

    def get_historical_bars(
        self,
        symbol: str,
        duration: str = "3 M",
        bar_size: str = "1 day",
    ) -> pd.DataFrame:
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

        return df

    def place_market_order(self, symbol: str, side: str, quantity: int):
        contract = self._stock_contract(symbol)

        order = MarketOrder(side, quantity)
        trade = self.ib.placeOrder(contract, order)

        self.ib.sleep(2)

        return trade