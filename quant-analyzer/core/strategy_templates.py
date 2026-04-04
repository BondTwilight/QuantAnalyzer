"""
📋 策略代码模板库 — 经过验证的可回测策略

提供标准化的策略模板，确保生成的代码能够正确回测
"""

# ═══════════════════════════════════════════════
# 基础策略模板
# ═══════════════════════════════════════════════

SMA_CROSS_TEMPLATE = '''
import backtrader as bt

class SmaCrossStrategy(bt.Strategy):
    """双均线金叉死叉策略"""
    params = (
        ('fast', 5),
        ('slow', 20),
        ('stop_loss', 0.05),
    )
    
    def __init__(self):
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.p.fast)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.p.slow)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
        else:
            if self.crossover < 0:
                self.order = self.sell()
            elif self.data.close[0] < self.position.price * (1 - self.p.stop_loss):
                self.order = self.sell()
                
    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None
'''

MACD_TEMPLATE = '''
import backtrader as bt

class MacdStrategy(bt.Strategy):
    """MACD策略"""
    params = (
        ('fast', 12),
        ('slow', 26),
        ('signal', 9),
        ('stop_loss', 0.05),
    )
    
    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.fast,
            period_me2=self.p.slow,
            period_signal=self.p.signal
        )
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]:
                self.order = self.buy()
        else:
            if self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] >= self.macd.signal[-1]:
                self.order = self.sell()
            elif self.data.close[0] < self.position.price * (1 - self.p.stop_loss):
                self.order = self.sell()
                
    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None
'''

RSI_TEMPLATE = '''
import backtrader as bt

class RsiStrategy(bt.Strategy):
    """RSI超买超卖策略"""
    params = (
        ('period', 14),
        ('upper', 70),
        ('lower', 30),
        ('stop_loss', 0.05),
    )
    
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.period)
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.rsi[0] < self.p.lower:
                self.order = self.buy()
        else:
            if self.rsi[0] > self.p.upper:
                self.order = self.sell()
            elif self.data.close[0] < self.position.price * (1 - self.p.stop_loss):
                self.order = self.sell()
                
    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None
'''

BOLLINGER_TEMPLATE = '''
import backtrader as bt

class BollingerStrategy(bt.Strategy):
    """布林带策略"""
    params = (
        ('period', 20),
        ('devfactor', 2),
        ('stop_loss', 0.05),
    )
    
    def __init__(self):
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.p.period,
            devfactor=self.p.devfactor
        )
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.data.close[0] < self.boll.lines.bot[0]:
                self.order = self.buy()
        else:
            if self.data.close[0] > self.boll.lines.top[0]:
                self.order = self.sell()
            elif self.data.close[0] < self.position.price * (1 - self.p.stop_loss):
                self.order = self.sell()
                
    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None
'''

MOMENTUM_TEMPLATE = '''
import backtrader as bt

class MomentumStrategy(bt.Strategy):
    """动量策略"""
    params = (
        ('period', 20),
        ('threshold', 0.05),
        ('stop_loss', 0.05),
    )
    
    def __init__(self):
        self.roc = bt.indicators.RateOfChange(self.data.close, period=self.p.period)
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.roc[0] > self.p.threshold:
                self.order = self.buy()
        else:
            if self.roc[0] < -self.p.threshold:
                self.order = self.sell()
            elif self.data.close[0] < self.position.price * (1 - self.p.stop_loss):
                self.order = self.sell()
                
    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None
'''

COMBINED_TEMPLATE = '''
import backtrader as bt

class CombinedStrategy(bt.Strategy):
    """多因子组合策略"""
    params = (
        ('rsi_period', 14),
        ('rsi_lower', 30),
        ('rsi_upper', 70),
        ('ma_fast', 5),
        ('ma_slow', 20),
        ('stop_loss', 0.05),
    )
    
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.p.ma_fast)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.p.ma_slow)
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            # RSI超卖 + 短期均线上穿长期均线
            if self.rsi[0] < self.p.rsi_lower and self.fast_ma[0] > self.slow_ma[0]:
                self.order = self.buy()
        else:
            # RSI超买
            if self.rsi[0] > self.p.rsi_upper:
                self.order = self.sell()
            elif self.data.close[0] < self.position.price * (1 - self.p.stop_loss):
                self.order = self.sell()
                
    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None
'''

# 模板映射
STRATEGY_TEMPLATES = {
    "sma_cross": SMA_CROSS_TEMPLATE,
    "macd": MACD_TEMPLATE,
    "rsi": RSI_TEMPLATE,
    "bollinger": BOLLINGER_TEMPLATE,
    "momentum": MOMENTUM_TEMPLATE,
    "combined": COMBINED_TEMPLATE,
}

def get_template(name: str) -> str:
    """获取策略模板"""
    return STRATEGY_TEMPLATES.get(name, SMA_CROSS_TEMPLATE)

def get_all_templates() -> dict:
    """获取所有模板"""
    return STRATEGY_TEMPLATES.copy()

def generate_strategy_code(strategy_type: str, **params) -> str:
    """根据类型和参数生成策略代码"""
    template = get_template(strategy_type)
    
    # 替换参数
    for key, value in params.items():
        template = template.replace(f'self.p.{key}', str(value))
    
    return template
