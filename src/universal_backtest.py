import os
from pathlib import Path
import pandas as pd
import backtrader as bt
import yfinance as yf

# ==========================================
# 导入配置、实盘动作与魔法工厂
# ==========================================
from config_loader import load_config
from models import SignalAction
# 💡 修复点 1：明确导入魔法工厂，防止 not defined 报错！
from strategies.strategy_factory import create_strategy

# ==========================================
# 1. 适配器：欺骗实盘策略的伪装 Broker
# ==========================================
class BtAdapterBroker:
    def __init__(self, bt_strategy):
        self.bt_strategy = bt_strategy

    def get_historical_bars(self, symbol: str, duration: str = "1 Y", bar_size: str = "1 day") -> pd.DataFrame:
        data = self.bt_strategy.getdatabyname(symbol)
        
        lookback = 252
        if "M" in duration.upper():
            lookback = int(duration.split()[0]) * 21
        elif "Y" in duration.upper():
            lookback = int(duration.split()[0]) * 252
        
        opens = data.open.get(size=lookback)
        highs = data.high.get(size=lookback)
        lows = data.low.get(size=lookback)
        closes = data.close.get(size=lookback)
        volumes = data.volume.get(size=lookback)

        if len(closes) == 0:
            return pd.DataFrame()

        return pd.DataFrame({
            "open": opens, "high": highs, "low": lows,
            "close": closes, "volume": volumes
        })

# ==========================================
# 2. 包装器：Backtrader 驱动引擎
# ==========================================
class LiveStrategyWrapperBT(bt.Strategy):
    params = (
        ('live_strategy', None), 
        ('risk_per_trade', 0.95), 
    )

    def __init__(self):
        self.adapter_broker = BtAdapterBroker(self)
        self.order = None

    def next(self):
        if self.order:
            return

        live_strat = self.p.live_strategy
        if not live_strat:
            return

        signals = live_strat.generate_signals(self.adapter_broker)

        for sig in signals:
            symbol = sig.symbol
            action = sig.action
            
            data = self.getdatabyname(symbol)
            current_position = self.getposition(data).size
            curr_close = data.close[0]

            if action == SignalAction.BUY and current_position <= 0:
                target_value = self.broker.getcash() * self.p.risk_per_trade
                qty = int(target_value / curr_close)
                if qty > 0:
                    self.order = self.buy(data=data, size=qty)

            elif action == SignalAction.SELL and current_position > 0:
                self.order = self.close(data=data)

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None

# ==========================================
# 3. 探针与成本模型
# ==========================================
class PortfolioValueAnalyzer(bt.Analyzer):
    def stop(self): self.final_val = self.strategy.broker.getvalue()
    def get_analysis(self): return {"final_value": self.final_val}

class IBKRCommissionInfo(bt.CommInfoBase):
    params = (('commission', 0.005), ('margin', None), ('mult', 1.0), ('min_comm', 1.0), ('stocklike', True), ('commtype', bt.CommInfoBase.COMM_FIXED))
    def _getcommission(self, size, price, pseudoexec):
        return max(abs(size) * self.p.commission, self.p.min_comm)

# ==========================================
# 4. 智能数据缓存加载器
# ==========================================
def get_cached_data(symbol: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    """💡 修复点 2：智能本地缓存，加速回测"""
    # 确保缓存目录存在
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建缓存文件名 (例如: data_cache/SPY_2019-01-01_2025-12-31.csv)
    cache_file = cache_dir / f"{symbol}_{start}_{end}.csv"
    
    if cache_file.exists():
        print(f"[{symbol}] ⚡ 从本地缓存读取数据...")
        # 必须把索引解析为日期格式，才能被 Backtrader 识别
        return pd.read_csv(cache_file, index_col=0, parse_dates=True)
    
    print(f"[{symbol}] 🌐 从雅虎金融下载历史数据...")
    df = yf.download(symbol, start=start, end=end, progress=False)
    
    if df.empty:
        raise ValueError(f"下载 {symbol} 失败或数据为空")
        
    # 处理 yfinance 的多层表头兼容性问题
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    # 保存到本地缓存
    df.to_csv(cache_file)
    return df

# ==========================================
# 5. 终极竞技场引擎
# ==========================================
def run_universal_arena():
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config" / "paper.yaml"
    
    # 定义缓存存放目录
    cache_dir = project_root / "data_cache"
    
    config = load_config(str(config_path))
    strategy_configs = config.get("strategies", [])
    trading_config = config.get("trading", {})
    cost_config = config.get("cost_model", {})
    
    symbols = trading_config.get("allowed_symbols", ['SPY', 'QQQ', 'TLT', 'GLD'])

    start_date = '2019-01-01'
    end_date = '2025-12-31'
    
    print(f"准备数据 ({start_date} 至 {end_date})...")
    data_feeds = {}
    for sym in symbols:
        # 使用我们的智能缓存加载器
        data_feeds[sym] = get_cached_data(sym, start_date, end_date, cache_dir)

    print("\n⚔️ 配置文件驱动：全策略自动化基准测试 ⚔️")
    print(f"{'品种':<5} | {'策略名称 (From YAML)':<25} | {'期末资金':<10} | {'胜率':<6} | {'最大回撤':<6} | {'交易数'}")
    print("-" * 78)

    for sym in symbols:
        for cfg in strategy_configs:
            if not cfg.get("enabled", False):
                continue
            if sym not in cfg.get("symbols", []):
                continue
                
            strat_name = cfg["name"]
            params = cfg.get("params", {})
            weight = float(cfg.get("weight", 1.0))
            
            try:
                # 动态生成策略！
                live_strat = create_strategy(strat_name, [sym], weight, params)
            except Exception as e:
                print(f"❌ 加载策略 {strat_name} 失败: {e}")
                continue

            cerebro = bt.Cerebro()
            data = bt.feeds.PandasData(dataname=data_feeds[sym], name=sym)
            cerebro.adddata(data)

            cerebro.addstrategy(
                LiveStrategyWrapperBT,
                live_strategy=live_strat,
                risk_per_trade=0.95
            )

            cerebro.broker.setcash(100000.0)
            comm_info = IBKRCommissionInfo(
                commission=float(cost_config.get("commission_per_share", 0.005)),
                min_comm=float(cost_config.get("min_commission", 1.0))
            )
            cerebro.broker.addcommissioninfo(comm_info)
            slippage_dec = float(cost_config.get("slippage_bps", 2.0)) / 10000.0
            cerebro.broker.set_slippage_perc(perc=slippage_dec)

            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(PortfolioValueAnalyzer, _name='my_value')

            try:
                res = cerebro.run()[0]
                
                final_val = res.analyzers.my_value.get_analysis()['final_value']
                trade_info = res.analyzers.trades.get_analysis()
                total_closed = trade_info.get('total', {}).get('closed', 0)
                won_trades = trade_info.get('won', {}).get('total', 0)
                win_rate = (won_trades / total_closed * 100) if total_closed > 0 else 0.0
                max_dd = res.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)

                print(f"{sym:<5} | {strat_name:<25} | ${final_val:<9.2f} | {win_rate:>4.1f}% | {max_dd:>4.1f}% | {total_closed}")
            
            except Exception as e:
                print(f"{sym:<5} | {strat_name:<25} | 运行报错: {e}")
        
        print("-" * 78)

if __name__ == '__main__':
    run_universal_arena()