"""
VWAP动态平衡策略
当价格低于VWAP时买入，高于时卖出，配合成交量确认
适合日内交易风格
"""
import backtrader as bt


class VWAPStrategy(bt.Strategy):
    params = (
        ("vwap_period", 14),
        ("volume_factor", 1.5),  # 成交量放大倍数确认
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datavol = self.datas[0].volume
        self.dataopen = self.datas[0].open

        # 手动计算VWAP
        self.order = None
        self.vwap_vals = []
        self.vwap_history = []

    def next(self):
        if len(self) < 2:
            # 简单VWAP：累计 (close * volume) / cumulative volume
            typical = (self.dataclose[0] + self.datahigh[0] + self.datalow[0]) / 3
            self.vwap_vals.append(typical * self.datavol[0])
            self.vwap_vals.append(self.datavol[0])
            return

        # 更新VWAP
        typical = (self.dataclose[0] + self.datalow[0] + self.datahigh[0]) / 3
        vol = self.datavol[0]

        if len(self.vwap_vals) >= 2:
            total_pv = self.vwap_vals[-2] + typical * vol
            total_vol = self.vwap_vals[-1] + vol
            self.vwap_vals[-2] = total_pv
            self.vwap_vals[-1] = total_vol
            vwap = total_pv / total_vol if total_vol > 0 else typical
        else:
            vwap = typical

        close = self.dataclose[0]

        # 成交量是否高于均量
        avg_vol = self.datavol[0] if len(self) < self.params.vwap_period else \
                  sum([self.datavol[-i] for i in range(1, self.params.vwap_period + 1)]) / self.params.vwap_period
        vol_confirm = vol > avg_vol * self.params.volume_factor

        # 买入：价格跌破VWAP + 成交量放大
        if close < vwap and vol_confirm and self.position.size == 0:
            self.order = self.buy()

        # 卖出：价格涨破VWAP + 成交量放大
        elif close > vwap and vol_confirm and self.position.size > 0:
            self.order = self.close()

    @property
    def datahigh(self):
        return self.datas[0].high

    @property
    def datalow(self):
        return self.datas[0].low
