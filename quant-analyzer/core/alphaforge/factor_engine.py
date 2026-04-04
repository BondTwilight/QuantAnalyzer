"""
🧪 FactorEngine — 因子计算引擎

核心功能：
1. 因子表达式解析与安全执行
2. 50+ 内置因子算子（时序/截面/技术指标）
3. 因子值计算与标准化
4. 因子库管理（存储/查询/版本控制）

设计参考：WorldQuant Alpha Factory + AlphaAgent FactorAgent
"""

import numpy as np
import pandas as pd
import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
# 因子算子库 — WorldQuant Alpha 101/161 风格
# ═══════════════════════════════════════════════

class FactorOperators:
    """内置因子算子"""
    
    # ─── 时序算子 ───
    @staticmethod
    def ts_mean(data: pd.Series, window: int) -> pd.Series:
        """时间序列均值"""
        return data.rolling(window=window, min_periods=1).mean()
    
    @staticmethod
    def ts_std(data: pd.Series, window: int) -> pd.Series:
        """时间序列标准差"""
        return data.rolling(window=window, min_periods=1).std()
    
    @staticmethod
    def ts_sum(data: pd.Series, window: int) -> pd.Series:
        """时间序列求和"""
        return data.rolling(window=window, min_periods=1).sum()
    
    @staticmethod
    def ts_max(data: pd.Series, window: int) -> pd.Series:
        """时间序列最大值"""
        return data.rolling(window=window, min_periods=1).max()
    
    @staticmethod
    def ts_min(data: pd.Series, window: int) -> pd.Series:
        """时间序列最小值"""
        return data.rolling(window=window, min_periods=1).min()
    
    @staticmethod
    def ts_rank(data: pd.Series, window: int) -> pd.Series:
        """时间序列排名（当前值在窗口内的百分位）"""
        return data.rolling(window=window, min_periods=1).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
        )
    
    @staticmethod
    def ts_skewness(data: pd.Series, window: int) -> pd.Series:
        """时间序列偏度"""
        return data.rolling(window=window, min_periods=1).skew()
    
    @staticmethod
    def ts_kurtosis(data: pd.Series, window: int) -> pd.Series:
        """时间序列峰度"""
        return data.rolling(window=window, min_periods=1).kurt()
    
    @staticmethod
    def ts_delta(data: pd.Series, period: int) -> pd.Series:
        """时间序列差分"""
        return data.diff(period)
    
    @staticmethod
    def ts_delay(data: pd.Series, period: int) -> pd.Series:
        """时间序列延迟"""
        return data.shift(period)
    
    @staticmethod
    def ts_corr(data1: pd.Series, data2: pd.Series, window: int) -> pd.Series:
        """时间序列相关性"""
        return data1.rolling(window=window, min_periods=1).corr(data2)
    
    @staticmethod
    def ts_cov(data1: pd.Series, data2: pd.Series, window: int) -> pd.Series:
        """时间序列协方差"""
        return data1.rolling(window=window, min_periods=1).cov(data2)
    
    @staticmethod
    def ts_regression(data: pd.Series, window: int) -> pd.Series:
        """时间序列回归斜率"""
        def _ols_slope(x):
            if len(x) < window:
                return np.nan
            y = np.arange(len(x), dtype=float)
            slope = np.polyfit(y, x, 1)[0]
            return slope
        return data.rolling(window=window, min_periods=window).apply(_ols_slope, raw=True)
    
    @staticmethod
    def ts_decay_linear(data: pd.Series, window: int) -> pd.Series:
        """线性衰减加权均值"""
        weights = np.arange(1, window + 1, dtype=float)
        weights = weights / weights.sum()
        return data.rolling(window=window, min_periods=1).apply(
            lambda x: np.dot(x, weights[-len(x):]) / weights[-len(x):].sum() if len(x) > 0 else np.nan,
            raw=True
        )
    
    @staticmethod
    def ts_arg_max(data: pd.Series, window: int) -> pd.Series:
        """时间序列最大值位置"""
        return data.rolling(window=window, min_periods=1).apply(
            lambda x: np.argmax(x) + 1, raw=True
        )
    
    @staticmethod
    def ts_arg_min(data: pd.Series, window: int) -> pd.Series:
        """时间序列最小值位置"""
        return data.rolling(window=window, min_periods=1).apply(
            lambda x: np.argmin(x) + 1, raw=True
        )
    
    @staticmethod
    def ts_product(data: pd.Series, window: int) -> pd.Series:
        """时间序列累积乘积"""
        log_data = np.log(data.replace(0, np.nan).clip(lower=1e-10))
        return np.exp(log_data.rolling(window=window, min_periods=1).sum())
    
    @staticmethod
    def ts_zscore(data: pd.Series, window: int) -> pd.Series:
        """时间序列Z-Score标准化"""
        mean = data.rolling(window=window, min_periods=1).mean()
        std = data.rolling(window=window, min_periods=1).std()
        return (data - mean) / std.replace(0, np.nan)
    
    # ─── 截面算子（跨股票） ───
    @staticmethod
    def rank(data: pd.Series) -> pd.Series:
        """截面排名（百分位）"""
        return data.rank(pct=True)
    
    @staticmethod
    def zscore(data: pd.Series) -> pd.Series:
        """截面Z-Score标准化"""
        return (data - data.mean()) / data.std()
    
    @staticmethod
    def demean(data: pd.Series) -> pd.Series:
        """去均值"""
        return data - data.mean()
    
    @staticmethod
    def normalize(data: pd.Series) -> pd.Series:
        """归一化到[0,1]"""
        min_val = data.min()
        max_val = data.max()
        if max_val == min_val:
            return pd.Series(0.5, index=data.index)
        return (data - min_val) / (max_val - min_val)
    
    @staticmethod
    def winsorize(data: pd.Series, lower: float = 0.05, upper: float = 0.95) -> pd.Series:
        """缩尾处理"""
        q_low = data.quantile(lower)
        q_high = data.quantile(upper)
        return data.clip(lower=q_low, upper=q_high)
    
    @staticmethod
    def sign(data: pd.Series) -> pd.Series:
        """符号函数"""
        return np.sign(data)
    
    @staticmethod
    def log(data: pd.Series) -> pd.Series:
        """对数变换"""
        return np.log(data.clip(lower=1e-10))
    
    @staticmethod
    def abs(data: pd.Series) -> pd.Series:
        """绝对值"""
        return data.abs()
    
    @staticmethod
    def power(data: pd.Series, exp: float) -> pd.Series:
        """幂运算"""
        return data.pow(exp)
    
    @staticmethod
    def max_(data1: pd.Series, data2: pd.Series) -> pd.Series:
        """取最大值"""
        return np.maximum(data1, data2)
    
    @staticmethod
    def min_(data1: pd.Series, data2: pd.Series) -> pd.Series:
        """取最小值"""
        return np.minimum(data1, data2)
    
    # ─── 技术指标算子 ───
    @staticmethod
    def sma(data: pd.Series, window: int) -> pd.Series:
        """简单移动平均"""
        return data.rolling(window=window, min_periods=1).mean()
    
    @staticmethod
    def ema(data: pd.Series, window: int) -> pd.Series:
        """指数移动平均"""
        return data.ewm(span=window, adjust=False).mean()
    
    @staticmethod
    def rsi(data: pd.Series, window: int = 14) -> pd.Series:
        """相对强弱指标"""
        delta = data.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD指标"""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger(data: pd.Series, window: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """布林带"""
        mid = data.rolling(window=window, min_periods=1).mean()
        std = data.rolling(window=window, min_periods=1).std()
        upper = mid + num_std * std
        lower = mid - num_std * std
        return upper, mid, lower
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """平均真实波幅"""
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=window, min_periods=1).mean()
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """能量潮指标"""
        direction = np.sign(close.diff())
        direction.iloc[0] = 0
        return (direction * volume).cumsum()
    
    @staticmethod
    def vwap(close: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
        """成交量加权平均价"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).rolling(window=window, min_periods=1).sum() / \
               volume.rolling(window=window, min_periods=1).sum()
    
    @staticmethod
    def roc(data: pd.Series, window: int = 12) -> pd.Series:
        """变化率"""
        return data.pct_change(window) * 100
    
    @staticmethod
    def momentum(data: pd.Series, window: int = 10) -> pd.Series:
        """动量"""
        return data - data.shift(window)
    
    @staticmethod
    def keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series, 
                        ema_window: int = 20, atr_window: int = 10, mult: float = 1.5) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """肯特纳通道"""
        mid = close.ewm(span=ema_window, adjust=False).mean()
        atr_val = FactorOperators.atr(high, low, close, atr_window)
        upper = mid + mult * atr_val
        lower = mid - mult * atr_val
        return upper, mid, lower
    
    @staticmethod
    def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, pd.Series]:
        """一目均衡表"""
        tenkan = (high.rolling(9, min_periods=1).max() + low.rolling(9, min_periods=1).min()) / 2
        kijun = (high.rolling(26, min_periods=1).max() + low.rolling(26, min_periods=1).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(52, min_periods=1).max() + low.rolling(52, min_periods=1).min()) / 2).shift(26)
        chikou = close.shift(-26)
        return {
            "tenkan": tenkan, "kijun": kijun, 
            "senkou_a": senkou_a, "senkou_b": senkou_b, "chikou": chikou
        }
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                   k_window: int = 14, d_window: int = 3) -> Tuple[pd.Series, pd.Series]:
        """随机指标"""
        lowest = low.rolling(window=k_window, min_periods=1).min()
        highest = high.rolling(window=k_window, min_periods=1).max()
        stoch_k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
        stoch_d = stoch_k.rolling(window=d_window, min_periods=1).mean()
        return stoch_k, stoch_d
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """平均趋向指标"""
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        atr_val = FactorOperators.atr(high, low, close, window)
        plus_di = 100 * plus_dm.ewm(span=window, adjust=False).mean() / atr_val.replace(0, np.nan)
        minus_di = 100 * minus_dm.ewm(span=window, adjust=False).mean() / atr_val.replace(0, np.nan)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        return dx.ewm(span=window, adjust=False).mean()
    
    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """威廉指标"""
        highest = high.rolling(window=window, min_periods=1).max()
        lowest = low.rolling(window=window, min_periods=1).min()
        return -100 * (highest - close) / (highest - lowest).replace(0, np.nan)
    
    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> pd.Series:
        """商品通道指数"""
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(window=window, min_periods=1).mean()
        mad = tp.rolling(window=window, min_periods=1).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        return (tp - sma_tp) / (0.015 * mad).replace(0, np.nan)
    
    @staticmethod
    def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, window: int = 14) -> pd.Series:
        """资金流量指标"""
        tp = (high + low + close) / 3
        mf = tp * volume
        pos_mf = mf.where(tp > tp.shift(1), 0)
        neg_mf = mf.where(tp < tp.shift(1), 0)
        pos_sum = pos_mf.rolling(window=window, min_periods=1).sum()
        neg_sum = neg_mf.rolling(window=window, min_periods=1).sum()
        mfi_ratio = pos_sum / neg_sum.replace(0, np.nan)
        return 100 - (100 / (1 + mfi_ratio))
    
    @staticmethod
    def elder_ray(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 13) -> Tuple[pd.Series, pd.Series]:
        """伊尔德射线指标"""
        bull_power = high - close.ema(window)
        bear_power = low - close.ema(window)
        return bull_power, bear_power


