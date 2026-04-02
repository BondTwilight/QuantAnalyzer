"""
DualThrust区间突破策略
经典日内区间突破策略，通过N日内最高价-收盘价和收盘价-N日内最低价的较大值构建上下轨
"""
import backtrader as bt


class DualThrust(bt.Strategy):
    """DualThrust区间突破策略"""
    
    params = (
        ("kup", 0.5),      # 上轨系数
        ("kdown", 0.5),    # 下轨系数
        ("period", 2),     # 周期
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        self.order = None
        
        # 周期内最高价、最低价、收盘价
        self.highest_high = None
        self.lowest_low = None
        self.prev_close = None
        
    def next(self):
        if self.order:
            return
            
        # 需要至少period+1根K线
        if len(self) <= self.params.period:
            return
            
        # 获取周期内数据
        highs = self.datahigh.get(size=self.params.period + 1)
        lows = self.datalow.get(size=self.params.period + 1)
        closes = self.dataclose.get(size=self.params.period + 1)
        
        hh = max(highs[:-1])   # 周期内最高价
        ll = min(lows[:-1])   # 周期内最低价
        pc = closes[-2]       # 前一根收盘价
        
        # 计算上下轨
        range_val = max(hh - pc, pc - ll)
        upper = self.dataclose[0] + self.params.kup * range_val
        lower = self.dataclose[0] - self.params.kdown * range_val
        
        close = self.dataclose[0]
        
        # 价格向上突破上轨，买入
        if close > upper and not self.position:
            self.order = self.buy()
            
        # 价格向下突破下轨，卖出
        elif close < lower and self.position:
            self.order = self.close()
