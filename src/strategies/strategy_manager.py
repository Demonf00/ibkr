from .strategy_factory import create_strategy

class StrategyManager:
    def __init__(self, strategy_configs: list[dict]):
        self.strategies = []

        for cfg in strategy_configs:
            if not cfg.get("enabled", False):
                continue

            name = cfg["name"]
            symbols = cfg.get("symbols", [])
            weight = float(cfg.get("weight", 1.0))
            params = cfg.get("params", {})

            # 🚀 一行代码，动态创建任何策略！
            strategy_instance = create_strategy(name, symbols, weight, params)
            self.strategies.append(strategy_instance)

    def generate_all_signals(self, broker):
        all_signals = []
        for strategy in self.strategies:
            signals = strategy.generate_signals(broker)
            all_signals.extend(signals)
        return all_signals