# ═══════════════════════════════════════════════
# 因子定义与存储
# ═══════════════════════════════════════════════

@dataclass
class FactorDefinition:
    """因子定义"""
    name: str                           # 因子名称
    expression: str                     # 因子表达式
    category: str = "technical"         # 分类: technical/statistical/ml/composite
    description: str = ""               # 描述
    author: str = "alphaforge"          # 创建者: alphaforge/gp/llm/manual
    version: int = 1                    # 版本
    params: Dict[str, Any] = field(default_factory=dict)
    ic_mean: float = 0.0                # 平均IC
    ic_std: float = 0.0                 # IC标准差
    ir: float = 0.0                     # 信息比率 = IC_mean / IC_std
    sharpe: float = 0.0                 # 因子夏普
    turnover: float = 0.0               # 换手率
    max_drawdown: float = 0.0           # 最大回撤
    fitness: float = 0.0                # 适应度 = 综合评分
    is_valid: bool = False              # 是否有效
    created_at: str = ""                # 创建时间
    evaluated_at: str = ""              # 评估时间
    data_window: int = 250              # 所需数据窗口
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> "FactorDefinition":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)


class FactorStore:
    """因子存储管理"""
    
    def __init__(self, store_dir: Optional[str] = None):
        if store_dir is None:
            store_dir = str(Path(__file__).parent.parent.parent / "data" / "factor_store")
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.factors_file = self.store_dir / "factors.json"
        self._factors: Dict[str, FactorDefinition] = {}
        self._load()
    
    def _load(self):
        """从文件加载因子库"""
        if self.factors_file.exists():
            try:
                data = json.loads(self.factors_file.read_text(encoding="utf-8"))
                for name, fd in data.items():
                    self._factors[name] = FactorDefinition.from_dict(fd)
            except Exception as e:
                logger.warning(f"加载因子库失败: {e}")
    
    def _save(self):
        """保存因子库到文件"""
        try:
            data = {name: fd.to_dict() for name, fd in self._factors.items()}
            self.factors_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"保存因子库失败: {e}")
    
    def add(self, factor: FactorDefinition) -> bool:
        """添加或更新因子"""
        if not factor.name or not factor.expression:
            return False
        
        # 如果已存在，检查是否需要更新
        existing = self._factors.get(factor.name)
        if existing and existing.version >= factor.version:
            if factor.fitness <= existing.fitness:
                return False  # 新版本不会更差才更新
        
        if not factor.created_at:
            factor.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self._factors[factor.name] = factor
        self._save()
        return True
    
    def get(self, name: str) -> Optional[FactorDefinition]:
        """获取因子"""
        return self._factors.get(name)
    
    def get_all(self, category: str = None, valid_only: bool = False) -> List[FactorDefinition]:
        """获取所有因子"""
        factors = list(self._factors.values())
        if category:
            factors = [f for f in factors if f.category == category]
        if valid_only:
            factors = [f for f in factors if f.is_valid]
        return factors
    
    def get_top_factors(self, metric: str = "fitness", limit: int = 20) -> List[FactorDefinition]:
        """获取最优因子"""
        factors = sorted(self._factors.values(), 
                        key=lambda f: getattr(f, metric, 0), reverse=True)
        return factors[:limit]
    
    def remove(self, name: str) -> bool:
        """删除因子"""
        if name in self._factors:
            del self._factors[name]
            self._save()
            return True
        return False
    
    def count(self) -> int:
        return len(self._factors)
    
    def get_factor_names(self) -> List[str]:
        return list(self._factors.keys())
    
    def get_similar_factors(self, expression: str, threshold: float = 0.8) -> List[str]:
        """查找相似因子（基于表达式哈希）"""
        target_hash = hashlib.md5(expression.strip().encode()).hexdigest()[:16]
        similar = []
        for name, f in self._factors.items():
            f_hash = hashlib.md5(f.expression.strip().encode()).hexdigest()[:16]
            if f_hash == target_hash:
                similar.append(name)
        return similar


