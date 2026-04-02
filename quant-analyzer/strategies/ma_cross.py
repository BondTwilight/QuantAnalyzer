"""
策略1：双均线交叉策略 (MA Cross)
经典趋势跟踪策略 — 金叉买入，死叉卖出
"""
import backtrader as bt
import numpy as np


class MACrossStrategy(bt.Strategy):
    """双均线交叉策略"""

    params = (
        ("fast_period", 10),   # 快线周期
        ("slow_period", 30),   # 慢线周期
        ("strategy_name", "双均线交叉"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.p.fast_period)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        self.order = None
        self.trade_count = 0

    def next(self):
        if self.order:
            return

        if not self.position:
            # 金叉买入
            if self.crossover > 0:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            # 死叉卖出
            if self.crossover < 0:
                self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.trade_count += 1
        self.order = None


class MACrossStrategy_v2(bt.Strategy):
    """双均线交叉 v2 — 带成交量确认"""

    params = (
        ("fast_period", 5),
        ("slow_period", 20),
        ("vol_period", 20),
        ("strategy_name", "双均线交叉V2"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.p.fast_period)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.p.slow_period)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.vol_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        self.order = None

    def next(self):
        if self.order:
            return

        vol_ok = self.data.volume[0] > self.vol_ma[0] * 1.2  # 成交量放大20%

        if not self.position:
            if self.crossover > 0 and vol_ok:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            if self.crossover < 0:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None
