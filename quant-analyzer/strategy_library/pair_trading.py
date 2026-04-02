"""
配对交易策略
监控两只高度相关股票的价格差，当差价偏离均值时做多低估、做空高估
注意：需要传入两只相关联的股票数据
"""
import backtrader as bt
import numpy as np


class PairTrading(bt.Strategy):
    params = (
        ("lookback", 60),
        ("entry_threshold", 2.0),
        ("exit_threshold", 0.5),
        ("allocation", 0.5),
    )

    def __init__(self):
        if len(self.datas) < 2:
            raise ValueError("配对交易需要至少2只股票的数据")

        self.pair1 = self.datas[0]  # 第一只股票
        self.pair2 = self.datas[1]  # 第二只股票

        self.order = None
        self.spread_history = []
        self.mean_spread = None
        self.std_spread = None

    def log(self, txt):
        pass

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None

    def next(self):
        if len(self) < self.params.lookback:
            return
        if self.order:
            return

        # 计算历史价差比例
        p1_prices = [d.close[0] for d in self.pair1.lines.get(size=self.params.lookback)]
        p2_prices = [d.close[0] for d in self.pair2.lines.get(size=self.params.lookback)]

        spreads = [p1 / p2 for p1, p2 in zip(p1_prices, p2_prices)]
        mean_s = np.mean(spreads)
        std_s = np.std(spreads)

        current_spread = self.pair1.close[0] / self.pair2.close[0]
        z_score = (current_spread - mean_s) / std_s if std_s > 0 else 0

        # 入场
        if z_score > self.params.entry_threshold:
            # 做空pair1，做多pair2
            if not self.getposition(self.pair1).size:
                self.sell(self.pair1, size=int(self.broker.getcash() * self.params.allocation / self.pair1.close[0] / 100) * 100)
                self.buy(self.pair2, size=int(self.broker.getcash() * self.params.allocation / self.pair2.close[0] / 100) * 100)

        elif z_score < -self.params.entry_threshold:
            # 做多pair1，做空pair2
            if not self.getposition(self.pair1).size:
                self.buy(self.pair1, size=int(self.broker.getcash() * self.params.allocation / self.pair1.close[0] / 100) * 100)
                self.sell(self.pair2, size=int(self.broker.getcash() * self.params.allocation / self.pair2.close[0] / 100) * 100)

        # 平仓
        elif abs(z_score) < self.params.exit_threshold:
            self.close()
