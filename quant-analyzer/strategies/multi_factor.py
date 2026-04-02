"""
策略4：多因子选股策略
价值 + 成长 + 动量 因子综合评分
"""
import backtrader as bt
import numpy as np


class MultiFactorStrategy(bt.Strategy):
    """
    多因子策略 (简化版 — 在单股票上模拟)
    实际多因子需要多股票轮动，这里用技术指标作为因子代理
    """

    params = (
        ("value_period", 60),     # 估值周期
        ("growth_period", 20),    # 成长周期
        ("momentum_period", 30),  # 动量周期
        ("strategy_name", "多因子选股"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name

        # 价值因子代理：价格相对低位
        self.price_rank = bt.indicators.PercentRank(self.data.close, period=self.p.value_period)

        # 成长因子代理：近期涨幅
        self.growth = bt.indicators.ROC(self.data.close, period=self.p.growth_period)

        # 动量因子代理：价格趋势
        self.momentum = bt.indicators.ROC(self.data.close, period=self.p.momentum_period)

        # 趋势确认
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma60 = bt.indicators.SMA(self.data.close, period=60)

        # 成交量
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=20)

        self.order = None
        self.hold_days = 0
        self.rebalance_interval = 20  # 每20天重新评估

    def _calculate_score(self):
        """计算综合因子评分 (0-100)"""
        score = 0

        # 价值因子 (30%): 价格越低越好
        if self.price_rank[0] < 0.3:
            score += 30
        elif self.price_rank[0] < 0.5:
            score += 20
        elif self.price_rank[0] < 0.7:
            score += 10

        # 成长因子 (30%): 近期正增长
        if self.growth[0] > 0.1:
            score += 30
        elif self.growth[0] > 0.05:
            score += 20
        elif self.growth[0] > 0:
            score += 10

        # 动量因子 (20%): 正动量
        if self.momentum[0] > 0.05:
            score += 20
        elif self.momentum[0] > 0:
            score += 10

        # 趋势因子 (20%): 短期均线在长期上方
        if self.sma20[0] > self.sma60[0]:
            score += 20

        return score

    def next(self):
        if self.order:
            return

        if not self.position:
            score = self._calculate_score()
            # 综合评分超过60分买入
            if score >= 60:
                vol_ok = self.data.volume[0] > self.vol_ma[0] * 0.8
                if vol_ok:
                    size = self.broker.getcash() * 0.95 / self.data.close[0]
                    self.order = self.buy(size=int(size / 100) * 100)
                    self.hold_days = 0
        else:
            self.hold_days += 1
            # 每20天重新评估 或 评分过低
            if self.hold_days % self.rebalance_interval == 0:
                score = self._calculate_score()
                if score < 40:
                    self.order = self.close()

    def notify_order(self, order):
        self.order = None


class ValueMomentumStrategy(bt.Strategy):
    """价值动量组合策略"""

    params = (
        ("pe_threshold", 0.4),     # 估值百分位阈值
        ("momentum_period", 60),
        ("strategy_name", "价值动量组合"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.price_rank = bt.indicators.PercentRank(self.data.close, period=252)
        self.momentum = bt.indicators.ROC(self.data.close, period=self.p.momentum_period)
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # 估值低 + 动量正 + RSI不超买
            if (self.price_rank[0] < self.p.pe_threshold and
                self.momentum[0] > 0 and
                self.rsi[0] < 70):
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            # 动量转负 或 RSI超买
            if self.momentum[0] < -0.05 or self.rsi[0] > 85:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None
