"""
策略2：RSI 超买超卖策略
经典均值回归策略 — RSI低位买入，高位卖出
"""
import backtrader as bt
import numpy as np


class RSIStrategy(bt.Strategy):
    """RSI 均值回归策略"""

    params = (
        ("rsi_period", 14),       # RSI周期
        ("oversold", 30),         # 超卖阈值
        ("overbought", 70),       # 超买阈值
        ("strategy_name", "RSI均值回归"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # RSI低于超卖线买入
            if self.rsi[0] < self.p.oversold:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            # RSI高于超买线卖出
            if self.rsi[0] > self.p.overbought:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None


class RSIMACDStrategy(bt.Strategy):
    """RSI + MACD 组合策略"""

    params = (
        ("rsi_period", 14),
        ("oversold", 25),
        ("overbought", 75),
        ("strategy_name", "RSI+MACD组合"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(self.data.close)
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # RSI超卖 + MACD金叉
            if self.rsi[0] < self.p.oversold and self.macd_cross > 0:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            # RSI超买 或 MACD死叉
            if self.rsi[0] > self.p.overbought or self.macd_cross < 0:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None
