"""
MACD趋势策略
使用MACD指标的金叉死叉作为交易信号，过滤假突破
"""
import backtrader as bt


class MACDStrategy(bt.Strategy):
    """MACD趋势策略"""
    
    params = (
        ("fast", 12),       # 快线EMA周期
        ("slow", 26),       # 慢线EMA周期
        ("signal", 9),      # Signal线周期
        ("atr_period", 14), # ATR周期（用于止损）
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # MACD指标
        self.macd = bt.indicators.MACD(
            self.datas[0],
            period_me1=self.params.fast,
            period_me2=self.params.slow,
            period_signal=self.params.signal
        )
        
        # MACD柱状图
        self.macd_hist = self.macd.macd - self.macd.signal
        
        # ATR用于止损
        self.atr = bt.indicators.ATR(self.datas[0], period=self.params.atr_period)
        
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
            
        # MACD金叉（快线从下穿上）
        if self.macd.lines.macd[-1] < self.macd.lines.signal[-1] and \
           self.macd.lines.macd[0] > self.macd.lines.signal[0]:
            if not self.position:
                self.order = self.buy()
                
        # MACD死叉（快线从上穿下）
        elif self.macd.lines.macd[-1] > self.macd.lines.signal[-1] and \
             self.macd.lines.macd[0] < self.macd.lines.signal[0]:
            if self.position:
                self.order = self.close()
