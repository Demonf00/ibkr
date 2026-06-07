class TradingCostModel:
    """
    简化成本模型：
    - commission_per_share: 每股佣金估算
    - min_commission: 每笔最低佣金估算
    - slippage_bps: 滑点估算，1 bps = 0.01%

    注意：真实 IBKR 费用会因账户类型、交易所、路由、国家、定价计划变化。
    所以这里必须是 config 参数，而不是写死策略里。
    """

    def __init__(
        self,
        commission_per_share: float = 0.005,
        min_commission: float = 1.0,
        slippage_bps: float = 2.0,
    ):
        self.commission_per_share = commission_per_share
        self.min_commission = min_commission
        self.slippage_bps = slippage_bps

    def estimate(self, price: float, quantity: int) -> dict:
        trade_value = price * quantity

        if trade_value <= 0:
            return {
                "commission": 0.0,
                "slippage": 0.0,
                "total_cost": 0.0,
                "cost_bps": 0.0,
            }

        commission = max(
            self.min_commission,
            self.commission_per_share * quantity,
        )

        slippage = trade_value * self.slippage_bps / 10_000
        total_cost = commission + slippage
        cost_bps = total_cost / trade_value * 10_000

        return {
            "commission": commission,
            "slippage": slippage,
            "total_cost": total_cost,
            "cost_bps": cost_bps,
        }