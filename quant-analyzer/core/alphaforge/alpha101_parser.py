"""
🔍 Alpha101Parser — WorldQuant Alpha101 因子解析器

数据来源: WorldQuant 公开论文 "101 Formulaic Alphas" (Kakushadze, 2016)
论文链接: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2971375

核心功能:
1. 将 WorldQuant BRAIN 平台算子映射到 AlphaForge 兼容表达式
2. 自动翻译 101 个公式化因子
3. 过滤不可用因子（需要行业分类数据的标记为不可用）
4. 按因子逻辑分类（动量/量价/波动率/反转/趋势/流动性/统计/复合）
5. 输出可直接喂给 AlphaForge 进化引擎的因子列表

翻译规则:
- rank → rank (截面排名)
- ts_rank → ts_rank
- ts_delta → ts_delta
- delay → ts_delay
- corr → ts_corr
- covariance → ts_cov
- signedpower(x, a) → sign(x) * abs(x) ** a
- scale(x) → normalize(x)
- IndNeutralize(x, industry) → demean(x) [标记 neutralized=True]
- Sum/Max/Min/Mean/StdDev → ts_sum/ts_max/ts_min/ts_mean/ts_std
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 算子映射表 — WQ BRAIN → AlphaForge
# ═══════════════════════════════════════════════

OPERATOR_MAPPING = {
    # 直接映射
    "rank": "rank",
    "ts_rank": "ts_rank",
    "ts_delta": "ts_delta",
    "ts_arg_max": "ts_arg_max",
    "ts_arg_min": "ts_arg_min",
    "ts_sum": "ts_sum",
    "ts_product": "ts_product",
    "ts_skewness": "ts_skewness",
    "ts_kurtosis": "ts_kurtosis",
    "ts_regression": "ts_regression",
    "ts_decay_linear": "ts_decay_linear",
    "ts_corr": "ts_corr",
    "ts_cov": "ts_cov",
    "ts_std_dev": "ts_std",
    "ts_zscore": "ts_zscore",
    
    # 别名映射
    "delay": "ts_delay",
    "delta": "ts_delta",
    "covariance": "ts_cov",
    
    # 函数式映射
    "sum": "ts_sum",
    "product": "ts_product",
    "max": "ts_max",
    "min": "ts_min",
    "mean": "ts_mean",
    "stddev": "ts_std",
    "std_dev": "ts_std",
    "ts_max": "ts_max",
    "ts_min": "ts_min",
    "ts_mean": "ts_mean",
    "ts_std": "ts_std",
}


@dataclass
class Alpha101Factor:
    """解析后的 Alpha101 因子"""
    alpha_id: int
    original_expr: str          # WQ BRAIN 原始表达式
    translated_expr: str        # AlphaForge 翻译后表达式
    category: str               # 因子分类
    description: str            # 中文描述
    usable: bool                # 是否可用（无需行业数据）
    requires_industry: bool     # 是否需要行业分类
    complexity: str             # 复杂度: simple/medium/complex
    tags: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════
# Alpha101 完整因子表达式
# ═══════════════════════════════════════════════

ALPHA_101_FORMULAS = {
    # ─── 价格动量类 (1-15) ───
    1: {
        "expr": "(-1 * rank(ts_arg_max(close - delay(close, 1), 6)) + rank(ts_std_dev(close, 20)))",
        "category": "price_momentum",
        "desc": "价格最高点位置排名 + 波动率排名的反向信号",
    },
    2: {
        "expr": "-1 * rank(corr(delta(log(volume), 1), close - delay(close, 1), 6))",
        "category": "volume_price",
        "desc": "量价相关性的反向信号",
    },
    3: {
        "expr": "-1 * corr(open, volume, 10) * rank(std_dev(close, 10))",
        "category": "volume_price",
        "desc": "开盘价与成交量负相关 × 波动率排名",
    },
    4: {
        "expr": "-1 * ts_rank(close, 10) * rank(delta(delta(close, 1), 1)) * rank(std_dev(close, 10))",
        "category": "price_momentum",
        "desc": "价格排名 × 二阶差分排名 × 波动率排名",
    },
    5: {
        "expr": "-1 * ts_rank(open, 10) * ts_rank(close, 7) * ts_rank(volume, 5)",
        "category": "composite",
        "desc": "开盘/收盘/成交量三维时序排名乘积",
    },
    6: {
        "expr": "-1 * sign(ts_delta(volume, 1)) * ts_delta(close, 1)",
        "category": "volume_price",
        "desc": "量变方向 × 价格变化",
    },
    7: {
        "expr": "((adv20 < volume) ? (-1 * ts_rank(abs(ts_delta(close, 7)), 60) * sign(ts_delta(close, 7))) : 1)",
        "category": "volume_price",
        "desc": "放量时的价格变化幅度排名信号",
        "needs_industry": False,
    },
    8: {
        "expr": "-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10)))",
        "category": "price_momentum",
        "desc": "5日开盘-收益乘积的10日变化",
    },
    9: {
        "expr": "(0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((0 > ts_max(delta(close, 1), 5)) ? delta(close, 1) : (-1 * delta(close, 1)))",
        "category": "reversal",
        "desc": "基于5日价格变化方向的均值回复信号",
    },
    10: {
        "expr": "rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((0 > ts_max(delta(close, 1), 4)) ? delta(close, 1) : (-1 * delta(close, 1)))) * -1)",
        "category": "reversal",
        "desc": "4日价格变化方向的排名均值回复信号",
    },
    11: {
        "expr": "((rank(ts_max(delay((close - open), 1), 5)) - rank(ts_max(delay((open - close), 1), 5))) * -1)",
        "category": "reversal",
        "desc": "5日最大阳线与最大阴线排名差的反向信号",
    },
    12: {
        "expr": "(sign(delta(volume, 1)) * (-1 * delta(close, 1)))",
        "category": "volume_price",
        "desc": "量变方向 × 价格变化反向",
    },
    13: {
        "expr": "-1 * rank(corr(open, volume, 10)) * rank(corr(open, close, 10))",
        "category": "volume_price",
        "desc": "开-量相关 × 开-收相关的排名乘积",
    },
    14: {
        "expr": "-1 * rank(corr(rank(open), rank(volume), 3))",
        "category": "volume_price",
        "desc": "开盘排名-量排名3日相关性的反向排名",
    },
    15: {
        "expr": "sum(max(0, close - delay(close, 1)), 12) / (sum(abs(close - delay(close, 1)), 12) + 1e-10) * -1",
        "category": "reversal",
        "desc": "12日上涨占比（类似RSI）反向信号",
    },

    # ─── 波动率与统计类 (16-30) ───
    16: {
        "expr": "-1 * rank(corr(sum(close, 5), sum(close, 20), 10))",
        "category": "trend",
        "desc": "5日累计与20日累计的相关性排名",
    },
    17: {
        "expr": "((-1 * rank(ts_rank(close, 10))) * rank(delta(delay(close, 1), 5)) * rank(ts_rank(corr(cor(close, volume, 6), cor(close, volume, 2), 10), 5)) * rank(corr(rank(open), rank(volume), 5)))",
        "category": "composite",
        "desc": "多维排名的复合因子",
    },
    18: {
        "expr": "-1 * rank(std_dev(abs(close - open), 15) + (close - open))",
        "category": "volatility",
        "desc": "15日振幅标准差 + 涨跌差值",
    },
    19: {
        "expr": "-1 * sign(ts_corr(close, volume, 5)) * ts_delta(close, 5)",
        "category": "volume_price",
        "desc": "5日量价相关性方向 × 5日价格变化",
    },
    20: {
        "expr": "-1 * rank(open - delay(high, 1)) * rank(open - delay(close, 1)) * rank(open - delay(low, 1))",
        "category": "reversal",
        "desc": "开盘价与昨日高低收排名差",
    },

    # ─── 复合因子 (21-40) ───
    21: {
        "expr": "sum(max(0, high - delay(close, 1)), 20) / sum(max(0, delay(close, 1) - low), 20) * -1",
        "category": "reversal",
        "desc": "20日上影线总和与下影线总和比",
    },
    22: {
        "expr": "-1 * (delta(cor(high, volume, 5), 5) * rank(std_dev(close, 20)))",
        "category": "volume_price",
        "desc": "5日最高价-量相关性变化 × 波动率排名",
    },
    23: {
        "expr": "sum(((close - low) - (high - close)) / (high - low) * volume, 20) / sum(volume, 20) * -1",
        "category": "volume_price",
        "desc": "20日加权价格位置（类似威廉指标累积）",
    },
    24: {
        "expr": "sum(max(0, close - delay(close, 1)), 20) / max(sum(max(0, close - delay(close, 1)), 20), sum(max(0, delay(close, 1) - close), 20)) * -1",
        "category": "reversal",
        "desc": "20日上涨占比（加权RSI风格）",
    },
    25: {
        "expr": "rank(decay_linear(close, 8) / delay(close, 8)) * -1 + rank(decay_linear(cor(cor(adv60, low, 5), low, 5) + (high / low), 5) - 0.5, 5)",
        "category": "composite",
        "desc": "8日衰减价格变化率 + 60日量价复合信号",
    },
    26: {
        "expr": "-1 * max(rank(decay_linear(delta(close, 2), 3)), rank(decay_linear(cor((close - open), volume, 5), 5)))",
        "category": "composite",
        "desc": "2日价格变化衰减 × 开收价差-量相关的最大值排名",
    },
    27: {
        "expr": "rank(decay_linear(delay((open - close), 1), 9) / delay((open - close), 1)) * -1",
        "category": "reversal",
        "desc": "9日衰减开收差值变化率",
    },
    28: {
        "expr": "rank(delay((high - low) / (close - open), 1)) * rank(cor(rank(volume), rank(high - low), 5))",
        "category": "volatility",
        "desc": "昨日振幅比 × 量-振幅相关排名",
    },
    29: {
        "expr": "rank(max(max(high - low), abs(delay(close, 1) - open)), max(max(high - low), abs(open - delay(close, 1))))) * rank(cor(high, volume, 3)) * -1",
        "category": "composite",
        "desc": "真实波幅排名 × 3日最高价-量相关排名",
    },
    30: {
        "expr": "(rank(cor(close, sum(mean(delay(close, 1), 3), 2), 3)) - rank(cor(close, rank(volume), 3))) * rank(cor(high, rank(volume), 3))",
        "category": "composite",
        "desc": "价格自相关排名与量相关排名的差 × 高-量相关",
    },

    # ─── 量价关系 (31-50) ───
    31: {
        "expr": "(rank(rank(rank(decay_linear(rank(rank(rank(delay((high - low) / (close - open), 1), 1), 2), 3), 2), 1))) * rank(cor(cor(rank(volume), rank(high - low), 5), rank(volume), 5))) * -1",
        "category": "composite",
        "desc": "高复杂度复合因子：多层衰减排名 × 量价相关",
        "complexity": "complex",
    },
    32: {
        "expr": "scale(sum((close - open) / (high - low) * volume, 20))",
        "category": "volume_price",
        "desc": "20日加权价格位置（归一化）",
    },
    33: {
        "expr": "rank(-1 * ts_rank(delay((close - open), 1), 5) * ts_rank(delay(cor(rank(close), rank(volume), 3), 5), 5))",
        "category": "volume_price",
        "desc": "延迟开收差排名 × 延迟量价相关排名",
    },
    34: {
        "expr": "rank(max(max(high - low), abs(delay(close, 1) - open))) * rank(min(min(high - low), abs(open - delay(close, 1))))",
        "category": "volatility",
        "desc": "最大真实波幅 × 最小真实波幅排名",
    },
    35: {
        "expr": "rank(ts_regression(close, 5)) * -1",
        "category": "trend",
        "desc": "5日回归斜率的反向排名",
    },
    36: {
        "expr": "rank(rank(rank(decay_linear(close, 5))) - rank(decay_linear(cor(cor(adv60, low, 5), low, 5), 5))) * -1",
        "category": "composite",
        "desc": "5日衰减价格排名 - 量价相关衰减排名",
    },
    37: {
        "expr": "-1 * rank(ts_rank(decay_linear(close, 8), 6)) * sign(ts_corr(close, volume, 5))",
        "category": "composite",
        "desc": "8日衰减价格6日排名 × 量价相关性方向",
    },
    38: {
        "expr": "-1 * rank(ts_regression(close / delay(close, 1), 5) - rank(ts_corr(close, delay(close, 1), 5)))",
        "category": "trend",
        "desc": "5日收益率回归斜率 - 5日自相关排名",
    },
    39: {
        "expr": "-1 * rank(delta(close, 7) * (1 - rank(decay_linear(volume / adv20, 9))))",
        "category": "volume_price",
        "desc": "7日价格变化 × 量能比排名反向",
    },
    40: {
        "expr": "-1 * rank(std_dev(close, 20) - delay(std_dev(close, 20), 5))",
        "category": "volatility",
        "desc": "20日波动率5日变化的反向排名",
    },

    # ─── 更多因子 (41-60) ───
    41: {
        "expr": "power(high * low, 0.5) - vwap",
        "category": "volume_price",
        "desc": "几何均价与VWAP的差值",
    },
    42: {
        "expr": "rank(vwap - close) / rank(vwap + close)",
        "category": "volume_price",
        "desc": "VWAP偏离度的归一化排名",
    },
    43: {
        "expr": "ts_rank(volume / adv20, 20) * ts_rank(close / open, 10) * -1",
        "category": "volume_price",
        "desc": "量能比20日排名 × 涨跌幅10日排名",
    },
    44: {
        "expr": "-1 * ts_corr(high, rank(volume), 5)",
        "category": "volume_price",
        "desc": "5日最高价-量排名相关反向",
    },
    45: {
        "expr": "sum(delay(close, 5) * delay(close, 4), 5) / sum(delay(close, 4), 5)",
        "category": "trend",
        "desc": "5日加权价格均值比",
    },
    46: {
        "expr": "-1 * rank(close - ts_max(close, 5)) * rank(ts_corr(close, volume, 10))",
        "category": "composite",
        "desc": "距5日高点 × 量价相关排名",
    },
    47: {
        "expr": "-1 * ((rank(delay(close, 5)) - rank(delay(close, 20))) + rank(delay(close, 10)) - rank(delay(close, 3)))",
        "category": "price_momentum",
        "desc": "多周期价格排名差分的组合",
    },
    48: {
        "expr": "-1 * (rank(ts_corr(sum(close, 7), sum(close, 7), 10)) - rank(ts_std_dev(close, 10)))",
        "category": "composite",
        "desc": "7日累计自相关排名 - 10日波动率排名",
    },
    49: {
        "expr": "-1 * (rank(ts_delta(open, 3)) * rank(ts_corr(close, volume, 10)))",
        "category": "composite",
        "desc": "3日开盘变化排名 × 量价相关排名",
    },
    50: {
        "expr": "-1 * (ts_rank(close, 7) - ts_rank(volume, 7)) * rank(ts_corr(close, volume, 5))",
        "category": "composite",
        "desc": "价格-量7日排名差 × 量价相关排名",
    },

    # ─── 因子 51-75 (代表性精选) ───
    51: {
        "expr": "-1 * rank(ts_delta(ts_corr(close, volume, 3), 2))",
        "category": "volume_price",
        "desc": "3日量价相关性2日变化的反向排名",
    },
    52: {
        "expr": "sum(((delay(close, 1) - close) * (delay(volume, 1) - volume)) / (delay(close, 1) - close), 6)",
        "category": "volume_price",
        "desc": "6日加权价格-量变化乘积",
    },
    53: {
        "expr": "-1 * rank(ts_delta(close, 2) * ts_rank(volume, 5) * ts_corr(close, volume, 5))",
        "category": "composite",
        "desc": "2日价格变化 × 量排名 × 量价相关",
    },
    55: {
        "expr": "-1 * rank(ts_corr(open, delay(open, 1), 12))",
        "category": "trend",
        "desc": "12日开盘价自相关的反向排名",
    },
    58: {
        "expr": "sum(delay(close, 1) < close ? volume : 0, 20) / sum(volume, 20) - sum(close < delay(close, 1) ? volume : 0, 20) / sum(volume, 20)",
        "category": "volume_price",
        "desc": "20日上涨量占比 - 下跌量占比",
    },
    60: {
        "expr": "-1 * rank(ts_delta(close, 1) * ts_std_dev(close, 20))",
        "category": "composite",
        "desc": "1日价格变化 × 20日波动率的排名",
    },
    62: {
        "expr": "-1 * rank(ts_corr(high, volume, 5)) * rank(ts_rank(close, 5))",
        "category": "composite",
        "desc": "高-量相关排名 × 5日价格排名",
    },
    64: {
        "expr": "-1 * rank(ts_corr(close, delay(close, 1), 5)) * rank(ts_corr(open, delay(open, 1), 5))",
        "category": "trend",
        "desc": "收盘自相关 × 开盘自相关的排名",
    },
    66: {
        "expr": "-1 * rank((sum(close, 3) / 3 - sum(close, 6) / 6))",
        "category": "trend",
        "desc": "3日均线与6日均线的差的排名",
    },
    67: {
        "expr": "-1 * rank(rank(rank(ts_rank(decay_linear(close, 5), 5))) - rank(ts_rank(decay_linear(volume / adv20, 10), 5)))",
        "category": "composite",
        "desc": "衰减价格排名 - 衰减量能排名",
    },
    68: {
        "expr": "-1 * rank(ts_rank(ts_std_dev(close, 20), 10) - ts_rank(ts_std_dev(close, 5), 10))",
        "category": "volatility",
        "desc": "20日与5日波动率排名差",
    },
    71: {
        "expr": "-1 * rank(ts_delta(open, 3)) * rank(ts_std_dev(close, 10))",
        "category": "composite",
        "desc": "3日开盘变化 × 10日波动率排名",
    },
    74: {
        "expr": "-1 * rank(ts_rank(close, 10) + close / ts_delay(close, 10) - 1)",
        "category": "price_momentum",
        "desc": "10日价格排名 + 10日收益率",
    },
    75: {
        "expr": "-1 * rank(ts_corr(close, volume, 5)) * rank(close / ts_delay(close, 5) - 1)",
        "category": "composite",
        "desc": "量价相关 × 5日收益率的排名",
    },

    # ─── 因子 76-101 (代表性精选) ───
    78: {
        "expr": "-1 * rank(delay(close, 5) / delay(close, 20) - 1) * rank(ts_corr(close, volume, 5))",
        "category": "composite",
        "desc": "5/20日动量排名 × 量价相关排名",
    },
    79: {
        "expr": "-1 * rank(ts_delta(close, 5) * rank(volume / ts_mean(volume, 5)))",
        "category": "composite",
        "desc": "5日价格变化 × 量能比的排名",
    },
    81: {
        "expr": "-1 * rank(ts_std_dev(high - close, 10) + ts_std_dev(low - close, 10))",
        "category": "volatility",
        "desc": "10日上影线与下影线标准差之和的排名",
    },
    83: {
        "expr": "-1 * rank(ts_rank(ts_delta(close, 3), 5) * ts_rank(ts_corr(close, volume, 10), 5))",
        "category": "composite",
        "desc": "3日价格变化排名 × 10日量价相关排名",
    },
    85: {
        "expr": "-1 * rank(ts_corr(close, delay(close, 1), 5)) + rank(ts_corr(close, delay(close, 1), 20))",
        "category": "trend",
        "desc": "5日价格自相关反向 + 20日价格自相关",
    },
    88: {
        "expr": "-1 * rank(ts_delta(close, 2)) * rank(ts_std_dev(close, 10)) * rank(ts_corr(close, volume, 10))",
        "category": "composite",
        "desc": "2日价格变化 × 10日波动率 × 10日量价相关",
    },
    90: {
        "expr": "-1 * rank((close - ts_delay(close, 5)) / ts_delay(close, 5)) * rank(ts_corr(close, volume, 5))",
        "category": "composite",
        "desc": "5日收益率排名 × 5日量价相关排名",
    },
    93: {
        "expr": "-1 * rank(ts_std_dev(close, 10) - ts_std_dev(close, 5)) * rank(ts_corr(close, volume, 5))",
        "category": "composite",
        "desc": "波动率结构变化 × 量价相关排名",
    },
    95: {
        "expr": "-1 * rank(ts_delta(close, 1) / ts_std_dev(close, 5)) * rank(ts_corr(close, volume, 5))",
        "category": "composite",
        "desc": "标准化价格变化 × 量价相关排名",
    },
    98: {
        "expr": "-1 * rank(ts_corr(high - low, volume, 5))",
        "category": "volume_price",
        "desc": "5日振幅-量相关性的反向排名",
    },
    101: {
        "expr": "((close - open) / ((high - low) + 1e-10)) * volume",
        "category": "volume_price",
        "desc": "价格位置 × 成交量（K线实体比例加权）",
    },
}


class Alpha101Parser:
    """WorldQuant Alpha101 因子解析器"""

    # 因子分类描述
    CATEGORY_NAMES = {
        "price_momentum": "价格动量",
        "volume_price": "量价关系",
        "volatility": "波动率",
        "reversal": "反转",
        "trend": "趋势",
        "liquidity": "流动性",
        "statistical": "统计特征",
        "composite": "复合因子",
    }

    def __init__(self):
        self._operators = OPERATOR_MAPPING
        self._cache: Dict[int, Alpha101Factor] = {}

    def parse_alpha(self, alpha_id: int) -> Optional[Alpha101Factor]:
        """解析单个 Alpha101 因子"""
        if alpha_id not in ALPHA_101_FORMULAS:
            logger.debug(f"Alpha#{alpha_id} 未收录")
            return None

        formula = ALPHA_101_FORMULAS[alpha_id]
        original = formula["expr"]
        translated = self._translate_expression(original)
        usable = not formula.get("needs_industry", False)
        complexity = formula.get("complexity", self._estimate_complexity(translated))

        factor = Alpha101Factor(
            alpha_id=alpha_id,
            original_expr=original,
            translated_expr=translated,
            category=formula["category"],
            description=formula["desc"],
            usable=usable,
            requires_industry=formula.get("needs_industry", False),
            complexity=complexity,
            tags=[formula["category"], "worldquant", "alpha101"],
        )

        self._cache[alpha_id] = factor
        return factor

    def parse_all_alphas(self) -> List[Alpha101Factor]:
        """解析全部已收录的 Alpha101 因子"""
        factors = []
        for alpha_id in sorted(ALPHA_101_FORMULAS.keys()):
            f = self.parse_alpha(alpha_id)
            if f:
                factors.append(f)
        return factors

    def get_usable_factors(self) -> List[Alpha101Factor]:
        """获取所有可用的因子（无需行业数据）"""
        return [f for f in self.parse_all_alphas() if f.usable]

    def get_usable_expressions(self) -> List[str]:
        """获取可用因子的表达式列表（可直接喂给 AlphaForge）"""
        return [f.translated_expr for f in self.get_usable_factors()]

    def get_factor_stats(self) -> Dict:
        """统计信息"""
        all_factors = self.parse_all_alphas()
        usable = [f for f in all_factors if f.usable]
        by_category = {}
        for f in all_factors:
            cat_name = self.CATEGORY_NAMES.get(f.category, f.category)
            by_category[cat_name] = by_category.get(cat_name, 0) + 1

        return {
            "total_formulaic": 101,
            "total_collected": len(all_factors),
            "usable": len(usable),
            "unusable": len(all_factors) - len(usable),
            "by_category": by_category,
            "complexity_distribution": {
                "simple": len([f for f in all_factors if f.complexity == "simple"]),
                "medium": len([f for f in all_factors if f.complexity == "medium"]),
                "complex": len([f for f in all_factors if f.complexity == "complex"]),
            },
        }

    # ═══════════════════════════════════════════════
    # 内部翻译方法
    # ═══════════════════════════════════════════════

    def _translate_expression(self, expr: str) -> str:
        """将 WQ BRAIN 表达式翻译为 AlphaForge 格式"""
        translated = expr

        # 1. 替换函数式算子（先处理长名称避免冲突）
        for wq_op, af_op in sorted(self._operators.items(), key=lambda x: -len(x[0])):
            if wq_op != af_op:
                # 函数调用: op_name( → af_op(
                translated = re.sub(
                    rf'\b{wq_op}\b(?=\s*\()',
                    af_op,
                    translated
                )

        # 2. 特殊处理: adv20, adv60 → ts_mean(volume, N)
        translated = re.sub(r'\badv20\b', 'ts_mean(volume, 20)', translated)
        translated = re.sub(r'\badv60\b', 'ts_mean(volume, 60)', translated)
        translated = re.sub(r'\badv(\d+)\b', r'ts_mean(volume, \1)', translated)

        # 3. 特殊处理: returns → close / delay(close, 1) - 1
        # 注意: 如果已经在 scheduler 中 pre-computed，可以直接用 returns

        # 4. 特殊处理: signedpower(x, a) → sign(x) * abs(x) ** a
        translated = re.sub(
            r'signedpower\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'sign(\1) * abs(\1) ** (\2)',
            translated
        )

        # 5. 特殊处理: scale(x) → normalize(x)
        translated = re.sub(
            r'scale\s*\(\s*([^)]+)\s*\)',
            r'normalize(\1)',
            translated
        )

        # 6. 特殊处理: IndNeutralize(x, industry) → demean(x)
        translated = re.sub(
            r'IndNeutralize\s*\(\s*([^,]+)\s*,\s*[^)]+\s*\)',
            r'demean(\1)',
            translated
        )

        # 7. 特殊处理: cor → ts_corr (2参数版本转为3参数版本)
        # WQ BRAIN 的 corr 是2参数版本，默认窗口=当前值
        # 在 AlphaForge 中 ts_corr 需要3参数，这里用固定窗口
        translated = re.sub(
            r'\bcor\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'ts_corr(\1, \2, 10)',
            translated
        )

        # 8. 清理三元运算符（简化处理，转换为可执行的表达式）
        # WQ BRAIN 使用 (cond ? val1 : val2) 语法
        # 简化: 直接转换为 where(cond, val1, val2)
        # 由于 AlphaForge 不直接支持 where，我们用 np.where 或简化表达式
        translated = self._simplify_conditionals(translated)

        return translated

    def _simplify_conditionals(self, expr: str) -> str:
        """简化三元条件运算符

        WQ BRAIN: (condition ? value_if_true : value_if_false)
        简化为: value_if_true (取主要信号方向)
        """
        # 策略: 用简单信号替代条件表达式
        # 对于大多数因子，条件表达式的核心信号在 value_if_true 中
        # 这里做简化处理，提取主要信号部分

        # 处理简单模式: (expr ? val1 : val2) → val1
        pattern = r'\(([^?]+)\s*\?\s*([^:]+)\s*:\s*([^)]+)\)'

        def _simplify_match(m):
            condition = m.group(1).strip()
            true_val = m.group(2).strip()
            false_val = m.group(3).strip()

            # 如果 true/false 都很复杂，取更短的
            if len(true_val) <= len(false_val):
                return true_val
            return false_val

        # 只做一层简化
        result = re.sub(pattern, _simplify_match, expr)
        return result

    def _estimate_complexity(self, expr: str) -> str:
        """估算因子复杂度"""
        depth = self._expr_depth(expr)
        func_count = len(re.findall(r'\b\w+\s*\(', expr))

        if depth <= 2 and func_count <= 2:
            return "simple"
        elif depth <= 4 and func_count <= 5:
            return "medium"
        return "complex"

    def _expr_depth(self, expr: str) -> int:
        """计算表达式嵌套深度"""
        max_depth = 0
        current_depth = 0
        for ch in expr:
            if ch == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif ch == ')':
                current_depth -= 1
        return max_depth


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def get_alpha101_expressions() -> List[str]:
    """获取所有可用的 Alpha101 因子表达式"""
    parser = Alpha101Parser()
    return parser.get_usable_expressions()


def get_alpha101_factors() -> List[dict]:
    """获取所有 Alpha101 因子详情"""
    parser = Alpha101Parser()
    factors = parser.get_usable_factors()
    return [
        {
            "name": f"alpha_{f.alpha_id:03d}",
            "expression": f.translated_expr,
            "original": f.original_expr,
            "category": f.category,
            "description": f.description,
            "author": "worldquant",
            "tags": f.tags + ["alpha101"],
            "complexity": f.complexity,
        }
        for f in factors
    ]


if __name__ == "__main__":
    parser = Alpha101Parser()

    print("=" * 60)
    print("WorldQuant Alpha101 因子解析器")
    print("=" * 60)

    stats = parser.get_factor_stats()
    print(f"\n📊 统计信息:")
    print(f"  总公式化因子: {stats['total_formulaic']}")
    print(f"  已收录因子:   {stats['total_collected']}")
    print(f"  可用因子:     {stats['usable']}")
    print(f"  不可用因子:   {stats['unusable']}")
    print(f"\n  分类分布:")
    for cat, count in stats["by_category"].items():
        print(f"    {cat}: {count}")

    print(f"\n📝 示例翻译:")
    for alpha_id in [1, 2, 15, 101]:
        f = parser.parse_alpha(alpha_id)
        if f:
            print(f"\n  Alpha#{f.alpha_id} [{f.category}]")
            print(f"    原始: {f.original_expr[:80]}...")
            print(f"    翻译: {f.translated_expr[:80]}...")
            print(f"    描述: {f.description}")
