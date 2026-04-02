"""
策略6：布林带策略 (Bollinger Bands)
均值回归 + 波动率突破
"""
import backtrader as bt
import numpy as np


class BollingerBandStrategy(bt.Strategy):
    """布林带均值回归策略"""

    params = (
        ("bb_period", 20),
        ("bb_dev", 2.0),
        ("strategy_name", "布林带策略"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.p.bb_period,
            devfactor=self.p.bb_dev
        )
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # 价格触及下轨买入
            if self.data.close[0] <= self.boll.lines.bot[0]:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            # 价格触及上轨或回到中轨卖出
            if self.data.close[0] >= self.boll.lines.top[0] or self.data.close[0] >= self.boll.lines.mid[0]:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None


class BollingerSqueeze(bt.Strategy):
    """布林带收缩突破策略"""

    params = (
        ("bb_period", 20),
        ("bb_dev", 2.0),
        ("atr_period", 14),
        ("strategy_name", "布林带突破"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.boll = bt.indicators.BollingerBands(self.data.close, period=self.p.bb_period, devfactor=self.p.bb_dev)
        self.atr = bt.indicators.ATR(self.data.close, period=self.p.atr_period)
        self.bb_width = (self.boll.lines.top - self.boll.lines.bot) / self.boll.lines.mid
        self.order = None

    def next(self):
        if self.order:
            return

        # 布林带宽度
        current_width = self.bb_width[0]

        if not self.position:
            # 价格突破上轨且ATR放大
            if (self.data.close[0] > self.boll.lines.top[0] and
                self.data.volume[0] > self.data.volume[-1]):
                size = self.broker.getcash() * 0.5 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            # 回到布林带中轨以下止损
            if self.data.close[0] < self.boll.lines.mid[0]:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None
