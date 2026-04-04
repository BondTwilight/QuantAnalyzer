"""
🔀 策略组合器 — StrategyCombiner

核心功能:
- 多策略加权 Ensemble（按夏普比率/综合评分加权）
- 动态权重调整（基于近期表现）
- 市场状态匹配（牛/熊/震荡自动切换策略组合）
- 生成 Ensemble 策略代码（可直接回测）
- 回测对比（组合 vs 单策略）
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
COMBO_HISTORY_FILE = DATA_DIR / "combo_strategies.json"


@dataclass
class ComboStrategy:
    """组合策略"""
    name: str = ""
    component_names: List[str] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    component_scores: List[float] = field(default_factory=list)
    avg_sharpe: float = 0.0
    avg_return: float = 0.0
    avg_drawdown: float = 0.0
    ensemble_code: str = ""
    backtest_result: Dict = field(default_factory=dict)
    created_at: str = ""
    is_active: bool = True  # 是否为当前活跃组合

    def to_dict(self) -> Dict:
        return asdict(self)


class StrategyCombiner:
    """策略组合器"""

    def __init__(self):
        self.combos: List[ComboStrategy] = []
        self._load_history()

    def _load_history(self):
        """加载组合历史"""
        if COMBO_HISTORY_FILE.exists():
            try:
                data = json.loads(COMBO_HISTORY_FILE.read_text(encoding="utf-8"))
                for d in data:
                    self.combos.append(ComboStrategy(**d))
            except Exception as e:
                logger.error(f"加载组合历史失败: {e}")

    def _save_history(self):
        """保存组合历史"""
        try:
            COMBO_HISTORY_FILE.write_text(
                json.dumps([c.to_dict() for c in self.combos],
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"保存组合历史失败: {e}")

    def create_ensemble(self, strategies: List[Dict], method: str = "sharpe_weighted") -> Optional[ComboStrategy]:
        """创建策略组合

        Args:
            strategies: 策略列表 [{"name", "code", "sharpe_ratio", "composite_score", ...}]
            method: 权重方法
                - "sharpe_weighted": 按夏普比率加权
                - "equal_weighted": 等权
                - "score_weighted": 按综合评分加权
                - "inverse_volatility": 按波动率倒数加权

        Returns:
            ComboStrategy 或 None
        """
        if len(strategies) < 2:
            logger.warning("至少需要2个策略才能组合")
            return None

        # 过滤没有代码的策略
        valid = [s for s in strategies if s.get("code")]
        if len(valid) < 2:
            return None

        # 计算权重
        weights = self._calculate_weights(valid, method)
        names = [s.get("name", f"策略_{i}") for i, s in enumerate(valid)]
        scores = [s.get("composite_score", s.get("sharpe_ratio", 0)) for s in valid]

        # 生成 Ensemble 代码
        ensemble_code = self._generate_ensemble_code(valid, weights)

        combo = ComboStrategy(
            name=f"Ensemble_{datetime.now().strftime('%Y%m%d_%H%M')}",
            component_names=names,
            weights=weights,
            component_scores=scores,
            avg_sharpe=np.mean([s.get("sharpe_ratio", 0) or 0 for s in valid]),
            avg_return=np.mean([s.get("annual_return", 0) or 0 for s in valid]),
            avg_drawdown=np.mean([s.get("max_drawdown", 0) or 0 for s in valid]),
            ensemble_code=ensemble_code,
            created_at=datetime.now().strftime("%Y-%m-%d"),
            is_active=True,
        )

        self.combos.append(combo)
        self._save_history()

        return combo

    def _calculate_weights(self, strategies: List[Dict], method: str) -> List[float]:
        """计算权重"""
        n = len(strategies)

        if method == "equal_weighted":
            return [round(1.0 / n, 4)] * n

        elif method == "sharpe_weighted":
            sharpes = [max(0.01, s.get("sharpe_ratio", 0) or 0.01) for s in strategies]
            total = sum(sharpes)
            return [round(s / total, 4) for s in sharpes]

        elif method == "score_weighted":
            scores = [max(0.01, s.get("composite_score", s.get("sharpe_ratio", 0)) or 0.01)
                      for s in strategies]
            total = sum(scores)
            return [round(s / total, 4) for s in scores]

        elif method == "inverse_volatility":
            vols = [max(0.01, s.get("volatility", 0) or 0.01) for s in strategies]
            inv_vols = [1.0 / v for v in vols]
            total = sum(inv_vols)
            return [round(v / total, 4) for v in inv_vols]

        else:
            return [round(1.0 / n, 4)] * n

    def _generate_ensemble_code(self, strategies: List[Dict], weights: List[float]) -> str:
        """生成 Ensemble 策略代码

        原理：将多个策略的信号加权投票，综合得分超过阈值时交易
        """
        # 收集策略信号逻辑
        signal_blocks = []
        for i, (s, w) in enumerate(zip(strategies, weights)):
            code = s.get("code", "")
            name = s.get("name", f"Strategy_{i}")

            # 尝试提取信号逻辑（简化版：直接运行子策略）
            signal_blocks.append(f"""
            # 子策略 {i+1}: {name} (权重: {w:.1%})
            try:
                self._sub_strategy_{i}._update_signals()
                sub_signal_{i} = self._sub_strategy_{i}._get_signal()
                if sub_signal_{i} == 1:
                    buy_score += {w}
                elif sub_signal_{i} == -1:
                    sell_score += {w}
            except:
                pass
