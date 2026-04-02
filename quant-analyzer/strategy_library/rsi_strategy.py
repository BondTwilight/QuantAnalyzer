"""
RSI超买超卖策略
RSI低于30超卖买入，高于70超买卖出
"""
import backtrader as bt


class RSIStrategy(bt.Strategy):
    """RSI超买超卖策略"""
    
    params = (
        ("period", 14),      # RSI周期
        ("lower", 30),       # 超卖阈值
        ("upper", 70),       # 超买阈值
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # RSI指标
        self.rsi = bt.indicators.RSI(
            self.datas[0].close,
            period=self.params.period
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
            
        rsi_val = self.rsi[0]
        
        # RSI低于超卖阈值且无持仓，买入
        if rsi_val < self.params.lower and not self.position:
            self.order = self.buy()
            
        # RSI高于超买阈值且有持仓，卖出
        elif rsi_val > self.params.upper and self.position:
            self.order = self.close()
