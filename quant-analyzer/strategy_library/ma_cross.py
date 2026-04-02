"""
均线金叉死叉策略
最简单的趋势策略：短期均线上穿长期均线买入，下穿卖出
"""
import backtrader as bt


class MACross(bt.Strategy):
    """均线金叉死叉策略"""
    
    params = (
        ("fast", 5),      # 快速均线周期
        ("slow", 20),     # 慢速均线周期
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # 均线指标
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.fast
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.slow
        )
        
        # 金叉死叉信号
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        self.order = None
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入, 价格: {order.executed.price:.2f}')
            else:
                self.log(f'卖出, 价格: {order.executed.price:.2f}')
        self.order = None
        
    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        # print(f'{dt.isoformat()} {txt}')
        
    def next(self):
        if self.order:
            return
            
        # 金叉买入
        if self.crossover > 0:
            self.log(f'信号: 买入 (金叉) | 现价: {self.dataclose[0]:.2f}')
            self.order = self.buy()
            
        # 死叉卖出
        elif self.crossover < 0:
            if self.position:
                self.log(f'信号: 卖出 (死叉) | 现价: {self.dataclose[0]:.2f}')
                self.order = self.close()
