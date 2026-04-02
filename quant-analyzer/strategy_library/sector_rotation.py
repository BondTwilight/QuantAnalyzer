"""
板块轮动策略
跟踪行业动量，每月轮动到近期最强板块
"""
import backtrader as bt


class SectorRotation(bt.Strategy):
    """板块轮动策略"""
    
    params = (
        ("lookback", 60),      # 动量回看周期
        ("top_n", 3),          # 选择前N名
        ("ma_period", 50),     # 均线过滤周期
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # 动量指标
        self.momentum = bt.indicators.Momentum(
            self.datas[0].close,
            period=self.params.lookback
        )
        
        # 均线
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0].close,
            period=self.params.ma_period
        )
        
        self.order = None
        self.rebalance_day = 0
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.order = None
            
    def next(self):
        if self.order:
            return
            
        # 每月再平衡一次 (简化：每20个交易日)
        current_day = len(self)
        if current_day - self.rebalance_day < 20:
            return
            
        close = self.dataclose[0]
        mom = self.momentum[0]
        
        # 动量为正且价格在均线上方
        if mom > 0 and close > self.sma[0]:
            if not self.position:
                self.order = self.buy()
                self.rebalance_day = current_day
        # 动量为负或价格在均线下方
        elif (mom < 0 or close < self.sma[0]) and self.position:
            self.order = self.close()
            self.rebalance_day = current_day
