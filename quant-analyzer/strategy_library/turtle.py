"""
海龟交易法则
经典趋势跟踪策略，使用N日突破作为入场信号
"""
import backtrader as bt


class Turtle(bt.Strategy):
    """海龟交易法则"""
    
    params = (
        ("period_entry", 20),   # 入场突破周期
        ("period_exit", 10),     # 出场突破周期
        ("atr_period", 20),      # ATR周期
        ("atr_multiplier", 2.0), # ATR倍数
        ("max_size", 4),         # 最大仓位单位
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        
        # 唐奇安通道
        self.donchian_entry = bt.indicators.Highest(
            self.datas[0].high, period=self.params.period_entry
        )
        self.donchian_exit = bt.indicators.Lowest(
            self.datas[0].low, period=self.params.period_exit
        )
        
        # ATR
        self.atr = bt.indicators.ATR(
            self.datas[0],
            period=self.params.atr_period
        )
        
        self.order = None
        self.entry_price = None
        self.size_units = 0
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.size_units += 1
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.order = None
            
    def next(self):
        if self.order:
            return
            
        close = self.dataclose[0]
        high = self.datas[0].high[0]
        low = self.datas[0].low[0]
        
        # 入场信号：价格突破20日高点
        if high > self.donchian_entry[-1] and not self.position:
            self.order = self.buy()
            self.entry_price = close
            
        # 出场信号：价格跌破10日低点
        elif low < self.donchian_exit[-1] and self.position:
            self.order = self.close()
            self.size_units = 0
            
        # 止损：跌破2ATR
        elif self.position and self.entry_price:
            stop_loss = self.entry_price - self.params.atr_multiplier * self.atr[0]
            if close < stop_loss:
                self.order = self.close()
                self.size_units = 0
