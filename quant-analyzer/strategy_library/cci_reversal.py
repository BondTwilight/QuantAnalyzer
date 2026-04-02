"""
CCI超买超卖反转策略
使用CCI商品通道指标，CCI<-100超卖买入，CCI>+100超买卖出
适用于震荡市场
"""
import backtrader as bt


class CCIReversal(bt.Strategy):
    params = (
        ("period", 14),
        ("buy_threshold", -100),
        ("sell_threshold", 100),
        ("exit_after_bars", 10),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # CCI指标
        self.cci = bt.indicators.CommodityChannelIndex(
            self.datas[0], period=self.params.period
        )

        self.order = None
        self.bars_held = 0

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        self.order = None

    def next(self):
        if self.order:
            return

        if self.position.size > 0:
            self.bars_held += 1

        cci_val = self.cci[0]

        # 买入：CCI低于-100超卖
        if cci_val < self.params.buy_threshold and self.position.size == 0:
            self.order = self.buy()
            self.bars_held = 0

        # 卖出：CCI高于+100超买 或 持仓超过N天
        elif ((cci_val > self.params.sell_threshold) or
              (self.position.size > 0 and self.bars_held >= self.params.exit_after_bars)):
            self.order = self.close()
