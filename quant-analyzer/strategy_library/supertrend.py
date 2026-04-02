"""
超级趋势线策略
使用超级趋势指标（Supertrend），趋势向上时做多，向下时做空
结合波动率自适应参数
"""
import backtrader as bt
import math


class Supertrend(bt.Strategy):
    params = (
        ("period", 10),
        ("multiplier", 3.0),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # ATR (用于HL2计算)
        self.atr = bt.indicators.ATR(self.datas[0], period=self.params.period)

        # 手动计算超级趋势
        self.order = None
        self.supert = None
        self.upperband = None
        self.lowerband = None

        # 初始化
        self._hl2 = (self.datahigh[0] + self.datalow[0]) / 2

    def _calc_supertrend(self):
        hl2 = (self.datahigh[0] + self.datalow[0]) / 2
        atr_val = self.atr[0]
        mult = self.params.multiplier

        upper = hl2 + mult * atr_val
        lower = hl2 - mult * atr_val

        # 简单版本的超级趋势
        close = self.dataclose[0]
        prev_close = self.dataclose[-1]

        if self.supert is None:
            self.supert = close
            self.upperband = upper
            self.lowerband = lower
        else:
            if close > self.upperband:
                self.supert = close
            elif close < self.lowerband:
                self.supert = close
            else:
                if prev_close > self.supert:
                    self.supert = max(self.lowerband, self.supert)
                else:
                    self.supert = min(self.upperband, self.supert)

            self.upperband = upper
            self.lowerband = lower

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None

    def next(self):
        if self.order:
            return

        self._calc_supertrend()
        close = self.dataclose[0]

        # 趋势由跌转涨 -> 买入
        if close > self.supert and self.position.size == 0:
            self.order = self.buy()

        # 趋势由涨转跌 -> 卖出
        elif close < self.supert and self.position.size > 0:
            self.order = self.close()
