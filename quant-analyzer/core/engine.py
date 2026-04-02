"""
回测引擎 — Backtrader 封装
"""
import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import INITIAL_CASH, COMMISSION, SLIPPAGE
from core.metrics import calculate_all_metrics

logger = logging.getLogger(__name__)


class PortfolioTracker(bt.Analyzer):
    """跟踪每日组合净值"""
    def __init__(self):
        self.daily_values = []
        self.daily_dates = []

    def next(self):
        self.daily_dates.append(self.data.datetime.date(0))
        self.daily_values.append(self.strategy.broker.getvalue())


class BacktestEngine:
    """Backtrader 回测引擎"""

    def __init__(self, initial_cash=INITIAL_CASH):
        self.initial_cash = initial_cash
        self.cerebro = None

    def run(self, strategy_class, data_feed: pd.DataFrame, benchmark_feed: pd.DataFrame = None, **kwargs):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(self.initial_cash)
        self.cerebro.broker.setcommission(commission=COMMISSION)
        self.cerebro.broker.set_slippage_perc(perc=SLIPPAGE)

        # 确保数据有所有必需列且为float
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in data_feed.columns:
                data_feed[col] = data_feed.get("close", 0)
            data_feed[col] = pd.to_numeric(data_feed[col], errors="coerce").fillna(0)

        bt_data = bt.feeds.PandasData(
            dataname=data_feed.copy(),
            datetime=None,
            open="open", high="high", low="low", close="close", volume="volume",
            openinterest=-1,
        )
        self.cerebro.adddata(bt_data)

        # 不把 benchmark 作为 feed（避免指标冲突），只在提取结果时使用
        self.cerebro.addstrategy(strategy_class, **kwargs)
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        self.cerebro.addanalyzer(PortfolioTracker, _name="portfolio")

        results = self.cerebro.run(runonce=False)  # 用step-by-step模式避免numpy兼容问题
        strat = results[0]

        return self._extract_results(strat, data_feed, benchmark_feed)

    def _extract_results(self, strat, data_feed, benchmark_feed):
        portfolio_tracker = strat.analyzers.portfolio
        dates = portfolio_tracker.daily_dates
        portfolio_values = portfolio_tracker.daily_values

        # 基准净值曲线
        benchmark_values = []
        if benchmark_feed is not None and not benchmark_feed.empty:
            first_price = benchmark_feed["close"].iloc[0]
            if first_price > 0:
                for price in benchmark_feed["close"]:
                    benchmark_values.append(price / first_price * self.initial_cash)

        portfolio_series = pd.Series(portfolio_values, index=pd.to_datetime(dates))
        rolling_max = portfolio_series.expanding().max()
        drawdown_series = (portfolio_series - rolling_max) / rolling_max

        daily_df = pd.DataFrame({
            "portfolio_value": portfolio_values,
            "drawdown": drawdown_series.values,
        }, index=pd.to_datetime(dates))

        if benchmark_values and len(benchmark_values) >= len(dates):
            daily_df["benchmark_value"] = benchmark_values[:len(dates)]
        else:
            daily_df["benchmark_value"] = np.nan

        # 计算日收益率和指标
        returns = portfolio_series.pct_change().dropna().values
        bench_returns = None
        if benchmark_values and len(benchmark_values) > 1:
            bench_series = pd.Series(benchmark_values[:len(returns)])
            bench_returns = bench_series.pct_change().dropna().values[:len(returns)]

        metrics = calculate_all_metrics(returns, bench_returns, risk_free_rate=0.03)

        # 交易统计
        trades = []
        try:
            ta = strat.analyzers.trades.get("analysis")
            if ta:
                total_trades = ta.get("total", {}).get("total", 0)
                won = ta.get("won", {}).get("total", 0)
                win_rate = won / total_trades if total_trades > 0 else 0
                avg_win = ta.get("won", {}).get("pnl", {}).get("average", 0) if ta.get("won") else 0
                avg_loss = abs(ta.get("lost", {}).get("pnl", {}).get("average", 0)) if ta.get("lost") else 1
                profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
            else:
                total_trades = 0
                win_rate = 0
                profit_loss_ratio = 0
        except:
            total_trades = 0
            win_rate = 0
            profit_loss_ratio = 0

        final_value = strat.broker.getvalue()
        total_return = (final_value - self.initial_cash) / self.initial_cash
        trading_days = len(dates)
        annual_return = metrics.get("annual_return", total_return * 252 / max(trading_days, 1))

        result = {
            "strategy_name": getattr(strat, "strategy_name", "unknown"),
            "start_date": dates[0].strftime("%Y-%m-%d") if dates else "",
            "end_date": dates[-1].strftime("%Y-%m-%d") if dates else "",
            "initial_cash": self.initial_cash,
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 4),
            "annual_return": round(annual_return, 4),
            "max_drawdown": round(abs(metrics.get("max_drawdown", 0)), 4),
            "sharpe_ratio": round(metrics.get("sharpe_ratio", 0), 4),
            "sortino_ratio": round(metrics.get("sortino_ratio", 0), 4) if metrics.get("sortino_ratio", 0) != 0 else None,
            "calmar_ratio": round(metrics.get("calmar_ratio", 0), 4) if metrics.get("calmar_ratio", 0) != 0 else None,
            "win_rate": round(win_rate, 4),
            "profit_loss_ratio": round(profit_loss_ratio, 4),
            "total_trades": total_trades,
            "trade_frequency": round(total_trades / (trading_days / 252), 2) if trading_days >= 252 else total_trades,
            "beta": round(metrics.get("beta", 0), 4) if metrics.get("beta") else None,
            "volatility": round(metrics.get("volatility", 0), 4),
            "daily_values": daily_df,
            "trades": trades,
        }

        return result