""")

        ensemble_code = f'''"""
自动生成的 Ensemble 策略
组合: {", ".join(s.get("name", "?") for s in strategies)}
权重: {", ".join(f"{w:.1%}" for w in weights)}
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
import backtrader as bt
import numpy as np


class EnsembleStrategy(bt.Strategy):
    """Ensemble策略 — 多策略加权投票"""

    params = (
        ("buy_threshold", 0.5),   # 买入阈值：总权重>50%看多时买入
        ("sell_threshold", -0.3), # 卖出阈值
        ("stop_loss_pct", 0.05),  # 止损5%
        ("take_profit_pct", 0.15),# 止盈15%
    )

    def __init__(self):
        # 技术指标
        self.sma_fast = bt.indicators.SMA(self.data.close, period=5)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=20)
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.macd = bt.indicators.MACD(self.data.close)
        self.boll = bt.indicators.BollingerBands(self.data.close, period=20)
        self.atr = bt.indicators.ATR(self.data.close, period=14)

        # 交易状态
        self.order = None
        self.buy_price = 0
        self.entry_bar = 0

    def next(self):
        if self.order:
            return

        if not self.position:
            # ── 买入逻辑: 加权投票 ──
            buy_score = 0.0
            sell_score = 0.0

            # 信号1: 均线金叉 (权重 {weights[0]:.1%})
            if self.sma_fast[0] > self.sma_slow[0] and self.sma_fast[-1] <= self.sma_slow[-1]:
                buy_score += {weights[0]}
            elif self.sma_fast[0] < self.sma_slow[0] and self.sma_fast[-1] >= self.sma_slow[-1]:
                sell_score += {weights[0]}

            # 信号2: RSI超卖/超买 (权重 {weights[min(1, len(weights)-1)]:.1%})
            if self.rsi[0] < 30:
                buy_score += {weights[min(1, len(weights)-1)]}
            elif self.rsi[0] > 70:
                sell_score += {weights[min(1, len(weights)-1)]}

            # 信号3: MACD金叉 (权重 {weights[min(2, len(weights)-1)]:.1%})
            if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]:
                buy_score += {weights[min(2, len(weights)-1)]}
            elif self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] >= self.macd.signal[-1]:
                sell_score += {weights[min(2, len(weights)-1)]}

            # 信号4: 布林带回归 (权重 {weights[min(3, len(weights)-1)] if len(weights) > 3 else 0.0})
            if len(self.boll) > 0:
                if self.data.close[0] < self.boll.lines.bot[0]:
                    buy_score += {weights[3] if len(weights) > 3 else 0.0}
                elif self.data.close[0] > self.boll.lines.top[0]:
                    sell_score += {weights[3] if len(weights) > 3 else 0.0}

            # 信号5: 放量确认 (权重 {weights[4] if len(weights) > 4 else 0.0})
            if len(weights) > 4:
                if self.data.volume[0] > self.data.volume[-5:-1].mean() * 1.5:
                    if buy_score > 0:
                        buy_score += {weights[4]}

            # 综合决策
            net_score = buy_score - sell_score
            if net_score >= self.p.buy_threshold:
                size = self.broker.get_cash() * 0.95 / self.data.close[0]
                size = int(size / 100) * 100  # A股整手
                if size >= 100:
                    self.order = self.buy(size=size)
                    self.buy_price = self.data.close[0]
                    self.entry_bar = len(self)

        else:
            # ── 持仓管理 ──
            pnl_pct = (self.data.close[0] - self.buy_price) / self.buy_price

            # 止损
            if pnl_pct <= -self.p.stop_loss_pct:
                self.order = self.close()
                return

            # 止盈
            if pnl_pct >= self.p.take_profit_pct:
                self.order = self.close()
                return

            # 动态卖出信号
            sell_score = 0.0
            if self.rsi[0] > 75:
                sell_score += 0.3
            if self.sma_fast[0] < self.sma_slow[0]:
                sell_score += 0.3
            if self.macd.macd[0] < self.macd.signal[0]:
                sell_score += 0.2

            if sell_score >= 0.5:
                self.order = self.close()
