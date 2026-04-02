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
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import INITIAL_CASH, COMMISSION, STAMP_TAX, SLIPPAGE
from core.metrics import calculate_all_metrics

logger = logging.getLogger(__name__)


class BenchmarkData(bt.feeds.PandasData):
    """基准数据 Feed"""
    params = (
        ("datetime", None),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "volume"),
        ("openinterest", -1),
    )


class BacktestEngine:
    """Backtrader 回测引擎"""

    def __init__(self, initial_cash=INITIAL_CASH):
        self.initial_cash = initial_cash
        self.cerebro = None

    def run(self, strategy_class, data_feed: pd.DataFrame, benchmark_feed: pd.DataFrame = None, **kwargs):
        """
        运行回测
        strategy_class: Backtrader策略类
        data_feed: 股票日线数据 (DataFrame, index=日期, columns=open/close/high/low/volume)
        benchmark_feed: 基准数据 (可选)
        kwargs: 策略参数
        """
        self.cerebro = bt.Cerebro()

        # 设置初始资金
        self.cerebro.broker.setcash(self.initial_cash)

        # 设置佣金
        self.cerebro.broker.setcommission(
            commission=COMMISSION,
            stock=True,
            stamp_duty=STAMP_TAX,
        )

        # 设置滑点
        self.cerebro.broker.set_slippage_perc(slippage=SLIPPAGE)

        # 添加数据
        bt_data = bt.feeds.PandasData(
            dataname=data_feed.copy(),
            datetime=None,
            open="open", high="high", low="low", close="close", volume="volume",
            openinterest=-1,
        )
        self.cerebro.adddata(bt_data)

        # 添加基准
        if benchmark_feed is not None and not benchmark_feed.empty:
            bt_bench = BenchmarkData(dataname=benchmark_feed.copy())
            self.cerebro.adddata(bt_bench, name="benchmark")

        # 添加策略
        self.cerebro.addstrategy(strategy_class, **kwargs)

        # 添加分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        self.cerebro.addanalyzer(bt.analyzers.Variance, _name="variance")
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        self.cerebro.addanalyzer(bt.analyzers.PyFolio, _name="pyfolio")

        # 运行
        results = self.cerebro.run()
        strat = results[0]

        # 提取结果
        return self._extract_results(strat, data_feed, benchmark_feed)

    def _extract_results(self, strat, data_feed, benchmark_feed):
        """从回测结果中提取所有指标"""
        # 净值曲线
        portfolio_values = []
        dates = []
        for i, dt in enumerate(data_feed.index):
            if i < len(strat.analyzers.pyfolio.get("returns")):
                dates.append(dt)
                portfolio_values.append(strat.broker.getvalue())

        # 基准净值曲线
        benchmark_values = []
        if benchmark_feed is not None and not benchmark_feed.empty:
            first_price = benchmark_feed["close"].iloc[0]
            for price in benchmark_feed["close"]:
                benchmark_values.append(price / first_price * self.initial_cash)

        # 最大回撤序列
        portfolio_series = pd.Series(portfolio_values, index=dates[:len(portfolio_values)])
        rolling_max = portfolio_series.expanding().max()
        drawdown_series = (portfolio_series - rolling_max) / rolling_max

        # 回撤数据对齐
        dd_aligned = drawdown_series.reindex(dates[:len(portfolio_values)])

        # 构建每日净值 DataFrame
        daily_df = pd.DataFrame({
            "portfolio_value": portfolio_values[:len(dates)],
            "drawdown": dd_aligned.values[:len(dates)] if len(dd_aligned) >= len(dates) else [0] * len(dates),
        }, index=dates[:len(portfolio_values)])

        if benchmark_values and len(benchmark_values) >= len(dates):
            daily_df["benchmark_value"] = benchmark_values[:len(dates)]
        else:
            daily_df["benchmark_value"] = np.nan

        # 交易记录
        trades = []
        for trade in strat.analyzers.trades.get("trades") or []:
            for entry, exit_ in zip(trade.get("entry", []), trade.get("exit", [])):
                trades.append({
                    "date": exit_.get("dt", "").strftime("%Y-%m-%d") if hasattr(exit_.get("dt", ""), "strftime") else str(exit_.get("dt", "")),
                    "action": "BUY" if trade.get("pnl", 0) >= 0 else "SELL",
                    "price": exit_.get("price", 0),
                    "pnl": trade.get("pnl", 0),
                    "pnl_pct": trade.get("pnl", 0) / (trade.get("pnl", 0) - exit_.get("price", 0) * trade.get("size", 0)) if trade.get("size", 0) else 0,
                    "reason": f"持有{strat.params._getpairs() if hasattr(strat.params, '_getpairs') else ''}天",
                })

        # 提取分析器数据
        try:
            sharpe = strat.analyzers.sharpe.get("sharperatio")
        except:
            sharpe = None

        try:
            max_dd = strat.analyzers.drawdown.get("max").get("drawdown", 0) / 100
        except:
            max_dd = 0

        try:
            ta = strat.analyzers.trades.get("analysis")
            total_trades = ta.get("total", {}).get("total", 0) if ta else 0
            won = ta.get("won", {}).get("total", 0) if ta else 0
            lost = ta.get("lost", {}).get("total", 0) if ta else 0
            win_rate = won / total_trades if total_trades > 0 else 0

            # 盈亏比
            avg_win = ta.get("won", {}).get("pnl", {}).get("average", 0) if ta and ta.get("won") else 0
            avg_loss = abs(ta.get("lost", {}).get("pnl", {}).get("average", 0)) if ta and ta.get("lost") else 1
            profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        except:
            total_trades = 0
            won = 0
            win_rate = 0
            profit_loss_ratio = 0

        try:
            annual_return = strat.analyzers.returns.get("rnorm100", 0) / 100
        except:
            annual_return = 0

        try:
            var = strat.analyzers.variance.get("vartarget", 0)
            volatility = np.sqrt(var) if var > 0 else 0
        except:
            volatility = 0

        final_value = strat.broker.getvalue()
        total_return = (final_value - self.initial_cash) / self.initial_cash

        # 用 empyrical 精确计算
        try:
            returns = portfolio_series.pct_change().dropna().values
            from empyrical import sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio, beta as calc_beta
            import empyrical as ep

            if len(returns) > 0:
                sharpe = sharpe_ratio(returns, risk_free=0.02/252, annualization=252)
                try:
                    sortino = sortino_ratio(returns, risk_free=0.02/252, annualization=252)
                except:
                    sortino = None
                max_dd = max_drawdown(returns)
                if max_dd != 0:
                    calmar = calmar_ratio(returns, risk_free=0.02/252, annualization=252)
                else:
                    calmar = None
                if benchmark_values and len(benchmark_values) >= len(returns):
                    bench_returns = pd.Series(benchmark_values[:len(returns)]).pct_change().dropna().values
                    if len(bench_returns) == len(returns):
                        beta_val = calc_beta(returns, bench_returns)
                    else:
                        beta_val = None
                else:
                    beta_val = None
            else:
                sortino = None
                calmar = None
                beta_val = None
        except ImportError:
            sortino = None
            calmar = None
            beta_val = None

        # Beta 计算
        if beta_val is None and benchmark_values:
            try:
                port_returns = portfolio_series.pct_change().dropna()
                bench_series = pd.Series(benchmark_values[:len(port_returns)], index=port_returns.index)
                bench_returns = bench_series.pct_change().dropna()
                common_idx = port_returns.index.intersection(bench_returns.index)
                if len(common_idx) > 10:
                    cov_matrix = np.cov(port_returns[common_idx], bench_returns[common_idx])
                    beta_val = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else None
                else:
                    beta_val = None
            except:
                beta_val = None

        # 交易天数
        trading_days = len(dates)
        if trading_days > 0:
            trade_freq = total_trades / (trading_days / 252) if trading_days >= 252 else total_trades
        else:
            trade_freq = 0

        result = {
            "strategy_name": getattr(strat, "strategy_name", "unknown"),
            "start_date": dates[0].strftime("%Y-%m-%d") if dates else "",
            "end_date": dates[-1].strftime("%Y-%m-%d") if dates else "",
            "initial_cash": self.initial_cash,
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 4),
            "annual_return": round(annual_return, 4) if annual_return else round(total_return * 252 / max(trading_days, 1), 4),
            "max_drawdown": round(abs(max_dd), 4) if max_dd else 0,
            "sharpe_ratio": round(sharpe, 4) if sharpe else 0,
            "sortino_ratio": round(sortino, 4) if sortino else None,
            "calmar_ratio": round(calmar, 4) if calmar else None,
            "win_rate": round(win_rate, 4),
            "profit_loss_ratio": round(profit_loss_ratio, 4),
            "total_trades": total_trades,
            "trade_frequency": round(trade_freq, 2),
            "beta": round(beta_val, 4) if beta_val else None,
            "volatility": round(volatility, 4) if volatility else round(np.std(portfolio_series.pct_change().dropna()) * np.sqrt(252), 4) if len(portfolio_series) > 1 else 0,
            "daily_values": daily_df,
            "trades": trades,
        }

        return result
