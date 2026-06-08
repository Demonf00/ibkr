import backtrader as bt
import yfinance as yf
import pandas as pd

# ==========================================
# 0. 数据探针 (自定义最终资金 Analyzer)
# ==========================================
class PortfolioValueAnalyzer(bt.Analyzer):
    def stop(self):
        self.final_val = self.strategy.broker.getvalue()
    def get_analysis(self):
        return {"final_value": self.final_val}

# ==========================================
# 1. 绝对真实的交易成本模型 (对标 IBKR)
# ==========================================
class IBKRCommissionInfo(bt.CommInfoBase):
    params = (('commission', 0.005), ('margin', None), ('mult', 1.0), ('min_comm', 1.0), ('stocklike', True), ('commtype', bt.CommInfoBase.COMM_FIXED))
    def _getcommission(self, size, price, pseudoexec):
        return max(abs(size) * self.p.commission, self.p.min_comm)

# ==========================================
# 2. V-AR (波动率自适应回归) 策略
# ==========================================
class VolatilityReversionBT(bt.Strategy):
    params = (
        ('window', 20),
        ('std_dev', 2.5),
        ('atr_window', 14),
        ('risk_per_trade', 0.90), # 🔥 核心修改：90% 仓位拉满 🔥
    )

    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.window)
        self.std = bt.indicators.StdDev(self.data.close, period=self.p.window)
        self.boll_upper = self.sma + (self.p.std_dev * self.std)
        self.boll_lower = self.sma - (self.p.std_dev * self.std)
        self.order = None

    def next(self):
        if self.order: return

        curr_close = self.data.close[0]
        curr_sma = self.sma[0]

        if not self.position:
            if curr_close < self.boll_lower[0]:
                # 按 90% 仓位买入
                target_value = self.broker.getcash() * self.p.risk_per_trade
                qty = int(target_value / curr_close)
                if qty > 0:
                    self.order = self.buy(size=qty)
        else:
            if curr_close > self.boll_upper[0] or curr_close >= curr_sma:
                self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None

# ==========================================
# 3. 核心运行逻辑
# ==========================================
def run_backtest():
    cerebro = bt.Cerebro()

    print("正在下载历史数据...")
    df = yf.download('SPY', start='2019-01-01', end='2024-01-01', progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    # 加载优化策略
    cerebro.optstrategy(
        VolatilityReversionBT,
        std_dev=[1.5, 2.0, 2.5, 3.0],
        window=[10, 15, 20, 25, 30]
    )

    cerebro.broker.setcash(100000.0)
    cerebro.broker.addcommissioninfo(IBKRCommissionInfo())
    cerebro.broker.set_slippage_perc(perc=0.0002)

    # 🔥 新增：挂载官方硬核分析器 🔥
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(PortfolioValueAnalyzer, _name='my_value')

    print("开始多核参数优化，请稍候...")
    results = cerebro.run()
    
    performance = []
    for run in results:
        for strat in run:
            # 提取最终资金
            final_value = strat.analyzers.my_value.get_analysis()['final_value']
            
            # 提取交易胜率
            trade_info = strat.analyzers.trades.get_analysis()
            total_closed = trade_info.get('total', {}).get('closed', 0)
            won_trades = trade_info.get('won', {}).get('total', 0)
            win_rate = (won_trades / total_closed * 100) if total_closed > 0 else 0.0
            
            # 提取最大回撤
            dd_info = strat.analyzers.drawdown.get_analysis()
            max_dd = dd_info.get('max', {}).get('drawdown', 0.0)
            
            performance.append({
                'window': strat.params.window,
                'std_dev': strat.params.std_dev,
                'final_value': final_value,
                'win_rate': win_rate,
                'max_dd': max_dd,
                'total_trades': total_closed
            })
    
    # 依然按最终资金排序
    performance.sort(key=lambda x: x['final_value'], reverse=True)

    print("\n" + "="*50)
    print("🏆 90% 仓位火力全开：最佳参数 TOP 5 🏆")
    print("="*50)
    for i, p in enumerate(performance[:5]):
        print(f"Top {i+1}: Window={p['window']:<2}, StdDev={p['std_dev']:<3} | "
              f"期末资金: ${p['final_value']:<9.2f} | "
              f"胜率: {p['win_rate']:<5.1f}% | "
              f"最大回撤: {p['max_dd']:<5.1f}% | "
              f"交易次数: {p['total_trades']}")

if __name__ == '__main__':
    run_backtest()