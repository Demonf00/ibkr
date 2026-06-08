from models import OrderRequest, SignalAction


class OrderManager:
    def __init__(self, broker, risk_manager, dry_run: bool = True):
        self.broker = broker
        self.risk_manager = risk_manager
        self.dry_run = dry_run

    def handle_signal(self, signal):
        if signal.action == SignalAction.HOLD:
            print(
                f"[FinalSignal] symbol={signal.symbol} action=HOLD "
                f"reason={signal.reason}"
            )
            return None

        order = OrderRequest(
            symbol=signal.symbol,
            side=signal.action,
            quantity=signal.quantity,
            strategy_name=signal.strategy_name,
            reason=signal.reason,
            source_strategies=signal.source_strategies,
        )

        price = self.broker.get_market_price(order.symbol)

        self.risk_manager.validate_order(order, price, self.broker)

        if self.dry_run:
            print(
                f"[DryRun] Would place order: "
                f"{order.side.value} {order.quantity} {order.symbol} "
                f"price={price:.2f}, sources={order.source_strategies}, "
                f"reason={order.reason}"
            )
            return None

        print(
            f"[Order] Placing market order: "
            f"{order.side.value} {order.quantity} {order.symbol}"
        )

        trade = self.broker.place_market_order(
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
        )

        self.risk_manager.record_order(order)

        return trade