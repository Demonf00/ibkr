from abc import ABC, abstractmethod
from typing import Iterable

from models import Signal


class StrategyBase(ABC):
    def __init__(self, name: str, symbols: list[str], weight: float = 1.0):
        self.name = name
        self.symbols = symbols
        self.weight = weight

    @abstractmethod
    def generate_signals(self, broker) -> Iterable[Signal]:
        pass