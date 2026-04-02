"""
波动率突破策略
波动率放大时顺势交易，使用ATR衡量波动，配合N日突破确认
"""
import backtrader as bt


class VolatilityBreakout(bt.Strategy):
    params = (
        ("atr_period", 14),
        ("breakout_period", 20),
        ("atr_multiplier", 2.0),
        ("position_size", 0.95),  # 仓位
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # ATR
        self.atr = bt.indicators.ATR(self.datas[0], period=self.params.atr_period)
        # N日最高/最低
        self.highest = bt.indicators.Highest(self.datahigh, period=self.params.breakout_period)
        self.lowest = bt.indicators.Lowest(self.datalow, period=self.params.breakout_period)

        self.order = None
        self.highest_ok = False
        self.lowest_ok = False

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None

    def next(self):
        if len(self) < self.params.breakout_period:
            return
        if self.order:
            return

        close = self.dataclose[0]
        atr_val = self.atr[0]
        break_high = self.highest[-self.params.breakout_period]
        break_low = self.lowest[-self.params.breakout_period]

        # 价格突破20日高点 + ATR放大
        if close > break_high:
            size = int(self.broker.getcash() * self.params.position_size / close / 100) * 100
            if size > 0:
                self.order = self.buy(size=size)

        # 价格跌破20日低点
        elif close < break_low:
            self.order = self.close()
