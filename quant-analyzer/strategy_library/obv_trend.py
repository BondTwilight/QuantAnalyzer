"""
OBV量价趋势策略
基于能量潮指标OBD的趋势跟踪，配合均线过滤假信号
"""
import backtrader as bt


class OBVTrend(bt.Strategy):
    params = (
        ("obv_period", 20),
        ("ma_period", 30),
        ("confirm_bars", 2),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datavol = self.datas[0].volume

        # OBV
        self.obv = bt.indicators.OBV(self.datas[0])
        self.obv_ma = bt.indicators.SMA(self.obv, period=self.params.obv_period)

        # 价格均线
        self.ma = bt.indicators.SMA(self.dataclose, period=self.params.ma_period)

        # 持仓状态
        self.order = None
        self.bars_held = 0
        self.was_below = True

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.bars_held = 0
            else:
                self.bars_held = 0
        self.order = None

    def next(self):
        if self.order:
            return

        # 跟踪持仓时间
        if self.position.size > 0:
            self.bars_held += 1

        close = self.dataclose[0]
        obv_val = self.obv[0]
        obv_ma_val = self.obv_ma[0]
        ma_val = self.ma[0]

        # 买入信号：OBV上穿均线 + 价格在均线上方
        if obv_val > obv_ma_val and close > ma_val and self.position.size == 0:
            self.order = self.buy()

        # 卖出信号：OBV下穿均线 或 价格跌破均线
        elif (obv_val < obv_ma_val or close < ma_val) and self.position.size > 0:
            self.order = self.close()
