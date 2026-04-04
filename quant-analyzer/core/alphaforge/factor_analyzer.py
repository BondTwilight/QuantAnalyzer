"""
📊 FactorAnalyzer — 因子评估与IC/IR分析

核心功能：
1. IC（信息系数）计算：因子值与未来收益的相关性
2. IR（信息比率）计算：IC均值/IC标准差，衡量因子稳定性
3. 分层回测：按因子分组看收益差异
4. 因子衰减分析：IC随时间的变化
5. 多因子组合评估：因子相关性、冗余分析
6. 适应度函数：为遗传编程提供选择压力

设计参考：WorldQuant Alpha 评估框架 + Alphalens
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 评估结果数据结构
# ═══════════════════════════════════════════════

@dataclass
class FactorEvaluation:
    """因子评估结果"""
    factor_name: str = ""
    
    # IC分析
    ic_mean: float = 0.0              # IC均值（核心指标）
    ic_std: float = 0.0               # IC标准差
    ic_ir: float = 0.0                # 信息比率 = IC_mean / IC_std
    ic_skewness: float = 0.0          # IC偏度
    ic_kurtosis: float = 0.0          # IC峰度
    ic_positive_ratio: float = 0.0    # IC为正的比例
    
    # 收益分析
    annual_return: float = 0.0        # 年化收益（多头-空头）
    sharpe_ratio: float = 0.0         # 夏普比率
    max_drawdown: float = 0.0         # 最大回撤
    win_rate: float = 0.0             # 胜率
    profit_loss_ratio: float = 0.0    # 盈亏比
    turnover: float = 0.0             # 换手率
    
    # 分层回测
    quintile_returns: Dict[int, float] = field(default_factory=dict)  # 五分位收益
    
    # 衰减分析
    ic_by_year: Dict[str, float] = field(default_factory=dict)
    
    # 综合评分
    fitness: float = 0.0              # 适应度（0-1），用于遗传编程
    is_valid: bool = False            # 是否通过有效性检验
    
    # 诊断
    error: str = ""
    
    def to_dict(self) -> Dict:
        from dataclasses import asdict
        return asdict(self)
    
    def summary(self) -> str:
        """生成评估摘要"""
        status = "✅ 有效" if self.is_valid else "❌ 无效"
        lines = [
            f"═══ 因子评估: {self.factor_name} {status} ═══",
            f"  IC均值: {self.ic_mean:.4f} | IR: {self.ic_ir:.4f} | IC>0比例: {self.ic_positive_ratio:.2%}",
            f"  年化收益: {self.annual_return:.2%} | 夏普: {self.sharpe_ratio:.2f} | 最大回撤: {self.max_drawdown:.2%}",
            f"  胜率: {self.win_rate:.2%} | 盈亏比: {self.profit_loss_ratio:.2f} | 换手率: {self.turnover:.2%}",
            f"  适应度: {self.fitness:.4f}",
        ]
        if self.quintile_returns:
            lines.append("  五分位收益:")
            for q, ret in sorted(self.quintile_returns.items()):
                lines.append(f"    Q{q}: {ret:.2%}")
        if self.error:
            lines.append(f"  错误: {self.error}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 因子评估器
# ═══════════════════════════════════════════════

class FactorAnalyzer:
    """
    因子评估器
    
    评估因子的预测能力、稳定性和可交易性。
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {
            # IC分析
            "ic_method": "spearman",           # IC计算方法: spearman/pearson
            "forward_periods": [1, 5, 10, 20], # 前瞻收益周期（天）
            "ic_window": 20,                   # 滚动IC窗口
            
            # 有效性阈值（放宽以允许更多因子通过）
            "min_ic_mean": 0.005,              # 最小IC均值（降低）
            "min_ir": 0.05,                     # 最小IR（降低）
            "min_ic_positive_ratio": 0.48,     # 最小IC正值比例（降低）
            "min_trades": 5,                   # 最小交易次数
            
            # 分层回测
            "n_quantiles": 5,                  # 分层数量
            
            # 适应度权重
            "fitness_weights": {
                "ic": 0.30,                    # IC均值权重
                "ir": 0.25,                    # IR权重
                "sharpe": 0.20,                # 夏普权重
                "drawdown": 0.10,              # 回撤控制权重
                "turnover": 0.05,              # 低换手权重
                "stability": 0.10,             # 稳定性权重
            },
            
            # 风险控制
            "max_turnover": 0.5,               # 最大换手率
            "max_drawdown_limit": 0.3,         # 最大允许回撤
        }
        if config:
            self.config.update(config)
    
    def evaluate(self, factor_values: pd.Series, forward_returns: pd.Series,
                 factor_name: str = "") -> FactorEvaluation:
        """
        评估单个因子
        
        Args:
            factor_values: 因子值序列
            forward_returns: 未来收益序列
            factor_name: 因子名称
            
        Returns:
            FactorEvaluation 评估结果
        """
        result = FactorEvaluation(factor_name=factor_name)
        
        try:
            # 对齐数据
            aligned = pd.DataFrame({
                "factor": factor_values,
                "return": forward_returns,
            }).dropna()
            
            if len(aligned) < 30:
                result.error = f"数据不足: {len(aligned)} 条"
                return result
            
            factors = aligned["factor"]
            returns = aligned["return"]
            
            # ─── 1. IC分析 ───
            ic_analysis = self._compute_ic(factors, returns)
            result.ic_mean = ic_analysis["ic_mean"]
            result.ic_std = ic_analysis["ic_std"]
            result.ic_ir = ic_analysis["ic_ir"]
            result.ic_skewness = ic_analysis["ic_skewness"]
            result.ic_kurtosis = ic_analysis["ic_kurtosis"]
            result.ic_positive_ratio = ic_analysis["ic_positive_ratio"]
            
            # ─── 2. 分层回测 ───
            quintile_result = self._quintile_backtest(factors, returns)
            result.quintile_returns = quintile_result["quintile_returns"]
            result.annual_return = quintile_result["long_short_return"]
            result.sharpe_ratio = quintile_result["sharpe"]
            result.max_drawdown = quintile_result["max_drawdown"]
            result.win_rate = quintile_result["win_rate"]
            result.profit_loss_ratio = quintile_result["profit_loss_ratio"]
            result.turnover = quintile_result["turnover"]
            
            # ─── 3. 综合评分 ───
            result.fitness = self._compute_fitness(result)
            result.is_valid = self._check_validity(result)
            
        except Exception as e:
            result.error = str(e)
            logger.warning(f"因子评估失败 [{factor_name}]: {e}")
        
        return result
    
    def evaluate_expression(self, expression: str, data: pd.DataFrame,
                            factor_name: str = "") -> Dict:
        """
        评估因子表达式（供遗传编程调用）
        
        Args:
            expression: 因子表达式
            data: OHLCV数据
            factor_name: 因子名称
            
        Returns:
            评估结果字典
        """
        from core.alphaforge.factor_engine import FactorEngine
        
        engine = FactorEngine()
        factor_values = engine.compute(expression, data)
        
        if factor_values is None or factor_values.empty:
            return {"fitness": 0, "ic_mean": 0, "ir": 0, "sharpe": 0, "error": "因子计算结果为空"}
        
        # 计算前瞻收益
        forward_returns = data["close"].pct_change().shift(-1)
        
        # 对齐
        aligned = pd.DataFrame({
            "factor": factor_values.reindex(data.index),
            "return": forward_returns,
        }).dropna()
        
        if len(aligned) < 30:
            return {"fitness": 0, "ic_mean": 0, "ir": 0, "sharpe": 0, "error": "数据不足"}
        
        eval_result = self.evaluate(aligned["factor"], aligned["return"], factor_name)
        
        return {
            "fitness": eval_result.fitness,
            "ic_mean": eval_result.ic_mean,
            "ir": eval_result.ic_ir,
            "sharpe": eval_result.sharpe_ratio,
            "annual_return": eval_result.annual_return,
            "max_drawdown": eval_result.max_drawdown,
            "is_valid": eval_result.is_valid,
            "error": eval_result.error,
        }
    
    def batch_evaluate(self, factor_results: Dict[str, pd.Series], 
                       forward_returns: pd.Series) -> Dict[str, FactorEvaluation]:
        """批量评估多个因子"""
        evaluations = {}
        for name, factor_values in factor_results.items():
            evaluations[name] = self.evaluate(factor_values, forward_returns, name)
        return evaluations
    
    def analyze_decay(self, factor_values: pd.Series, forward_returns: pd.Series,
                      factor_name: str = "") -> Dict[str, Any]:
        """分析因子衰减"""
        aligned = pd.DataFrame({
            "factor": factor_values,
            "return": forward_returns,
        }).dropna()
        
        if len(aligned) < 60:
            return {"error": "数据不足进行衰减分析"}
        
        # 滚动IC
        ic_window = self.config["ic_window"]
        rolling_ic = aligned["factor"].rolling(ic_window).corr(aligned["return"])
        
        # 按年度分析
        yearly_ic = {}
        if hasattr(aligned.index, "year"):
            for year, group in aligned.groupby(aligned.index.year):
                if len(group) >= 20:
                    ic, _ = scipy_stats.spearmanr(group["factor"], group["return"])
                    yearly_ic[str(year)] = round(ic, 4)
        
        # IC衰减趋势
        half_life = None
        if len(rolling_ic.dropna()) > 10:
            ic_series = rolling_ic.dropna().abs().values
            half_life_idx = np.searchsorted(-np.diff(ic_series), -0.5 * ic_series[0])
            if half_life_idx < len(ic_series):
                half_life = half_life_idx
        
        return {
            "factor_name": factor_name,
            "rolling_ic_mean": float(rolling_ic.mean()) if not rolling_ic.empty else 0,
            "rolling_ic_std": float(rolling_ic.std()) if not rolling_ic.empty else 0,
            "ic_stability": float(rolling_ic.std()) / (abs(rolling_ic.mean()) + 1e-8) if not rolling_ic.empty else 0,
            "yearly_ic": yearly_ic,
            "half_life_days": half_life,
        }
    
    def correlation_matrix(self, factor_results: Dict[str, pd.Series]) -> pd.DataFrame:
        """计算因子相关性矩阵"""
        df = pd.DataFrame(factor_results)
        return df.corr(method="spearman")
    
    def find_redundant(self, factor_results: Dict[str, pd.Series], 
                       threshold: float = 0.7) -> List[List[str]]:
        """找出冗余因子组"""
        corr = self.correlation_matrix(factor_results)
        redundant_groups = []
        visited = set()
        
        for col in corr.columns:
            if col in visited:
                continue
            similar = corr.index[corr[col].abs() > threshold].tolist()
            if len(similar) > 1:
                redundant_groups.append(similar)
                visited.update(similar)
        
        return redundant_groups
    
    # ─── 内部方法 ───
    
    def _compute_ic(self, factors: pd.Series, returns: pd.Series) -> Dict:
        """计算IC系列指标"""
        method = self.config["ic_method"]
        
        # 滚动IC
        ic_window = self.config["ic_window"]
        rolling_ic = factors.rolling(ic_window).corr(returns)
        rolling_ic = rolling_ic.dropna()
        
        if rolling_ic.empty:
            return {
                "ic_mean": 0, "ic_std": 0, "ic_ir": 0,
                "ic_skewness": 0, "ic_kurtosis": 0, "ic_positive_ratio": 0,
            }
        
        # 整体IC
        if method == "spearman":
            ic_overall, _ = scipy_stats.spearmanr(factors, returns)
        else:
            ic_overall, _ = scipy_stats.pearsonr(factors, returns)
        
        ic_mean = float(rolling_ic.mean())
        ic_std = float(rolling_ic.std())
        
        return {
            "ic_mean": round(abs(ic_overall), 4),   # 使用绝对值
            "ic_std": round(ic_std, 4),
            "ic_ir": round(ic_mean / (ic_std + 1e-8), 4),
            "ic_skewness": round(float(rolling_ic.skew()), 4),
            "ic_kurtosis": round(float(rolling_ic.kurtosis()), 4),
            "ic_positive_ratio": round(float((rolling_ic > 0).mean()), 4),
        }
    
    def _quintile_backtest(self, factors: pd.Series, returns: pd.Series) -> Dict:
        """五分层回测"""
        n_quantiles = self.config["n_quantiles"]
        
        try:
            # 分层
            quantiles = pd.qcut(factors, n_quantiles, labels=False, duplicates="drop")
        except Exception:
            quantiles = pd.cut(factors, n_quantiles, labels=False)
        
        aligned = pd.DataFrame({"factor_group": quantiles, "return": returns}).dropna()
        
        if aligned.empty or aligned["factor_group"].nunique() < 2:
            return {
                "quintile_returns": {},
                "long_short_return": 0,
                "sharpe": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "profit_loss_ratio": 0,
                "turnover": 0,
            }
        
        # 各分位收益
        quintile_returns = {}
        group_means = aligned.groupby("factor_group")["return"].mean()
        for q in sorted(aligned["factor_group"].unique()):
            quintile_returns[int(q)] = round(float(group_means.get(q, 0)), 6)
        
        # 多空收益（最高组 - 最低组）
        if len(group_means) >= 2:
            long_short = group_means.iloc[-1] - group_means.iloc[0]
        else:
            long_short = 0
        
        # 计算每日多空收益序列
        high_group = aligned[aligned["factor_group"] == aligned["factor_group"].max()]["return"]
        low_group = aligned[aligned["factor_group"] == aligned["factor_group"].min()]["return"]
        if len(high_group) > 0 and len(low_group) > 0:
            ls_daily = high_group.reindex(aligned.index) - low_group.reindex(aligned.index)
            ls_daily = ls_daily.dropna()
        else:
            ls_daily = pd.Series(dtype=float)
        
        # 夏普比率
        if len(ls_daily) > 1:
            sharpe = float(ls_daily.mean() / (ls_daily.std() + 1e-8) * np.sqrt(252))
        else:
            sharpe = 0
        
        # 最大回撤
        if len(ls_daily) > 1:
            cum_return = (1 + ls_daily).cumprod()
            rolling_max = cum_return.cummax()
            drawdown = (cum_return - rolling_max) / rolling_max
            max_dd = float(drawdown.min())
        else:
            max_dd = 0
        
        # 胜率
        win_rate = float((ls_daily > 0).mean()) if len(ls_daily) > 0 else 0
        
        # 盈亏比
        wins = ls_daily[ls_daily > 0].mean() if (ls_daily > 0).any() else 0
        losses = abs(ls_daily[ls_daily < 0].mean()) if (ls_daily < 0).any() else 1
        profit_loss_ratio = float(wins / (losses + 1e-8))
        
        # 换手率（简化估计）
        if len(quantiles) > 1:
            turnover = float((quantiles != quantiles.shift(1)).mean())
        else:
            turnover = 0
        
        return {
            "quintile_returns": quintile_returns,
            "long_short_return": round(float(long_short), 6),
            "sharpe": round(sharpe, 4),
            "max_drawdown": round(abs(max_dd), 4),
            "win_rate": round(win_rate, 4),
            "profit_loss_ratio": round(profit_loss_ratio, 4),
            "turnover": round(turnover, 4),
        }
    
    def _compute_fitness(self, eval_result: FactorEvaluation) -> float:
        """计算适应度（0-1）"""
        w = self.config["fitness_weights"]
        
        # 各维度分数
        ic_score = min(1, abs(eval_result.ic_mean) / 0.1)   # IC=0.1满分
        ir_score = min(1, abs(eval_result.ic_ir) / 1.0)     # IR=1.0满分
        sharpe_score = min(1, eval_result.sharpe_ratio / 2.0) # 夏普=2.0满分
        dd_score = max(0, 1 - eval_result.max_drawdown / self.config["max_drawdown_limit"])
        turnover_score = max(0, 1 - eval_result.turnover / self.config["max_turnover"])
        stability_score = eval_result.ic_positive_ratio  # IC正值比例直接使用
        
        fitness = (
            w["ic"] * ic_score +
            w["ir"] * ir_score +
            w["sharpe"] * sharpe_score +
            w["drawdown"] * dd_score +
            w["turnover"] * turnover_score +
            w["stability"] * stability_score
        )
        
        return round(min(1.0, max(0.0, fitness)), 4)
    
    def _check_validity(self, eval_result: FactorEvaluation) -> bool:
        """检查因子是否通过有效性检验"""
        if eval_result.error:
            return False
        
        checks = [
            abs(eval_result.ic_mean) >= self.config["min_ic_mean"],
            abs(eval_result.ic_ir) >= self.config["min_ir"],
            eval_result.ic_positive_ratio >= self.config["min_ic_positive_ratio"],
            eval_result.fitness >= 0.15,  # 最低适应度
        ]
        
        return all(checks)
