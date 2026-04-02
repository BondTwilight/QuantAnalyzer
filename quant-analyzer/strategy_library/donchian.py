"""
唐奇安通道策略
价格突破N日最高价买入，跌破N日最低价卖出
海龟交易的简化入门版
"""
import backtrader as bt


class DonchianChannel(bt.Strategy):
    params = (
        ("period", 20),         # 通道周期
        ("atr_period", 20),     # ATR周期（用于止损）
        ("atr_stop", 2.0),      # ATR止损倍数
        ("position_pct", 0.95), # 仓位比例
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # 唐奇安通道
        self.highest = bt.indicators.Highest(self.datahigh, period=self.params.period)
        self.lowest = bt.indicators.Lowest(self.datalow, period=self.params.period)

        # ATR止损
        self.atr = bt.indicators.ATR(self.datas[0], period=self.params.atr_period)

        self.order = None
        self.entry_price = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            if order.isbuy():
                self.entry_price = order.executed.price
            else:
                self.entry_price = None
        self.order = None

    def next(self):
        if self.order:
            return

        close = self.dataclose[0]
        channel_high = self.highest[-1]  # 上周期收盘后的通道上轨
        channel_low = self.lowest[-1]
        atr_val = self.atr[0]

        # 持仓中：ATR跟踪止损
        if self.position.size > 0 and self.entry_price:
            stop_loss = self.entry_price - self.params.atr_stop * atr_val
            if close < stop_loss:
                self.order = self.close()
                return

        # 无持仓：突破通道入场
        if self.position.size == 0:
            if close > channel_high:
                size = int(self.broker.getcash() * self.params.position_pct / close / 100) * 100
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            # 持仓中：跌破通道下轨 + N天后
            if close < channel_low:
                self.order = self.close()
