"""
一目均衡表策略
基于日本Ichimoku Kinko Hyo系统
"""
import backtrader as bt


class IchimokuCloud(bt.Strategy):
    """一目均衡表策略"""
    
    params = (
        ("tenkan", 9),       # 转换线周期
        ("kijun", 26),       # 基准线周期
        ("senkou_b", 52),    # 延迟线周期
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # 转换线
        self.tenkan_sen = (bt.indicators.Highest(self.datahigh, period=self.params.tenkan) +
                          bt.indicators.Lowest(self.datalow, period=self.params.tenkan)) / 2
        
        # 基准线
        self.kijun_sen = (bt.indicators.Highest(self.datahigh, period=self.params.kijun) +
                         bt.indicators.Lowest(self.datalow, period=self.params.kijun)) / 2
        
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
            
        # 转换线与基准线交叉
        tenkan = self.tenkan_sen[0]
        kijun = self.kijun_sen[0]
        tenkan_prev = self.tenkan_sen[-1]
        kijun_prev = self.kijun_sen[-1]
        
        close = self.dataclose[0]
        
        # 转换线从下穿上基准线 (买入信号)
        if tenkan_prev < kijun_prev and tenkan > kijun:
            if not self.position and close > kijun:
                self.order = self.buy()
                
        # 转换线从上穿下基准线 (卖出信号)
        elif tenkan_prev > kijun_prev and tenkan < kijun:
            if self.position:
                self.order = self.close()
