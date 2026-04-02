"""
因子择时策略
综合动量、价值、波动率因子，根据因子综合得分调整仓位
"""
import backtrader as bt
import numpy as np


class FactorTiming(bt.Strategy):
    params = (
        ("mom_period", 60),       # 动量周期
        ("vol_period", 20),       # 波动率周期
        ("position_size", 0.95), # 最大仓位
        ("score_threshold", 0.3),# 得分阈值
    )

    def __init__(self):
        self.dataclose = self.datas[0].close

        # 因子1: 动量 (简单收益率)
        self.momentum = bt.indicators.Momentum(
            self.datas[0].close, period=self.params.mom_period
        )

        # 因子2: 波动率 (ATR相对值)
        self.atr = bt.indicators.ATR(self.datas[0], period=self.params.vol_period)
        self.atr_pct = self.atr / self.dataclose

        # 因子3: 均线偏离
        self.ma = bt.indicators.SMA(self.datas[0].close, period=20)
        self.ma_dev = (self.dataclose - self.ma) / self.ma

        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None

    def next(self):
        if len(self) < max(self.params.mom_period, self.params.vol_period):
            return
        if self.order:
            return

        close = self.dataclose[0]

        # 因子打分 (标准化到-1~1)
        mom_norm = np.tanh(self.momentum[0] / close * 100 / 10)  # 动量归一化
        vol_risk = -np.tanh(self.atr_pct[0] * 100 / 5)           # 波动率低=好
        ma_pos = np.tanh(self.ma_dev[0] * 10)                    # 价格在均线上=好

        # 综合得分
        score = (mom_norm + vol_risk + ma_pos) / 3.0

        # 得分高 -> 满仓， 低 -> 空仓
        if score > self.params.score_threshold and self.position.size == 0:
            size = int(self.broker.getcash() * self.params.position_size / close / 100) * 100
            if size > 0:
                self.order = self.buy(size=size)

        elif score < -self.params.score_threshold and self.position.size > 0:
            self.order = self.close()
