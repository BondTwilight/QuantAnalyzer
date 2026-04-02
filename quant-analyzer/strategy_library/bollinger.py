"""
布林带均值回归策略
价格触及布林带下轨买入，上轨卖出
"""
import backtrader as bt


class BollingerBands(bt.Strategy):
    """布林带均值回归策略"""
    
    params = (
        ("period", 20),        # 布林带周期
        ("devfactor", 2.0),    # 标准差倍数
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # 布林带指标
        self.boll = bt.indicators.BollingerBands(
            self.datas[0],
            period=self.params.period,
            devfactor=self.params.devfactor
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
        lower = self.boll.lines.bot[0]
        upper = self.boll.lines.top[0]
        middle = self.boll.lines.mid[0]
        
        # 价格触及下轨且低于均线，买入
        if close < lower and not self.position:
            self.order = self.buy()
            
        # 价格触及上轨且高于均线，卖出
        elif close > upper and self.position:
            self.order = self.close()
