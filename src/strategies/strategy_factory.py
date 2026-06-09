import importlib
import inspect
from .base import StrategyBase

def create_strategy(name: str, symbols: list[str], weight: float, params: dict):
    """
    黑魔法：动态加载策略类
    假设 yaml 里的 name 是 "macd_divergence"，它会自动去尝试加载 strategies/macd_divergence.py
    """
    # 1. 动态导入模块
    try:
        # 优先寻找完全同名的文件，比如 mean_reversion.py
        module = importlib.import_module(f"strategies.{name}")
    except ImportError:
        try:
            # 兼容你的 idle_strategy.py 这种带后缀的文件名
            module = importlib.import_module(f"strategies.{name}_strategy")
        except ImportError:
            raise ImportError(f"❌ 找不到策略文件: 请确保 src/strategies/ 下有 {name}.py 或 {name}_strategy.py")

    # 2. 在模块中自动寻找继承自 StrategyBase 的核心策略类
    strategy_class = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if inspect.isclass(attr) and issubclass(attr, StrategyBase) and attr is not StrategyBase:
            strategy_class = attr
            break
            
    if not strategy_class:
        raise TypeError(f"❌ 在 {module.__name__} 中没有找到继承自 StrategyBase 的类！")

    # 3. 自动解包 yaml 中的参数并实例化
    # 注意：YAML 解析器会自动把 "20" 转成 int，"0.05" 转成 float，完美契合！
    return strategy_class(
        name=name,
        symbols=symbols,
        weight=weight,
        **params  # 直接把 yaml 里的 params 字典解包成 key=value 传进去
    )