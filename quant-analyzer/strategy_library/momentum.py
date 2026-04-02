"""
动量策略
追涨杀跌策略：过去N日收益率为正则持有，负则空仓
"""
import backtrader as bt


class Momentum(bt.Strategy):
    """动量策略"""
    
    params = (
        ("period", 20),       # 动量计算周期
        ("ma_period", 50),    # 均线过滤周期
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # 动量指标 (价格变化率)
        self.momentum = bt.indicators.Momentum(
            self.datas[0].close,
            period=self.params.period
        )
        
        # 均线过滤
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0].close,
            period=self.params.ma_period
        )
        
        self.order = None
        
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
            
        close = self.dataclose[0]
        mom = self.momentum[0]
        
        # 动量为正且价格在均线上方，持有多头或买入
        if mom > 0 and close > self.sma[0]:
            if not self.position:
                self.order = self.buy()
                
        # 动量为负或价格在均线下方，平仓
        elif (mom < 0 or close < self.sma[0]) and self.position:
            self.order = self.close()
