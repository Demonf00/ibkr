import os
import time
from pathlib import Path
from dotenv import load_dotenv

from config_loader import load_config
from brokers.mock_broker import MockBroker
from brokers.ibkr_broker import IbkrBroker
from strategies.strategy_manager import StrategyManager
from risk.risk_manager import RiskManager
from execution.order_manager import OrderManager
from execution.cost_model import TradingCostModel
from execution.signal_aggregator import SignalAggregator


def to_bool(value, default: bool = False) -> bool:
    """
    安全解析 bool，避免 bool("false") == True 的坑。
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "on"}

    return bool(value)


def create_broker(config: dict):
    broker_mode = os.getenv("BROKER_MODE", "mock").strip().lower()

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


def create_signal_aggregator(config: dict) -> SignalAggregator:
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
    return SignalAggregator(
        strategy_weights=strategy_weights,
        cost_model=cost_model,
        buy_threshold=float(agg_cfg.get("buy_threshold", 0.35)),
        sell_threshold=float(agg_cfg.get("sell_threshold", -0.35)),
        default_quantity=int(agg_cfg.get("default_quantity", 1)),
        cost_gate_enabled=to_bool(agg_cfg.get("cost_gate_enabled", True), default=True),
        min_edge_buffer_bps=float(agg_cfg.get("min_edge_buffer_bps", 5.0)),
    )


def main():
    load_dotenv()

    app_env = os.getenv("APP_ENV", "paper").strip().lower()

    # 保证从项目根目录找 config，不依赖你在哪个路径运行 python
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / f"{app_env}.yaml"

    config = load_config(str(config_path))

    print(f"[App] env={app_env}")
    print(f"[App] broker_mode={os.getenv('BROKER_MODE', 'mock')}")
    print(f"[App] config={config_path}")

    broker = create_broker(config)
    strategy_manager = StrategyManager(config.get("strategies", []))
    risk_manager = RiskManager(config)
    signal_aggregator = create_signal_aggregator(config)

    dry_run = to_bool(config.get("runtime", {}).get("dry_run", True), default=True)

    order_manager = OrderManager(
        broker=broker,
        risk_manager=risk_manager,
        dry_run=dry_run,
    )

    loop_interval = int(config.get("runtime", {}).get("loop_interval_seconds", 10))

    try:
        broker.connect()

        accounts = broker.get_accounts()
        print(f"[App] accounts={accounts}")
        print(f"[App] dry_run={dry_run}")
        print("[App] robot started")

        while True:
            try:
                raw_signals = strategy_manager.generate_all_signals(broker)

                print("[RawSignals]")
                for signal in raw_signals:
                    print(
                        f"  {signal.strategy_name} {signal.symbol} "
                        f"{signal.action.value} confidence={signal.confidence:.2f} "
                        f"edge={signal.expected_edge_bps:.2f}bps "
                        f"reason={signal.reason}"
                    )

                final_signals = signal_aggregator.aggregate(raw_signals, broker)

                print("[FinalSignals]")
                for signal in final_signals:
                    try:
                        order_manager.handle_signal(signal)
                    except Exception as exc:
                        print(
                            f"[OrderError] symbol={signal.symbol} "
                            f"action={signal.action.value} error={exc}"
                        )

                print(f"[App] sleeping {loop_interval}s...\n")
                time.sleep(loop_interval)

            except Exception as exc:
                # 防止某一轮策略/IBKR临时错误直接杀掉机器人
                print(f"[LoopError] {exc}")
                print(f"[App] sleeping {loop_interval}s before retry...\n")
                time.sleep(loop_interval)

    except KeyboardInterrupt:
        print("[App] stopped by user")

    finally:
        try:
            broker.disconnect()
        except Exception as exc:
            print(f"[App] disconnect error: {exc}")


if __name__ == "__main__":
    main()