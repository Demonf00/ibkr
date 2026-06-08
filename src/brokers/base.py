from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class BrokerBase(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_accounts(self) -> list[str]:
        pass

    @abstractmethod
    def get_market_price(self, symbol: str) -> float:
        pass

    @abstractmethod
    def get_historical_bars(
        self,
        symbol: str,
        duration: str = "3 M",
        bar_size: str = "1 day",
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def place_market_order(self, symbol: str, side: str, quantity: int) -> Any:
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> int:
        pass