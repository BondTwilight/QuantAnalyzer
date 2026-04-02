"""
均值回归策略
价格偏离均线超过2倍标准差时反向操作，配合RSI确认信号
"""
import backtrader as bt


class MeanReversion(bt.Strategy):
    params = (
        ("period", 20),
        ("dev", 2.0),
        ("rsi_period", 14),
        ("rsi_buy", 30),
        ("rsi_sell", 70),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open

        # 布林带
        self.boll = bt.indicators.BollingerBands(
            self.datas[0], period=self.params.period, devfactor=self.params.dev
        )
        # RSI
        self.rsi = bt.indicators.RSI(
            self.datas[0].close, period=self.params.rsi_period
        )

        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                pass
            else:
                pass
        self.order = None

    def next(self):
        if self.order:
            return

        close = self.dataclose[0]
        lower = self.boll.lines.bot[0]
        upper = self.boll.lines.top[0]
        rsi_val = self.rsi[0]

        # 触及下轨且RSI超卖 -> 买入
        if close < lower and rsi_val < self.params.rsi_buy:
            self.order = self.buy()
        # 触及上轨且RSI超买 -> 卖出
        elif close > upper and rsi_val > self.params.rsi_sell:
            self.order = self.close()
