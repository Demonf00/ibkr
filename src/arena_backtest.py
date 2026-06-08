import backtrader as bt
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 探针与成本模型
# ==========================================
class PortfolioValueAnalyzer(bt.Analyzer):
    def stop(self): self.final_val = self.strategy.broker.getvalue()
    def get_analysis(self): return {"final_value": self.final_val}

class IBKRCommissionInfo(bt.CommInfoBase):
    params = (('commission', 0.005), ('margin', None), ('mult', 1.0), ('min_comm', 1.0), ('stocklike', True), ('commtype', bt.CommInfoBase.COMM_FIXED))
    def _getcommission(self, size, price, pseudoexec):
        return max(abs(size) * self.p.commission, self.p.min_comm)

# ==========================================
# 2. 参赛策略一：V-AR (震荡市王者)
# ==========================================
class VolatilityReversionBT(bt.Strategy):
    params = (('window', 20), ('std_dev', 2.0), ('risk_per_trade', 0.95))
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.window)
        self.std = bt.indicators.StdDev(self.data.close, period=self.p.window)
        self.boll_upper = self.sma + (self.p.std_dev * self.std)
        self.boll_lower = self.sma - (self.p.std_dev * self.std)
        self.order = None
    def next(self):
        if self.order: return
        if not self.position:
            if self.data.close[0] < self.boll_lower[0]:
                qty = int((self.broker.getcash() * self.p.risk_per_trade) / self.data.close[0])
                if qty > 0: self.order = self.buy(size=qty)
        else:
            if self.data.close[0] >= self.sma[0]:
                self.order = self.close()
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None

# ==========================================
# 3. 参赛策略二：纯粹动量 (大牛市收割机)
# ==========================================
class MomentumBT(bt.Strategy):
    params = (('lookback', 63), ('risk_per_trade', 0.95))
    def __init__(self):
        self.order = None
    def next(self):
        if self.order or len(self.data) < self.p.lookback: return
        
        # 简单暴力的动量：计算 63 天（约3个月）的涨幅
        ret = (self.data.close[0] - self.data.close[-self.p.lookback]) / self.data.close[-self.p.lookback]
        
        if not self.position:
            if ret > 0.05:  # 3个月涨超 5%，直接追高买入
                qty = int((self.broker.getcash() * self.p.risk_per_trade) / self.data.close[0])
                if qty > 0: self.order = self.buy(size=qty)
        else:
            if ret < 0:     # 动量衰竭，跌破 3 个月前的价格，平仓止盈/止损
                self.order = self.close()
    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None

# ==========================================
# 4. 竞技场核心引擎
# ==========================================
def run_arena():
    symbols = ['SPY', 'QQQ', 'TLT', 'GLD']
    strategies = [('V-AR (均值回归)', VolatilityReversionBT), ('Momentum (动量跟随)', MomentumBT)]
    
    results_matrix = []

    print("下载历史数据中 (2019 - 2025底)...")
    data_feeds = {}
    for sym in symbols:
        df = yf.download(sym, start='2019-01-01', end='2025-12-31', progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        data_feeds[sym] = df

    print("\n⚔️ 开始跨品种策略基准测试 ⚔️")
    print(f"{'品种':<6} | {'策略':<18} | {'期末资金':<10} | {'胜率':<6} | {'最大回撤':<6} | {'交易数'}")
    print("-" * 65)

    for sym in symbols:
        for strat_name, StratClass in strategies:
            cerebro = bt.Cerebro()
            data = bt.feeds.PandasData(dataname=data_feeds[sym])
            cerebro.adddata(data)
            cerebro.addstrategy(StratClass)
            
            cerebro.broker.setcash(100000.0)
            cerebro.broker.addcommissioninfo(IBKRCommissionInfo())
            cerebro.broker.set_slippage_perc(perc=0.0002)
            
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(PortfolioValueAnalyzer, _name='my_value')
            
            res = cerebro.run()[0]
            
            final_val = res.analyzers.my_value.get_analysis()['final_value']
            trade_info = res.analyzers.trades.get_analysis()
            total_closed = trade_info.get('total', {}).get('closed', 0)
            won_trades = trade_info.get('won', {}).get('total', 0)
            win_rate = (won_trades / total_closed * 100) if total_closed > 0 else 0.0
            max_dd = res.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
            
            print(f"{sym:<6} | {strat_name:<18} | ${final_val:<9.2f} | {win_rate:>4.1f}% | {max_dd:>4.1f}% | {total_closed}")

if __name__ == '__main__':
    run_arena()