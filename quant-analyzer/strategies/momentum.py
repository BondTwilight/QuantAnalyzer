"""
策略3：动量策略 (Momentum)
价格动量 + 成交量确认
"""
import backtrader as bt
import numpy as np


class MomentumStrategy(bt.Strategy):
    """简单动量策略 — 追涨杀跌"""

    params = (
        ("lookback", 20),         # 动量回看期
        ("threshold", 0.05),      # 最小动量阈值
        ("hold_period", 10),      # 持有天数
        ("strategy_name", "动量策略"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.momentum = bt.indicators.ROC(self.data.close, period=self.p.lookback)
        self.order = None
        self.hold_days = 0

    def next(self):
        if self.order:
            return

        if not self.position:
            # 动量超过阈值买入
            if self.momentum[0] > self.p.threshold:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
                self.hold_days = 0
        else:
            self.hold_days += 1
            # 持有到期 或 动量反转
            if self.hold_days >= self.p.hold_period or self.momentum[0] < -self.p.threshold:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None


class DualMomentumStrategy(bt.Strategy):
    """双重动量策略 — 绝对动量 + 相对动量"""

    params = (
        ("lookback", 60),
        ("ma_period", 200),
        ("strategy_name", "双重动量"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.momentum = bt.indicators.ROC(self.data.close, period=self.p.lookback)
        self.sma200 = bt.indicators.SMA(self.data.close, period=self.p.ma_period)
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # 价格在200MA上方 且 动量为正
            if self.data.close[0] > self.sma200[0] and self.momentum[0] > 0:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            # 价格跌破200MA 或 动量为负
            if self.data.close[0] < self.sma200[0] or self.momentum[0] < -0.1:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None
