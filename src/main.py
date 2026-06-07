import os
import time
from dotenv import load_dotenv

from config_loader import load_config
from brokers.mock_broker import MockBroker
from brokers.ibkr_broker import IbkrBroker
from strategies.strategy_manager import StrategyManager
from risk.risk_manager import RiskManager
from execution.order_manager import OrderManager
from execution.cost_model import TradingCostModel
from execution.signal_aggregator import SignalAggregator


def create_broker(config: dict):
    broker_mode = os.getenv("BROKER_MODE", "mock").lower()

    if broker_mode == "mock":
        return MockBroker()

    if broker_mode == "ibkr":
        ibkr_cfg = config["ibkr"]

        return IbkrBroker(
            host=ibkr_cfg["host"],
            port=int(ibkr_cfg["port"]),
            client_id=int(ibkr_cfg["client_id"]),
            expected_account_prefix=ibkr_cfg.get("expected_account_prefix", "DU"),
        )

    raise ValueError(f"Unknown BROKER_MODE: {broker_mode}")


def main():
    load_dotenv()

    app_env = os.getenv("APP_ENV", "paper")
    config_path = f"config/{app_env}.yaml"

    config = load_config(config_path)

    print(f"[App] env={app_env}")
    print(f"[App] broker_mode={os.getenv('BROKER_MODE', 'mock')}")
    print(f"[App] config={config_path}")

    broker = create_broker(config)
    strategy_manager = StrategyManager(config.get("strategies", []))
    risk_manager = RiskManager(config)

    dry_run = bool(config.get("runtime", {}).get("dry_run", True))
    strategy_weights = {
        s["name"]: float(s.get("weight", 1.0))
        for s in config.get("strategies", [])
        if s.get("enabled", False)
    }

    cost_cfg = config.get("cost_model", {})
    cost_model = TradingCostModel(
        commission_per_share=float(cost_cfg.get("commission_per_share", 0.005)),
        min_commission=float(cost_cfg.get("min_commission", 1.0)),
        slippage_bps=float(cost_cfg.get("slippage_bps", 2.0)),
    )

    agg_cfg = config.get("aggregate", {})
    signal_aggregator = SignalAggregator(
        strategy_weights=strategy_weights,
        cost_model=cost_model,
        buy_threshold=float(agg_cfg.get("buy_threshold", 0.35)),
        sell_threshold=float(agg_cfg.get("sell_threshold", -0.35)),
        default_quantity=int(agg_cfg.get("default_quantity", 1)),
        cost_gate_enabled=bool(agg_cfg.get("cost_gate_enabled", True)),
        min_edge_buffer_bps=float(agg_cfg.get("min_edge_buffer_bps", 5.0)),
    )
    order_manager = OrderManager(
        broker=broker,
        risk_manager=risk_manager,
        dry_run=dry_run,
    )

    loop_interval = int(config.get("runtime", {}).get("loop_interval_seconds", 10))

    broker.connect()

    try:
        accounts = broker.get_accounts()
        print(f"[App] accounts={accounts}")
        print("[App] robot started")

        while True:
            raw_signals = strategy_manager.generate_all_signals(broker)

            print("[RawSignals]")
            for signal in raw_signals:
                print(
                    f"  {signal.strategy_name} {signal.symbol} "
                    f"{signal.action.value} confidence={signal.confidence:.2f} "
                    f"reason={signal.reason}"
                )

            final_signals = signal_aggregator.aggregate(raw_signals, broker)

            print("[FinalSignals]")
            for signal in final_signals:
                order_manager.handle_signal(signal)

            print(f"[App] sleeping {loop_interval}s...\n")
            time.sleep(loop_interval)

    except KeyboardInterrupt:
        print("[App] stopped by user")

    finally:
        broker.disconnect()


if __name__ == "__main__":
    main()