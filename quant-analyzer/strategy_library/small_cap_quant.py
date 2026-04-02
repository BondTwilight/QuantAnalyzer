"""
小市值量化策略
按市值从小到大排序，选取最小N%的股票，等权配置，每月轮换
叠加动量和价值过滤
"""
import backtrader as bt
import numpy as np


class SmallCapQuant(bt.Strategy):
    """
    简化版小市值策略
    注意：完整版需要市值数据和每日重新排序
    这里使用价格动量作为近似指标
    """
    params = (
        ("lookback", 60),        # 动量周期
        ("rebalance_days", 20),  # 调仓周期
        ("size_pct", 0.95),      # 仓位
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.days_since_trade = 0

        # 动量指标
        self.momentum = bt.indicators.Momentum(
            self.datas[0].close, period=self.params.lookback
        )

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None

    def next(self):
        if len(self) < self.params.lookback:
            return
        if self.order:
            return

        self.days_since_trade += 1
        close = self.dataclose[0]
        mom = self.momentum[0]

        # 动量为正且超过调仓周期 -> 买入持有
        if mom > 0 and self.position.size == 0 and self.days_since_trade >= self.params.rebalance_days:
            size = int(self.broker.getcash() * self.params.size_pct / close / 100) * 100
            if size > 0:
                self.order = self.buy(size=size)

        # 动量转负 -> 卖出
        elif mom < 0 and self.position.size > 0:
            self.order = self.close()
            self.days_since_trade = 0