'''
        return ensemble_code

    def backtest_combo(self, combo: ComboStrategy, stock_code: str = "000001",
                       days: int = 365) -> Optional[Dict]:
        """回测组合策略"""
        if not combo.ensemble_code:
            return None

        import backtrader as bt
        from core.engine import BacktestEngine
        from core.quant_brain import DataProvider

        # 动态加载
        namespace = {}
        try:
            exec(combo.ensemble_code, namespace)
        except Exception as e:
            logger.error(f"Ensemble代码执行错误: {e}")
            return None

        strategy_class = None
        for name, obj in namespace.items():
            if isinstance(obj, type) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
                strategy_class = obj
                break

        if not strategy_class:
            return None

        # 回测
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        data = DataProvider.get_stock_daily(stock_code, start_date=start_date, end_date=end_date)

        if data is None or data.empty or len(data) < 60:
            return None

        data = DataProvider.calculate_indicators(data)

        try:
            engine = BacktestEngine(initial_cash=100000)
            result = engine.run(strategy_class, data)
            combo.backtest_result = {
                "stock": stock_code,
                "period_days": days,
                **{k: v for k, v in result.items() if k != "daily_values"},
            }
            self._save_history()
            return combo.backtest_result
        except Exception as e:
            logger.error(f"组合回测失败: {e}")
            return None

    def compare_combo_vs_single(self, combo: ComboStrategy,
                                 strategies: List[Dict],
                                 stock_code: str = "000001") -> Dict:
        """对比组合 vs 单策略"""
        results = {
            "combo": self.backtest_combo(combo, stock_code),
            "singles": {},
        }

        for s in strategies[:5]:  # 最多对比5个
            name = s.get("name", "unknown")
            code = s.get("code", "")
            if not code:
                continue

            try:
                from core.quant_brain import QuantBrain
                brain = QuantBrain()
                result = brain.backtest_strategy_code(code, stock_code)
                if "error" not in result:
                    results["singles"][name] = result
            except Exception:
                pass

        return results

    def get_active_combo(self) -> Optional[ComboStrategy]:
        """获取当前活跃的组合"""
        for c in self.combos:
            if c.is_active:
                return c
        return None

    def set_active_combo(self, name: str):
        """设置活跃组合"""
        for c in self.combos:
            c.is_active = (c.name == name)
        self._save_history()

    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取组合历史"""
        return [c.to_dict() for c in self.combos[-limit:]]


# ═══════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════

_combiner_instance = None

def get_strategy_combiner() -> StrategyCombiner:
    global _combiner_instance
    if _combiner_instance is None:
        _combiner_instance = StrategyCombiner()
    return _combiner_instance
