"""
聚宽经典策略: 小市值策略 (复现)
聚宽上最受欢迎的策略之一 — 选取市值最小的N只股票，定期轮动
原始逻辑: 每月第一个交易日，买入市值最小的30只股票，等权重持有

这里简化为在单股票上用市值代理指标进行交易：
- 用价格百分位作为市值代理（低价≈小市值）
- 20日定期调仓
- 结合成交量确认
"""
import backtrader as bt
import numpy as np


class JQSmallCapStrategy(bt.Strategy):
    """聚宽小市值策略 — 在单股票上的近似实现"""

    params = (
        ("lookback", 252),        # 一年百分位
        ("rebalance_days", 20),    # 月度调仓
        ("percentile_low", 0.3),   # 低价位阈值
        ("strategy_name", "聚宽小市值"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        # 价格百分位（市值代理）
        self.price_rank = bt.indicators.PercentRank(self.data.close, period=self.p.lookback)
        # 趋势确认
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma60 = bt.indicators.SMA(self.data.close, period=60)
        # 成交量
        self.vol_sma = bt.indicators.SMA(self.data.volume, period=20)
        self.order = None
        self.hold_days = 0

    def next(self):
        if self.order:
            return

        if not self.position:
            # 价格在低位（模拟小市值效应）+ 趋势企稳
            if (self.price_rank[0] < self.p.percentile_low and
                self.sma20[0] > self.sma60[0] and  # 均线多头
                self.data.volume[0] > self.vol_sma[0] * 0.8):  # 成交量正常
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
                self.hold_days = 0
        else:
            self.hold_days += 1
            # 定期调仓 + 止损
            stop_loss = self.data.close[0] < self.sma60[0] * 0.95
            if (self.hold_days >= self.p.rebalance_days and
                self.price_rank[0] > 0.5) or stop_loss:
                self.order = self.close()
                self.hold_days = 0

    def notify_order(self, order):
        self.order = None


class JQDualThrustStrategy(bt.Strategy):
    """
    聚宽经典策略: Dual Thrust 突破策略
    A股最经典的日内突破策略，这里改为日线级别
    逻辑: 计算N日最高价、最低价、收盘价的范围，突破上轨买入，跌破下轨卖出
    """

    params = (
        ("lookback", 20),
        ("k1", 0.5),     # 上轨系数
        ("k2", 0.5),     # 下轨系数
        ("strategy_name", "聚宽DualThrust"),
    )

    def __init__(self):
        self.strategy_name = self.params.strategy_name
        self.highest = bt.indicators.Highest(self.data.high, period=self.p.lookback)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.p.lookback)
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.lookback)
        self.order = None
        self.hold_days = 0

    def _calc_range(self):
        """计算Dual Thrust范围"""
        hh = self.highest[0]  # N日最高
        ll = self.lowest[0]    # N日最低
        hc = self.sma[0]      # 收盘均线作为中轨
        return hh, ll, hc

    def next(self):
        if self.order:
            return

        hh, ll, hc = self._calc_range()
        range_val = hh - ll
        upper = hc + self.p.k1 * range_val
        lower = hc - self.p.k2 * range_val

        if not self.position:
            if self.data.close[0] > upper:
                size = self.broker.getcash() * 0.95 / self.data.close[0]
                self.order = self.buy(size=int(size / 100) * 100)
                self.hold_days = 0
        else:
            self.hold_days += 1
            if self.data.close[0] < lower or self.hold_days > 30:
                self.order = self.close()
                self.hold_days = 0

    def notify_order(self, order):
        self.order = None
