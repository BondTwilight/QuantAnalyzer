"""
量化指标计算模块
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_all_metrics(returns: np.ndarray, benchmark_returns: np.ndarray = None,
                          risk_free_rate: float = 0.03) -> Dict:
    """
    计算所有量化指标

    Args:
        returns: 日收益率序列
        benchmark_returns: 基准日收益率序列 (可选)
        risk_free_rate: 无风险年化利率 (默认3%)

    Returns:
        指标字典
    """
    if len(returns) == 0:
        return {}

    rf_daily = risk_free_rate / 252
    annual_factor = 252

    result = {}

    # ── 收益指标 ──
    result["total_return"] = np.prod(1 + returns) - 1
    result["annual_return"] = (1 + result["total_return"]) ** (annual_factor / len(returns)) - 1

    # ── 风险指标 ──
    result["volatility"] = np.std(returns) * np.sqrt(annual_factor)
    result["downside_volatility"] = _downside_deviation(returns, rf_daily) * np.sqrt(annual_factor)
    result["max_drawdown"] = _max_drawdown(returns)

    # ── 风险调整收益 ──
    excess_returns = returns - rf_daily
    result["sharpe_ratio"] = np.mean(excess_returns) / np.std(returns) * np.sqrt(annual_factor) if np.std(returns) > 0 else 0

    downside = returns[returns < rf_daily]
    result["sortino_ratio"] = np.mean(excess_returns) / np.std(downside) * np.sqrt(annual_factor) if len(downside) > 0 and np.std(downside) > 0 else 0

    result["calmar_ratio"] = result["annual_return"] / abs(result["max_drawdown"]) if result["max_drawdown"] != 0 else 0

    # ── 交易统计 ──
    result["win_rate"] = np.sum(returns > 0) / len(returns)
    result["avg_win"] = np.mean(returns[returns > 0]) if np.sum(returns > 0) > 0 else 0
    result["avg_loss"] = abs(np.mean(returns[returns < 0])) if np.sum(returns < 0) > 0 else 1
    result["profit_loss_ratio"] = result["avg_win"] / result["avg_loss"] if result["avg_loss"] > 0 else 0

    # ── 偏度和峰度 ──
    result["skewness"] = float(pd.Series(returns).skew())
    result["kurtosis"] = float(pd.Series(returns).kurtosis())

    # ── VaR ──
    result["var_95"] = float(np.percentile(returns, 5))
    result["cvar_95"] = float(np.mean(returns[returns <= np.percentile(returns, 5)]))

    # ── 基准相关 ──
    if benchmark_returns is not None and len(benchmark_returns) == len(returns):
        excess = returns - benchmark_returns
        result["alpha"] = np.mean(excess) * annual_factor
        result["beta"] = np.cov(returns, benchmark_returns)[0, 1] / np.var(benchmark_returns) if np.var(benchmark_returns) > 0 else 0
        result["info_ratio"] = np.mean(excess) / np.std(excess) * np.sqrt(annual_factor) if np.std(excess) > 0 else 0
        result["tracking_error"] = np.std(excess) * np.sqrt(annual_factor)
        result["correlation"] = np.corrcoef(returns, benchmark_returns)[0, 1]

    return result


def _max_drawdown(returns: np.ndarray) -> float:
    """计算最大回撤"""
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    return float(np.min(drawdowns))


def _downside_deviation(returns: np.ndarray, rf: float) -> float:
    """计算下行偏差"""
    downside = np.minimum(returns - rf, 0)
    return np.sqrt(np.mean(downside ** 2))


def compute_strategy_score(metrics: Dict) -> Dict:
    """
    综合评分 — 将所有指标归一化为 0-100 分
    """
    score = {}

    # 年化收益评分 (0-30分)
    ar = metrics.get("annual_return", 0)
    score["return_score"] = min(30, max(0, ar * 100 * 2))  # 15%年化 = 30分满分

    # 最大回撤评分 (0-20分)
    mdd = abs(metrics.get("max_drawdown", 0))
    score["drawdown_score"] = max(0, 20 - mdd * 100)  # 回撤20% = 0分

    # 夏普比率评分 (0-20分)
    sr = metrics.get("sharpe_ratio", 0)
    score["sharpe_score"] = min(20, max(0, sr * 10))  # 夏普2.0 = 20分

    # 胜率评分 (0-15分)
    wr = metrics.get("win_rate", 0)
    score["win_rate_score"] = wr * 15

    # 盈亏比评分 (0-15分)
    plr = metrics.get("profit_loss_ratio", 0)
    score["pl_ratio_score"] = min(15, max(0, plr * 5))

    # 总分
    score["total_score"] = sum(score.values())

    # 评级
    total = score["total_score"]
    if total >= 80:
        score["rating"] = "A+"
    elif total >= 70:
        score["rating"] = "A"
    elif total >= 60:
        score["rating"] = "B+"
    elif total >= 50:
        score["rating"] = "B"
    elif total >= 40:
        score["rating"] = "C"
    else:
        score["rating"] = "D"

    return score


def compare_strategies(results: list) -> pd.DataFrame:
    """
    策略对比 — 输入多个策略的结果，生成对比表
    """
    rows = []
    for r in results:
        metrics = {
            "策略名称": r.get("strategy_name", "unknown"),
            "年化收益": f"{r.get('annual_return', 0):.2%}",
            "最大回撤": f"{abs(r.get('max_drawdown', 0)):.2%}",
            "夏普比率": f"{r.get('sharpe_ratio', 0):.2f}",
            "Sortino": f"{r.get('sortino_ratio', 0) or '-':.2f}" if r.get("sortino_ratio") else "-",
            "Calmar": f"{r.get('calmar_ratio', 0) or '-':.2f}" if r.get("calmar_ratio") else "-",
            "胜率": f"{r.get('win_rate', 0):.2%}",
            "盈亏比": f"{r.get('profit_loss_ratio', 0):.2f}",
            "交易次数": r.get("total_trades", 0),
            "Beta": f"{r.get('beta', 0) or '-':.2f}" if r.get("beta") else "-",
            "波动率": f"{r.get('volatility', 0):.2%}",
        }
        rows.append(metrics)
    return pd.DataFrame(rows)
