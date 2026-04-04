"""
🎯 StrategyEnsemble — 多因子策略组合优化器

核心功能：
1. 因子加权融合（IC加权/等权/优化权重）
2. 信号生成（多因子共振/投票机制）
3. 风险控制（止损/仓位管理/回撤保护）
4. 策略回测验证
5. 实时信号输出

设计参考：WorldQuant组合优化 + Grinblatt-Kahneman行为金融学
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 策略信号
# ═══════════════════════════════════════════════

@dataclass
class TradingSignal:
    """交易信号"""
    date: str = ""
    stock_code: str = ""
    stock_name: str = ""
    direction: int = 0          # 1=买入, -1=卖出, 0=持有
    strength: float = 0.0       # 信号强度 (0-1)
    composite_score: float = 0.0 # 综合评分
    factors_contribution: Dict[str, float] = field(default_factory=dict)
    stop_loss: float = 0.0      # 止损价
    take_profit: float = 0.0    # 止盈价
    position_size: float = 0.0  # 建议仓位 (0-1)
    reason: str = ""            # 信号理由
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EnsembleResult:
    """组合策略结果"""
    strategy_name: str = ""
    weights: Dict[str, float] = field(default_factory=dict)
    
    # 回测指标
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profit_loss_ratio: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # 因子贡献
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    
    # 信号记录
    signals: List[Dict] = field(default_factory=list)
    
    # 综合评分
    composite_score: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def score(self) -> float:
        """综合评分 (0-100)"""
        ret_score = min(25, max(0, self.annual_return * 8))
        sharpe_score = min(25, max(0, self.sharpe_ratio * 10))
        dd_score = max(0, 20 - self.max_drawdown * 80)
        win_score = min(10, self.win_rate * 10)
        freq_score = 5 if 3 <= self.total_trades <= 500 else 2
        return round(min(100, max(0, ret_score + sharpe_score + dd_score + win_score + freq_score)), 1)


# ═══════════════════════════════════════════════
# 策略组合优化器
# ═══════════════════════════════════════════════

class StrategyEnsemble:
    """
    多因子策略组合优化器
    
    将多个有效因子组合成一个交易策略，
    通过权重优化最大化风险调整收益。
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {
            # 组合方法
            "method": "ic_weighted",           # ic_weighted / equal / optimized / voting
            
            # 信号生成
            "buy_threshold": 0.6,              # 买入阈值
            "sell_threshold": -0.3,            # 卖出阈值
            "min_agreement": 3,                # 最少同意因子数（投票法）
            
            # 风险控制
            "stop_loss_pct": 0.05,             # 默认止损5%
            "take_profit_pct": 0.15,           # 默认止盈15%
            "max_position_pct": 0.3,           # 单只最大仓位30%
            "max_drawdown_limit": 0.15,        # 最大回撤限制15%
            
            # 仓位管理
            "base_position": 0.2,              # 基础仓位20%
            "kelly_fraction": 0.5,             # Kelly公式半仓
            "volatility_adjust": True,         # 波动率调整仓位
            
            # 回测参数
            "initial_cash": 100000,
            "commission": 0.0003,
            "slippage": 0.001,
        }
        if config:
            self.config.update(config)
        
        self._factor_cache: Dict[str, pd.Series] = {}
    
    def build_ensemble(self, factor_results: Dict[str, pd.Series], 
                       factor_meta: Dict[str, Dict] = None,
                       data: pd.DataFrame = None) -> EnsembleResult:
        """
        构建组合策略
        
        Args:
            factor_results: 因子名 -> 因子值序列
            factor_meta: 因子元数据 (ic_mean, ir, sharpe等)
            data: 原始OHLCV数据（用于回测）
            
        Returns:
            EnsembleResult
        """
        if not factor_results:
            return EnsembleResult(strategy_name="empty", error="无因子数据")
        
        factor_names = list(factor_results.keys())
        
        # 1. 计算因子权重
        weights = self._compute_weights(factor_results, factor_meta)
        
        # 2. 生成组合信号
        composite_signal = self._generate_composite_signal(factor_results, weights)
        
        # 3. 回测验证
        result = EnsembleResult(
            strategy_name=f"Ensemble_{len(factor_names)}F_{datetime.now().strftime('%m%d%H%M')}",
            weights=weights,
        )
        
        if data is not None and not data.empty:
            self._backtest_ensemble(result, composite_signal, data, factor_results)
        
        result.composite_score = result.score()
        return result
    
    def generate_signals(self, factor_results: Dict[str, pd.Series],
                         factor_meta: Dict[str, Dict] = None,
                         data: pd.DataFrame = None) -> List[TradingSignal]:
        """
        生成实时交易信号
        
        Args:
            factor_results: 各因子值
            factor_meta: 因子元数据
            data: OHLCV数据
            
        Returns:
            交易信号列表
        """
        if not factor_results or data is None or data.empty:
            return []
        
        # 获取最新因子值
        latest_factors = {}
        for name, values in factor_results.items():
            if not values.empty:
                latest_factors[name] = values.iloc[-1]
        
        if not latest_factors:
            return []
        
        # 计算权重
        weights = self._compute_weights(factor_results, factor_meta)
        
        # 计算综合得分
        composite = sum(latest_factors.get(f, 0) * weights.get(f, 0) for f in weights)
        
        # 标准化到[-1, 1]
        composite_norm = np.tanh(composite * 3)  # 压缩到[-1,1]
        
        # 生成信号
        signals = []
        latest_date = data.index[-1] if hasattr(data.index, '-1') else ""
        latest_close = data["close"].iloc[-1] if "close" in data else 0
        
        signal = TradingSignal(
            date=str(latest_date),
            strength=abs(composite_norm),
            composite_score=round(float(composite_norm), 4),
            factors_contribution={f: round(float(latest_factors.get(f, 0)), 4) for f in latest_factors},
            stop_loss=round(latest_close * (1 - self.config["stop_loss_pct"]), 2),
            take_profit=round(latest_close * (1 + self.config["take_profit_pct"]), 2),
            position_size=self._calculate_position_size(composite_norm, data),
        )
        
        # 判断方向
        if composite_norm > self.config["buy_threshold"]:
            signal.direction = 1
            signal.reason = f"多因子共振买入信号，综合得分{composite_norm:.3f}"
        elif composite_norm < self.config["sell_threshold"]:
            signal.direction = -1
            signal.reason = f"多因子共振卖出信号，综合得分{composite_norm:.3f}"
        else:
            signal.direction = 0
            signal.reason = f"信号中性，继续持有，综合得分{composite_norm:.3f}"
        
        signals.append(signal)
        return signals
    
    def _compute_weights(self, factor_results: Dict[str, pd.Series],
                         factor_meta: Dict[str, Dict] = None) -> Dict[str, float]:
        """计算因子权重"""
        method = self.config["method"]
        factor_names = list(factor_results.keys())
        n = len(factor_names)
        
        if n == 0:
            return {}
        
        if method == "equal":
            return {f: 1.0 / n for f in factor_names}
        
        elif method == "ic_weighted":
            if factor_meta:
                weights = {}
                for f in factor_names:
                    meta = factor_meta.get(f, {})
                    # 使用IC绝对值作为权重
                    ic = abs(meta.get("ic_mean", 0))
                    ir = abs(meta.get("ir", 0))
                    fitness = meta.get("fitness", 0)
                    
                    # 综合权重 = IC*0.4 + IR*0.3 + fitness*0.3
                    w = ic * 0.4 + ir * 0.3 + fitness * 0.3
                    weights[f] = max(w, 0.01)
                
                # 归一化
                total = sum(weights.values())
                if total > 0:
                    weights = {f: w / total for f, w in weights.items()}
                return weights
            else:
                return {f: 1.0 / n for f in factor_names}
        
        elif method == "optimized":
            return self._optimize_weights(factor_results, factor_meta)
        
        elif method == "voting":
            return {f: 1.0 for f in factor_names}  # 投票法权重相等
        
        return {f: 1.0 / n for f in factor_names}
    
    def _optimize_weights(self, factor_results: Dict[str, pd.Series],
                          factor_meta: Dict[str, Dict] = None) -> Dict[str, float]:
        """使用优化算法寻找最优权重"""
        factor_names = list(factor_results.keys())
        n = len(factor_names)
        
        if n < 2:
            return {f: 1.0 for f in factor_names}
        
        # 构建因子矩阵
        factor_df = pd.DataFrame(factor_results).dropna()
        if factor_df.empty:
            return {f: 1.0 / n for f in factor_names}
        
        # 目标函数：最大化组合夏普比率（简化版）
        def neg_sharpe(weights):
            composite = factor_df.values @ weights
            if composite.std() == 0:
                return 0
            sharpe = composite.mean() / composite.std()
            return -sharpe
        
        # 约束：权重和为1，每个权重 >= 0
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
        bounds = [(0.01, 0.5)] * n  # 单个因子最多50%
        x0 = np.array([1.0 / n] * n)
        
        try:
            result = minimize(neg_sharpe, x0, method="SLSQP",
                            bounds=bounds, constraints=constraints,
                            options={"maxiter": 100})
            optimal_weights = result.x
        except Exception:
            optimal_weights = x0
        
        return {f: round(float(w), 4) for f, w in zip(factor_names, optimal_weights)}
    
    def _generate_composite_signal(self, factor_results: Dict[str, pd.Series],
                                    weights: Dict[str, float]) -> pd.Series:
        """生成组合信号"""
        factor_df = pd.DataFrame(factor_results)
        
        # 标准化每个因子
        for col in factor_df.columns:
            std = factor_df[col].std()
            if std > 0:
                factor_df[col] = (factor_df[col] - factor_df[col].mean()) / std
            else:
                factor_df[col] = 0
        
        # 加权求和
        weighted_cols = []
        for f, w in weights.items():
            if f in factor_df.columns:
                weighted_cols.append(factor_df[f] * w)
        
        if weighted_cols:
            composite = pd.concat(weighted_cols, axis=1).sum(axis=1)
        else:
            composite = pd.Series(0, index=factor_df.index)
        
        return composite
    
    def _calculate_position_size(self, signal_strength: float, 
                                  data: pd.DataFrame) -> float:
        """计算建议仓位"""
        base = self.config["base_position"]
        
        # Kelly公式简化版
        kelly = base + (abs(signal_strength) - 0.5) * base * self.config["kelly_fraction"]
        
        # 波动率调整
        if self.config["volatility_adjust"] and len(data) >= 20:
            recent_vol = data["close"].pct_change().tail(20).std()
            avg_vol = data["close"].pct_change().std()
            if avg_vol > 0:
                vol_ratio = recent_vol / avg_vol
                kelly = kelly * (1 / max(0.5, min(2.0, vol_ratio)))
        
        # 限制范围
        position = max(0, min(self.config["max_position_pct"], kelly))
        return round(float(position), 4)
    
    def _backtest_ensemble(self, result: EnsembleResult, 
                           composite_signal: pd.Series,
                           data: pd.DataFrame,
                           factor_results: Dict[str, pd.Series]):
        """回测组合策略"""
        try:
            close = data["close"].astype(float)
            
            # 生成交易信号
            aligned = pd.DataFrame({
                "signal": composite_signal.reindex(data.index),
                "close": close,
            }).dropna()
            
            if len(aligned) < 20:
                return
            
            # 标准化信号
            signal_std = aligned["signal"].std()
            if signal_std > 0:
                aligned["signal_norm"] = aligned["signal"] / signal_std
            else:
                aligned["signal_norm"] = 0
            
            # 简单回测：信号 > 阈值做多，信号 < -阈值做空/卖出
            cash = self.config["initial_cash"]
            position = 0
            shares = 0
            trades = []
            entry_price = 0
            peak_value = cash
            
            for i in range(1, len(aligned)):
                price = aligned["close"].iloc[i]
                signal = aligned["signal_norm"].iloc[i]
                prev_signal = aligned["signal_norm"].iloc[i-1]
                
                commission = self.config["commission"]
                slippage = self.config["slippage"]
                
                # 买入信号
                if signal > self.config["buy_threshold"] and shares == 0:
                    cost = price * (1 + slippage)
                    max_shares = int(cash / (cost * (1 + commission)))
                    if max_shares > 0:
                        shares = max_shares
                        cash -= shares * cost * (1 + commission)
                        entry_price = cost
                        trades.append({
                            "type": "buy", "price": price, "shares": shares,
                            "date": str(aligned.index[i])
                        })
                
                # 卖出信号
                elif signal < self.config["sell_threshold"] and shares > 0:
                    revenue = shares * price * (1 - slippage) * (1 - commission)
                    cash += revenue
                    pnl_pct = (price - entry_price) / entry_price
                    trades.append({
                        "type": "sell", "price": price, "shares": shares,
                        "pnl_pct": pnl_pct, "date": str(aligned.index[i])
                    })
                    shares = 0
                
                # 止损
                elif shares > 0 and entry_price > 0:
                    if price < entry_price * (1 - self.config["stop_loss_pct"]):
                        revenue = shares * price * (1 - slippage) * (1 - commission)
                        cash += revenue
                        pnl_pct = (price - entry_price) / entry_price
                        trades.append({
                            "type": "stop_loss", "price": price, "shares": shares,
                            "pnl_pct": pnl_pct, "date": str(aligned.index[i])
                        })
                        shares = 0
                
                # 止盈
                elif shares > 0 and entry_price > 0:
                    if price > entry_price * (1 + self.config["take_profit_pct"]):
                        revenue = shares * price * (1 - slippage) * (1 - commission)
                        cash += revenue
                        pnl_pct = (price - entry_price) / entry_price
                        trades.append({
                            "type": "take_profit", "price": price, "shares": shares,
                            "pnl_pct": pnl_pct, "date": str(aligned.index[i])
                        })
                        shares = 0
                
                # 跟踪峰值
                current_value = cash + shares * price
                peak_value = max(peak_value, current_value)
            
            # 计算最终指标
            final_value = cash + shares * aligned["close"].iloc[-1]
            total_return = (final_value - self.config["initial_cash"]) / self.config["initial_cash"]
            
            # 交易统计
            sell_trades = [t for t in trades if t["type"] in ("sell", "stop_loss", "take_profit")]
            win_trades = [t for t in sell_trades if t.get("pnl_pct", 0) > 0]
            
            result.total_return = round(total_return, 4)
            result.annual_return = round(total_return * 252 / max(len(aligned), 1), 4)
            result.total_trades = len(sell_trades)
            result.win_rate = len(win_trades) / max(len(sell_trades), 1)
            
            if sell_trades:
                avg_win = np.mean([t["pnl_pct"] for t in win_trades]) if win_trades else 0
                avg_loss = abs(np.mean([t["pnl_pct"] for t in sell_trades if t["pnl_pct"] < 0])) if any(t["pnl_pct"] < 0 for t in sell_trades) else 1
                result.profit_loss_ratio = avg_win / (avg_loss + 1e-8)
            
            result.signals = trades
            
            # 因子贡献分析
            if factor_results:
                result.factor_contributions = {
                    f: round(float(w * 100), 1) for f, w in result.weights.items()
                }
            
        except Exception as e:
            logger.warning(f"组合回测失败: {e}")
            result.error = str(e)
    
    def get_ensemble_weights_report(self, weights: Dict[str, float],
                                     factor_meta: Dict[str, Dict] = None) -> str:
        """生成权重报告"""
        lines = ["═══ 因子组合权重 ═══"]
        for f, w in sorted(weights.items(), key=lambda x: -x[1]):
            pct = w * 100
            meta = factor_meta.get(f, {}) if factor_meta else {}
            ic = meta.get("ic_mean", 0)
            ir = meta.get("ir", 0)
            lines.append(f"  {f}: {pct:.1f}% (IC={ic:.4f}, IR={ir:.4f})")
        return "\n".join(lines)