# ═══════════════════════════════════════════════
# 因子计算引擎
# ═══════════════════════════════════════════════

class FactorEngine:
    """
    因子计算引擎
    
    安全地将因子表达式转换为可执行的Python函数，
    并在OHLCV数据上计算因子值。
    """
    
    def __init__(self, store: Optional[FactorStore] = None):
        self.operators = FactorOperators()
        self.store = store or FactorStore()
        self._cache: Dict[str, pd.Series] = {}
    
    def compute(self, expression: str, data: pd.DataFrame, 
                params: Dict[str, Any] = None) -> pd.Series:
        """
        计算因子值
        
        Args:
            expression: 因子表达式，支持嵌套运算
            data: OHLCV DataFrame，需包含 open/high/low/close/volume 列
            params: 表达式参数
            
        Returns:
            因子值序列
        """
        if data is None or data.empty:
            return pd.Series(dtype=float)
        
        params = params or {}
        
        # 提取价格和成交量数据
        close = data["close"].astype(float)
        high = data["high"].astype(float) if "high" in data else close
        low = data["low"].astype(float) if "low" in data else close
        open_ = data["open"].astype(float) if "open" in data else close
        volume = data["volume"].astype(float) if "volume" in data else pd.Series(1.0, index=data.index)
        
        # 构建安全执行环境
        safe_globals = {
            "ts_mean": self.operators.ts_mean,
            "ts_std": self.operators.ts_std,
            "ts_sum": self.operators.ts_sum,
            "ts_max": self.operators.ts_max,
            "ts_min": self.operators.ts_min,
            "ts_rank": self.operators.ts_rank,
            "ts_skewness": self.operators.ts_skewness,
            "ts_kurtosis": self.operators.ts_kurtosis,
            "ts_delta": self.operators.ts_delta,
            "ts_delay": self.operators.ts_delay,
            "ts_corr": self.operators.ts_corr,
            "ts_cov": self.operators.ts_cov,
            "ts_regression": self.operators.ts_regression,
            "ts_decay_linear": self.operators.ts_decay_linear,
            "ts_arg_max": self.operators.ts_arg_max,
            "ts_arg_min": self.operators.ts_arg_min,
            "ts_product": self.operators.ts_product,
            "ts_zscore": self.operators.ts_zscore,
            "rank": self.operators.rank,
            "zscore": self.operators.zscore,
            "demean": self.operators.demean,
            "normalize": self.operators.normalize,
            "winsorize": self.operators.winsorize,
            "sign": self.operators.sign,
            "log": self.operators.log,
            "abs": self.operators.abs,
            "power": self.operators.power,
            "max": self.operators.max_,
            "min": self.operators.min_,
            "sma": self.operators.sma,
            "ema": self.operators.ema,
            "rsi": self.operators.rsi,
            "macd": self.operators.macd,
            "bollinger": self.operators.bollinger,
            "atr": self.operators.atr,
            "obv": self.operators.obv,
            "vwap": self.operators.vwap,
            "roc": self.operators.roc,
            "momentum": self.operators.momentum,
            "stochastic": self.operators.stochastic,
            "adx": self.operators.adx,
            "williams_r": self.operators.williams_r,
            "cci": self.operators.cci,
            "mfi": self.operators.mfi,
            "np": np,
            "pd": pd,
        }
        
        safe_locals = {
            "close": close, "high": high, "low": low,
            "open": open_, "volume": volume, "v": volume,
            **params
        }
        
        try:
            # 安全执行因子表达式
            result = eval(expression, {"__builtins__": {}}, {**safe_globals, **safe_locals})
            
            # 处理返回结果
            if isinstance(result, pd.Series):
                result.index = data.index[:len(result)]
                return result
            elif isinstance(result, tuple):
                # 如MACD返回元组，取第一个
                if isinstance(result[0], pd.Series):
                    result[0].index = data.index[:len(result[0])]
                    return result[0]
                return pd.Series(result[0], index=data.index)
            elif isinstance(result, dict):
                # 如Ichimoku返回字典，取第一个值
                first_val = next(iter(result.values()))
                if isinstance(first_val, pd.Series):
                    first_val.index = data.index[:len(first_val)]
                    return first_val
            elif np.isscalar(result):
                return pd.Series(float(result), index=data.index)
            
            return pd.Series(dtype=float, index=data.index)
            
        except Exception as e:
            logger.warning(f"因子计算失败 [{expression[:50]}...]: {e}")
            return pd.Series(dtype=float, index=data.index)
    
    def compute_and_register(self, factor: FactorDefinition, 
                             data: pd.DataFrame) -> Optional[pd.Series]:
        """计算因子值并注册到因子库"""
        values = self.compute(factor.expression, data, factor.params)
        if values is not None and not values.empty:
            self.store.add(factor)
            return values
        return None
    
    def batch_compute(self, factors: List[FactorDefinition], 
                      data: pd.DataFrame) -> Dict[str, pd.Series]:
        """批量计算因子"""
        results = {}
        for factor in factors:
            values = self.compute(factor.expression, data, factor.params)
            if values is not None and not values.empty:
                results[factor.name] = values
        return results
    
    @staticmethod
    def neutralize(factor_values: pd.Series, industry: pd.Series = None) -> pd.Series:
        """因子中性化（去行业和市值影响）"""
        if industry is None:
            return factor_values - factor_values.mean()
        return factor_values.groupby(industry).transform(lambda x: x - x.mean())
    
    @staticmethod
    def standardize(factor_values: pd.Series, method: str = "zscore") -> pd.Series:
        """因子标准化"""
        if method == "zscore":
            return (factor_values - factor_values.mean()) / factor_values.std().replace(0, 1)
        elif method == "rank":
            return factor_values.rank(pct=True)
        elif method == "normalize":
            min_v, max_v = factor_values.min(), factor_values.max()
            return (factor_values - min_v) / (max_v - min_v).replace(0, 1)
        return factor_values
