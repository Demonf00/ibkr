import pandas as pd
import backtrader as bt
import yfinance as yf

# 导入你原汁原味的实盘模型与策略
from models import SignalAction
from strategies.mean_reversion import MeanReversionStrategy
from strategies.momentum import MomentumStrategy

# ==========================================
# 1. 适配器：欺骗实盘策略的伪装 Broker
# ==========================================
class BtAdapterBroker:
    def __init__(self, bt_strategy):
        self.bt_strategy = bt_strategy

    def get_historical_bars(self, symbol: str, duration: str = "1 Y", bar_size: str = "1 day") -> pd.DataFrame:
        data = self.bt_strategy.getdatabyname(symbol)
        
        # 简单估算需要的 K线数量
        lookback = 252
        if "M" in duration.upper():
            lookback = int(duration.split()[0]) * 21
        elif "Y" in duration.upper():
            lookback = int(duration.split()[0]) * 252
        
        # 从 Backtrader 安全提取历史切片 (无未来函数)
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
        ('risk_per_trade', 0.95), # 保持 95% 高资金利用率
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

        # 核心：直接调用实盘代码
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
# 4. 终极竞技场引擎
# ==========================================
def run_universal_arena():
    symbols = ['SPY', 'QQQ', 'TLT', 'GLD']

    print("下载历史数据中 (2019 - 2025年底)...")
    data_feeds = {}
    for sym in symbols:
        df = yf.download(sym, start='2019-01-01', end='2025-12-31', progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        data_feeds[sym] = df

    print("\n⚔️ 终极竞技场：原生实盘代码跨品种基准测试 ⚔️")
    print(f"{'品种':<6} | {'策略':<18} | {'期末资金':<10} | {'胜率':<6} | {'最大回撤':<6} | {'交易数'}")
    print("-" * 65)

    for sym in symbols:
        # 每次切换品种时，重新实例化原生策略，保证环境干净
        strats_to_test = [
            ("均值回归 (原生)", MeanReversionStrategy(
                name="mean_reversion",
                symbols=[sym],
                ma_window=20,
                buy_deviation=-0.04,
                sell_deviation=0.05,
                duration="1 Y"
            )),
            ("动量跟随 (原生)", MomentumStrategy(
                name="momentum",
                symbols=[sym],
                lookback=63,
                buy_threshold=0.05,
                sell_threshold=-0.05,
                duration="1 Y"
            ))
        ]

        for strat_name, live_strat in strats_to_test:
            cerebro = bt.Cerebro()

            # 注入对应品种的数据
            data = bt.feeds.PandasData(dataname=data_feeds[sym], name=sym)
            cerebro.adddata(data)

            # 挂载实盘策略包装器
            cerebro.addstrategy(
                LiveStrategyWrapperBT,
                live_strategy=live_strat,
                risk_per_trade=0.95
            )

            cerebro.broker.setcash(100000.0)
            cerebro.broker.addcommissioninfo(IBKRCommissionInfo())
            cerebro.broker.set_slippage_perc(perc=0.0002)

            # 挂载官方硬核探针
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(PortfolioValueAnalyzer, _name='my_value')

            # 运行回测
            res = cerebro.run()[0]

            # 提取数据
            final_val = res.analyzers.my_value.get_analysis()['final_value']
            trade_info = res.analyzers.trades.get_analysis()
            total_closed = trade_info.get('total', {}).get('closed', 0)
            won_trades = trade_info.get('won', {}).get('total', 0)
            win_rate = (won_trades / total_closed * 100) if total_closed > 0 else 0.0
            max_dd = res.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)

            # 打印战报
            print(f"{sym:<6} | {strat_name:<18} | ${final_val:<9.2f} | {win_rate:>4.1f}% | {max_dd:>4.1f}% | {total_closed}")

if __name__ == '__main__':
    run_universal_arena()