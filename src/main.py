import yaml
from brokers.mock_broker import MockBroker
from risk.risk_manager import RiskManager
from strategies.test_strategy import TestStrategy


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    config = load_config("config/paper.yaml")

    broker = MockBroker()
    risk = RiskManager(config)
    strategy = TestStrategy()

    symbol = "AAPL"
    price = broker.get_market_price(symbol)

    signal = strategy.generate_signal(symbol, price)
    print("Signal:", signal)

    risk.validate_order(
        symbol=signal["symbol"],
        side=signal["side"],
        quantity=signal["quantity"],
        price=price,
    )

    order = broker.place_market_order(
        symbol=signal["symbol"],
        side=signal["side"],
        quantity=signal["quantity"],
    )

    print("Order:", order)
    print("Cash:", broker.cash)
    print("Positions:", broker.positions)


if __name__ == "__main__":
    main()