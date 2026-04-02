"""
多因子策略
综合PE、PB、ROE、MACD多因子选股，结合动量择时
"""
import backtrader as bt


class MultiFactor(bt.Strategy):
    """多因子策略"""
    
    params = (
        ("pe_limit", 50),      # PE上限
        ("pb_limit", 5),       # PB上限
        ("roe_min", 5),        # ROE下限(%)
        ("mom_period", 60),    # 动量周期
        ("rsi_period", 14),    # RSI周期
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # 动量指标
        self.momentum = bt.indicators.Momentum(
            self.datas[0].close,
            period=self.params.mom_period
        )
        
        # RSI
        self.rsi = bt.indicators.RSI(
            self.datas[0].close,
            period=self.params.rsi_period
        )
        
        # 均线趋势
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0].close, period=20
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.datas[0].close, period=60
        )
        
        self.order = None
        self.factor_score = 0
        
    def calculate_factors(self):
        """计算多因子得分（简化版）"""
        close = self.dataclose[0]
        
        # 简化因子：
        # 1. 动量因子 (正动量=+1)
        mom_score = 1 if self.momentum[0] > 0 else -1
        
        # 2. RSI因子 (30-70区间)
        rsi_val = self.rsi[0]
        if 30 < rsi_val < 70:
            rsi_score = 0.5
        elif rsi_val <= 30:
            rsi_score = 1  # 超卖
        else:
            rsi_score = -1  # 超买
            
        # 3. 趋势因子
        trend_score = 1 if close > self.sma_fast[0] else -1
        
        return mom_score + rsi_score + trend_score
        
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
            
        # 计算综合因子得分
        self.factor_score = self.calculate_factors()
        
        # 综合得分大于0且无持仓，买入
        if self.factor_score >= 2 and not self.position:
            self.order = self.buy()
            
        # 综合得分小于0且有持仓，卖出
        elif self.factor_score <= -1 and self.position:
            self.order = self.close()
