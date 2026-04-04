"""
🧪 因子管理系统 — FactorManager

核心功能:
- 因子库 CRUD（增删改查）
- 因子 IC/IR 计算（信息系数/信息比率）
- 因子去冗余（相关性过滤）
- 因子有效性评估
- 因子组合评分
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

# 因子数据库文件
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
FACTOR_DB_FILE = DATA_DIR / "factor_database.json"
FACTOR_IC_CACHE = DATA_DIR / "factor_ic_cache.json"


@dataclass
class Factor:
    """量化因子"""
    name: str = ""
    category: str = ""  # 技术指标/量价/基本面/情绪
    source: str = ""  # 来源策略名
    description: str = ""
    formula: str = ""  # 计算公式（如果是代码因子）
    ic_mean: float = 0.0  # IC均值
    ic_std: float = 0.0  # IC标准差
    ir: float = 0.0  # 信息比率 = IC均值/IC标准差
    hit_rate: float = 0.0  # 因子胜率（IC>0的比例）
    turnover: float = 0.0  # 因子换手率
    decay: int = 5  # 因子衰减天数
    effective: bool = True  # 是否有效
    correlation_with_market: float = 0.0  # 与市场相关性
    created_at: str = ""
    updated_at: str = ""
    usage_count: int = 0  # 被策略使用次数
    backtest_score: float = 0.0  # 回测评分

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def quality_score(self) -> float:
        """因子质量评分 (0-100)"""
        # IR贡献（满分40）
        ir_score = min(40, abs(self.ir) * 20)
        # 胜率贡献（满分30）
        hit_score = min(30, self.hit_rate * 30)
        # IC均值贡献（满分20）
        ic_score = min(20, abs(self.ic_mean) * 50)
        # 使用次数贡献（满分10）
        usage_score = min(10, self.usage_count)

        total = ir_score + hit_score + ic_score + usage_score
        return round(min(100, max(0, total)), 1)


class FactorManager:
    """因子管理器"""

    # 预定义因子分类
    FACTOR_CATEGORIES = {
        "趋势类": ["SMA", "EMA", "MACD", "Price_Momentum", "趋势跟踪"],
        "均值回归类": ["RSI", "BOLL", "CCI", "Williams", "KDJ", "Mean_Reversion"],
        "量价类": ["Volume_MA", "OBV", "VWAP", "放量突破"],
        "波动类": ["ATR", "波动率"],
        "复合类": ["多信号共振", "Multi_Factor"],
    }

    def __init__(self):
        self.factors: List[Factor] = []
        self._load_data()

    def _load_data(self):
        """加载因子数据库"""
        if FACTOR_DB_FILE.exists():
            try:
                data = json.loads(FACTOR_DB_FILE.read_text(encoding="utf-8"))
                for d in data.get("factors", []):
                    self.factors.append(Factor(**d))
            except Exception as e:
                logger.error(f"加载因子库失败: {e}")

    def _save_data(self):
        """保存因子数据库"""
        try:
            data = {
                "factors": [f.to_dict() for f in self.factors],
                "updated_at": datetime.now().isoformat(),
                "total_factors": len(self.factors),
            }
            FACTOR_DB_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"保存因子库失败: {e}")

    # ─── CRUD ───

    def add_factor(self, name: str, source: str = "", category: str = "",
                   description: str = "") -> Factor:
        """添加因子"""
        # 检查是否已存在
        existing = self.find_factor(name)
        if existing:
            existing.usage_count += 1
            existing.updated_at = datetime.now().strftime("%Y-%m-%d")
            self._save_data()
            return existing

        # 自动分类
        if not category:
            category = self._auto_classify(name)

        factor = Factor(
            name=name,
            category=category,
            source=source,
            description=description or f"因子: {name}",
            created_at=datetime.now().strftime("%Y-%m-%d"),
            updated_at=datetime.now().strftime("%Y-%m-%d"),
            usage_count=1,
        )
        self.factors.append(factor)
        self._save_data()
        return factor

    def find_factor(self, name: str) -> Optional[Factor]:
        """查找因子"""
        for f in self.factors:
            if f.name == name:
                return f
        return None

    def remove_factor(self, name: str) -> bool:
        """删除因子"""
        for i, f in enumerate(self.factors):
            if f.name == name:
                self.factors.pop(i)
                self._save_data()
                return True
        return False

    def get_all_factors(self) -> List[Factor]:
        """获取所有因子"""
        return self.factors.copy()

    def get_factors_by_category(self, category: str) -> List[Factor]:
        """按分类获取因子"""
        return [f for f in self.factors if f.category == category]

    def get_effective_factors(self, min_ir: float = 0.02) -> List[Factor]:
        """获取有效因子（IR绝对值 > 阈值）"""
        return [f for f in self.factors if f.effective and abs(f.ir) >= min_ir]

    def get_top_factors(self, n: int = 10) -> List[Factor]:
        """获取质量最高的N个因子"""
        scored = sorted(self.factors, key=lambda f: -f.quality_score)
        return scored[:n]

    # ─── 因子计算 ───

    def calculate_factor_ic(self, factor_name: str, stock_pool: List[str] = None,
                            days: int = 252) -> Dict:
        """计算因子的IC（Information Coefficient）

        IC = RankCorrelation(因子值T, 未来收益T+1)

        Returns:
            {"ic_mean": float, "ic_std": float, "ir": float, "hit_rate": float}
        """
        from core.quant_brain import DataProvider

        if stock_pool is None:
            stock_pool = ["000001", "000333", "600519", "601318", "300750"]

        ic_values = []

        for code in stock_pool:
            try:
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
                data = DataProvider.get_stock_daily(code, start_date=start_date, end_date=end_date)

                if data is None or data.empty or len(data) < 60:
                    continue

                data = DataProvider.calculate_indicators(data)

                # 根据因子名获取因子值
                factor_values = self._compute_factor_values(factor_name, data)
                if factor_values is None or len(factor_values) < 30:
                    continue

                # 未来收益（T+1）
                future_returns = data["close"].pct_change(1).shift(-1)

                # 对齐
                valid = factor_values.notna() & future_returns.notna()
                if valid.sum() < 20:
                    continue

                # Rank IC (Spearman)
                ic = factor_values[valid].corr(future_returns[valid], method="spearman")
                if not np.isnan(ic):
                    ic_values.append(ic)

            except Exception as e:
                logger.debug(f"计算 {code} 的 {factor_name} IC失败: {e}")
                continue

        if not ic_values:
            return {"ic_mean": 0, "ic_std": 0, "ir": 0, "hit_rate": 0}

        ic_arr = np.array(ic_values)
        ic_mean = float(np.mean(ic_arr))
        ic_std = float(np.std(ic_arr))
        ir = ic_mean / ic_std if ic_std > 0 else 0
        hit_rate = float(np.sum(ic_arr > 0) / len(ic_arr))

        return {
            "ic_mean": round(ic_mean, 4),
            "ic_std": round(ic_std, 4),
            "ir": round(ir, 4),
            "hit_rate": round(hit_rate, 4),
        }

    def _compute_factor_values(self, factor_name: str, data: pd.DataFrame) -> Optional[pd.Series]:
        """根据因子名计算因子值"""
        name_upper = factor_name.upper()

        if "SMA" in name_upper or "均线" in factor_name:
            return data.get("ma_20", pd.Series(dtype=float))
        elif "EMA" in name_upper:
            return data["close"].ewm(span=12).mean() - data["close"].ewm(span=26).mean()
        elif "RSI" in name_upper:
            return data.get("rsi", pd.Series(dtype=float))
        elif "MACD" in name_upper:
            return data.get("macd_hist", pd.Series(dtype=float))
        elif "BOLL" in name_upper or "BOLLINGER" in name_upper:
            return (data["close"] - data["boll_mid"]) / data["boll_upper"].sub(data["boll_lower"]).replace(0, 1e-10)
        elif "ATR" in name_upper:
            return data.get("atr", pd.Series(dtype=float))
        elif "KDJ" in name_upper or "STOCHASTIC" in name_upper:
            return data.get("k", pd.Series(dtype=float))
        elif "OBV" in name_upper:
            # 简化OBV
            direction = data["close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
            return (direction * data["volume"]).cumsum()
        elif "VWAP" in name_upper:
            return data.get("vol_ma_5", pd.Series(dtype=float))  # 近似
        elif "MOMENTUM" in name_upper or "ROC" in name_upper or "动量" in factor_name:
            return data["close"].pct_change(5)
        elif "VOLUME" in name_upper or "量" in factor_name:
            return data["volume"] / data.get("vol_ma_20", data["volume"].rolling(20).mean())
        elif "CCI" in name_upper:
            # 简化CCI
            tp = (data["high"] + data["low"] + data["close"]) / 3
            ma_tp = tp.rolling(20).mean()
            md = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            return (tp - ma_tp) / (0.015 * md.replace(0, 1e-10))
        else:
            # 默认使用RSI作为通用因子
            return data.get("rsi", pd.Series(dtype=float))

    def update_factor_stats(self, factor_name: str, stock_pool: List[str] = None):
        """更新因子统计信息"""
        factor = self.find_factor(factor_name)
        if not factor:
            return

        ic_stats = self.calculate_factor_ic(factor_name, stock_pool)
        factor.ic_mean = ic_stats["ic_mean"]
        factor.ic_std = ic_stats["ic_std"]
        factor.ir = ic_stats["ir"]
        factor.hit_rate = ic_stats["hit_rate"]
        factor.effective = abs(factor.ir) >= 0.02 or abs(factor.ic_mean) >= 0.02
        factor.updated_at = datetime.now().strftime("%Y-%m-%d")

        self._save_data()

    def batch_update_ic(self, stock_pool: List[str] = None):
        """批量更新所有因子的IC"""
        for factor in self.factors:
            try:
                self.update_factor_stats(factor.name, stock_pool)
                logger.info(f"更新因子 {factor.name}: IC={factor.ic_mean:.4f}, IR={factor.ir:.4f}")
            except Exception as e:
                logger.warning(f"更新因子 {factor.name} 失败: {e}")

    # ─── 因子去冗余 ───

    def deduplicate_factors(self, correlation_threshold: float = 0.8) -> List[str]:
        """去冗余：移除高度相关的因子

        Returns:
            被移除的因子名列表
        """
        if len(self.factors) < 2:
            return []

        # 计算IC相关性矩阵
        names = [f.name for f in self.factors if abs(f.ic_mean) > 0 or abs(f.ir) > 0]
        if len(names) < 2:
            return []

        # 用IC值序列计算因子间相关性
        ic_matrix = {}
        for name in names:
            ic_matrix[name] = getattr(self.find_factor(name), "ic_mean", 0)

        # 简化：基于IC方向和大小来判断冗余
        removed = []
        to_remove = set()

        for i, name_a in enumerate(names):
            if name_a in to_remove:
                continue
            f_a = self.find_factor(name_a)
            if not f_a:
                continue
            for name_b in names[i+1:]:
                if name_b in to_remove:
                    continue
                f_b = self.find_factor(name_b)
                if not f_b:
                    continue

                # 如果两个因子的IC同向且大小接近，认为冗余
                if (abs(f_a.ic_mean - f_b.ic_mean) < 0.01 and
                    f_a.ic_mean * f_b.ic_mean > 0 and
                    f_a.category == f_b.category):
                    # 保留quality_score更高的
                    if f_a.quality_score >= f_b.quality_score:
                        to_remove.add(name_b)
                    else:
                        to_remove.add(name_a)
                        break

        for name in to_remove:
            if self.remove_factor(name):
                removed.append(name)

        if removed:
            logger.info(f"去冗余移除了 {len(removed)} 个因子: {removed}")
            self._save_data()

        return removed

    # ─── 分类 ───

    def _auto_classify(self, name: str) -> str:
        """自动分类因子"""
        name_upper = name.upper()
        for category, keywords in self.FACTOR_CATEGORIES.items():
            for kw in keywords:
                if kw.upper() in name_upper:
                    return category
        return "其他"

    # ─── 统计 ───

    def get_summary(self) -> Dict:
        """获取因子库概要"""
        total = len(self.factors)
        effective = len([f for f in self.factors if f.effective])
        by_category = {}
        for f in self.factors:
            cat = f.category or "未分类"
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total_factors": total,
            "effective_factors": effective,
            "by_category": by_category,
            "avg_quality": round(np.mean([f.quality_score for f in self.factors]), 1) if self.factors else 0,
            "top_factors": [
                {"name": f.name, "category": f.category, "quality": f.quality_score,
                 "ir": f.ir, "ic": f.ic_mean}
                for f in self.get_top_factors(5)
            ],
        }

    def get_factor_ranking(self) -> List[Dict]:
        """获取因子排名"""
        return [
            f.to_dict() for f in sorted(self.factors, key=lambda f: -f.quality_score)
        ]
