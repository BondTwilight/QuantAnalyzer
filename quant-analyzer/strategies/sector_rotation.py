"""
策略5：行业轮动策略 (Sector Rotation)
基于动量的行业配置策略
"""
import backtrader as bt
import numpy as np
from datetime import datetime, timedelta


class SectorRotationStrategy(bt.Strategy):
    """
    行业轮动策略 (简化版)
    在单股票上模拟行业轮动逻辑：
    - 计算不同"行业信号"（用不同周期的动量作为代理）
    - 选择动量最强的信号进行交易
    """

    params = (
        ("fast_period", 10),      # 短期动量
        ("medium_period", 30),    # 中期动量
        ("slow_period", 60),      # 长期动量
        ("rebalance_days", 20),   # 轮动周期
        ("strategy_name", "行业轮动"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name

        # 多周期动量作为"行业强度"代理
        self.mom_fast = bt.indicators.ROC(self.data.close, period=self.p.fast_period)
        self.mom_medium = bt.indicators.ROC(self.data.close, period=self.p.medium_period)
        self.mom_slow = bt.indicators.ROC(self.data.close, period=self.p.slow_period)

        # 趋势指标
        self.sma_short = bt.indicators.SMA(self.data.close, period=10)
        self.sma_long = bt.indicators.SMA(self.data.close, period=60)

        # 波动率
        self.atr = bt.indicators.ATR(self.data, period=14)

        # 成交量
        self.vol_sma = bt.indicators.SMA(self.data.volume, period=20)

        self.order = None
        self.days_since_rebalance = 0
        self.in_uptrend = False

    def _rotation_signal(self):
        """
        轮动信号计算
        模拟行业轮动：综合短期+中期+长期动量
        """
        # 加权动量得分
        score = (self.mom_fast[0] * 0.5 +
                 self.mom_medium[0] * 0.3 +
                 self.mom_slow[0] * 0.2)

        # 趋势确认
        trend_ok = self.sma_short[0] > self.sma_long[0]

        # 波动率过滤（低波优先）
        vol_ok = self.atr[0] < self.atr[0] * 2  # 波动率不过高

        return score > 0.02 and trend_ok and vol_ok

    def next(self):
        if self.order:
            return

        self.days_since_rebalance += 1

        if not self.position:
            # 轮动信号触发买入
            if self._rotation_signal():
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
                self.days_since_rebalance = 0
                self.in_uptrend = True
        else:
            # 到达轮动周期重新评估
            if self.days_since_rebalance >= self.p.rebalance_days:
                if not self._rotation_signal():
                    self.order = self.close()
                    self.in_uptrend = False
                    self.days_since_rebalance = 0

    def notify_order(self, order):
        self.order = None


class TacticalAllocationStrategy(bt.Strategy):
    """战术性资产配置策略"""

    params = (
        ("momentum_lookback", 120),
        ("vol_lookback", 20),
        ("strategy_name", "战术资产配置"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.momentum = bt.indicators.ROC(self.data.close, period=self.p.momentum_lookback)
        self.atr = bt.indicators.ATR(self.data.close, period=self.p.vol_lookback)
        self.sma200 = bt.indicators.SMA(self.data.close, period=200)
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # 正动量 + 在200日线上方
            if self.momentum[0] > 0 and self.data.close[0] > self.sma200[0]:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
        else:
            # 负动量 或 跌破200日线
            if self.momentum[0] < -0.05 or self.data.close[0] < self.sma200[0]:
                self.order = self.close()

    def notify_order(self, order):
        self.order = None
