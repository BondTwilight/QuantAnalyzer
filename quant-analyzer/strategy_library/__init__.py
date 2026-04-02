"""
QuantAnalyzer 策略库注册表
包含所有内置策略的元数据
"""
import importlib
import inspect
import backtrader as bt
from pathlib import Path

STRATEGY_LIBRARY = {
    # ═══ 趋势跟踪 ═══
    "dual_thrust": {
        "name": "DualThrust",
        "name_cn": "DualThrust区间突破",
        "category": "趋势跟踪",
        "difficulty": "⭐⭐",
        "description": "经典日内区间突破策略，通过N日内最高价-收盘价和收盘价-N日内最低价的较大值构建上下轨。适合趋势行情。",
        "params": {
            "kup": 0.5, "kdown": 0.5, "period": 2,
        },
        "source": "聚宽经典",
        "suitable": "趋势明显的市场",
        "annual_expected": "15-30%",
    },
    "turtle": {
        "name": "Turtle",
        "name_cn": "海龟交易法则",
        "category": "趋势跟踪",
        "difficulty": "⭐⭐",
        "description": "经典趋势跟踪策略，使用N日突破作为入场信号，分批建仓，配合ATR止损。40年验证有效。",
        "params": {
            "period_entry": 20, "period_exit": 10, "atr_period": 20,
        },
        "source": "经典海外策略",
        "suitable": "趋势明显的市场",
        "annual_expected": "20-40%",
    },
    "ma_cross": {
        "name": "MACross",
        "name_cn": "均线金叉死叉",
        "category": "趋势跟踪",
        "difficulty": "⭐",
        "description": "最简单的趋势策略：短期均线上穿长期均线买入，下穿卖出。参数少，易理解。",
        "params": {"fast": 5, "slow": 20},
        "source": "内置基础",
        "suitable": "趋势明显的市场",
        "annual_expected": "5-15%",
    },
    "macd": {
        "name": "MACDStrategy",
        "name_cn": "MACD趋势策略",
        "category": "趋势跟踪",
        "difficulty": "⭐⭐",
        "description": "使用MACD指标的金叉死叉作为交易信号，过滤假突破。",
        "params": {"fast": 12, "slow": 26, "signal": 9},
        "source": "内置基础",
        "suitable": "趋势明显的市场",
        "annual_expected": "8-20%",
    },
    "bollinger": {
        "name": "BollingerBands",
        "name_cn": "布林带均值回归",
        "category": "均值回归",
        "difficulty": "⭐⭐",
        "description": "价格触及布林带下轨买入，上轨卖出。经典均值回归策略。",
        "params": {"period": 20, "devfactor": 2.0},
        "source": "内置基础",
        "suitable": "震荡市场",
        "annual_expected": "10-20%",
    },
    "rsi_strategy": {
        "name": "RSIStrategy",
        "name_cn": "RSI超买超卖",
        "category": "均值回归",
        "difficulty": "⭐",
        "description": "RSI低于30超卖买入，高于70超买卖出。简单有效的震荡策略。",
        "params": {"period": 14, "lower": 30, "upper": 70},
        "source": "内置基础",
        "suitable": "震荡市场",
        "annual_expected": "8-18%",
    },
    "momentum": {
        "name": "Momentum",
        "name_cn": "动量策略",
        "category": "动量因子",
        "difficulty": "⭐",
        "description": "追涨杀跌策略：过去N日收益率为正则持有，负则空仓。",
        "params": {"period": 20},
        "source": "内置基础",
        "suitable": "趋势明显的市场",
        "annual_expected": "10-25%",
    },
    "multi_factor": {
        "name": "MultiFactor",
        "name_cn": "多因子策略",
        "category": "多因子",
        "difficulty": "⭐⭐⭐",
        "description": "综合PE、PB、ROE、MACD多因子选股，结合动量择时。",
        "params": {"pe_limit": 50, "pb_limit": 5, "roe_min": 5},
        "source": "内置高级",
        "suitable": "价值+趋势市场",
        "annual_expected": "15-30%",
    },
    "sector_rotation": {
        "name": "SectorRotation",
        "name_cn": "板块轮动策略",
        "category": "动量因子",
        "difficulty": "⭐⭐",
        "description": "跟踪行业动量，每月轮动到近期最强板块。",
        "params": {"lookback": 60, "top_n": 3},
        "source": "内置高级",
        "suitable": "风格轮动市场",
        "annual_expected": "12-25%",
    },
    # ═══ 新增策略 ═══
    "mean_reversion": {
        "name": "MeanReversion",
        "name_cn": "均值回归策略",
        "category": "均值回归",
        "difficulty": "⭐⭐",
        "description": "基于布林带和RSI的均值回归策略，价格偏离均线超过2倍标准差时反向操作。",
        "params": {"period": 20, "dev": 2.0, "rsi_period": 14, "rsi_buy": 30, "rsi_sell": 70},
        "source": "GitHub精选",
        "suitable": "震荡市场",
        "annual_expected": "12-22%",
    },
    "pair_trading": {
        "name": "PairTrading",
        "name_cn": "配对交易策略",
        "category": "均值回归",
        "difficulty": "⭐⭐⭐",
        "description": "监控两只高度相关股票的价格差，当差价偏离均值超过阈值时做多低估、做空高估。",
        "params": {"lookback": 60, "entry_threshold": 2.0, "exit_threshold": 0.5},
        "source": "统计套利经典",
        "suitable": "高度相关资产",
        "annual_expected": "8-15%",
    },
    "vwap": {
        "name": "VWAPStrategy",
        "name_cn": "VWAP动态平衡",
        "category": "技术指标",
        "difficulty": "⭐⭐",
        "description": "当价格低于VWAP时买入，高于时卖出，配合成交量确认。适合日内交易。",
        "params": {"vwap_period": 14, "volume_factor": 1.5},
        "source": "日内交易经典",
        "suitable": "日内/短线",
        "annual_expected": "10-20%",
    },
    "factor_timing": {
        "name": "FactorTiming",
        "name_cn": "因子择时策略",
        "category": "多因子",
        "difficulty": "⭐⭐⭐",
        "description": "综合动量、价值、波动率因子，根据因子综合得分调整仓位。",
        "params": {"mom_period": 60, "val_period": 120, "vol_period": 20},
        "source": "quant因子研究",
        "suitable": "多市场环境",
        "annual_expected": "12-25%",
    },
    "vol_breakout": {
        "name": "VolatilityBreakout",
        "name_cn": "波动率突破策略",
        "category": "趋势跟踪",
        "difficulty": "⭐⭐",
        "description": "当波动率放大时顺势交易，使用ATR衡量波动，配合N日突破确认。",
        "params": {"atr_period": 14, "breakout_period": 20, "atr_multiplier": 2.0},
        "source": "波动率交易",
        "suitable": "趋势+高波动市场",
        "annual_expected": "15-30%",
    },
    "obv_trend": {
        "name": "OBVTrend",
        "name_cn": "OBV量价趋势",
        "category": "技术指标",
        "difficulty": "⭐⭐",
        "description": "基于能量潮指标OBV的趋势跟踪策略，配合均线过滤假信号。",
        "params": {"obv_period": 20, "ma_period": 30},
        "source": "量价分析经典",
        "suitable": "趋势明显的市场",
        "annual_expected": "10-20%",
    },
    "donchian": {
        "name": "DonchianChannel",
        "name_cn": "唐奇安通道策略",
        "category": "趋势跟踪",
        "difficulty": "⭐",
        "description": "价格突破N日最高价买入，跌破N日最低价卖出。海龟交易的简化版。",
        "params": {"period": 20},
        "source": "海龟变体",
        "suitable": "趋势明显的市场",
        "annual_expected": "15-35%",
    },
    "supertrend": {
        "name": "Supertrend",
        "name_cn": "超级趋势线策略",
        "category": "趋势跟踪",
        "difficulty": "⭐⭐",
        "description": "使用超级趋势指标，趋势向上时做多，向下时做空，结合波动率自适应参数。",
        "params": {"period": 10, "multiplier": 3.0},
        "source": "MT4经典指标",
        "suitable": "趋势明显的市场",
        "annual_expected": "12-25%",
    },
    "small_cap_quant": {
        "name": "SmallCapQuant",
        "name_cn": "小市值量化策略",
        "category": "多因子",
        "difficulty": "⭐⭐⭐",
        "description": "按市值从小到大排序，选取最小10%的股票，等权配置，每月轮换。叠加动量和价值过滤。",
        "params": {"top_pct": 0.10, "momentum_days": 60, "rebalance_months": 1},
        "source": "聚宽研究精选",
        "suitable": "A股小市值风格",
        "annual_expected": "20-50%",
    },
    "cci_reversal": {
        "name": "CCIReversal",
        "name_cn": "CCI超买超卖反转",
        "category": "均值回归",
        "difficulty": "⭐⭐",
        "description": "使用CCI商品通道指标，CCI<-100超卖买入，CCI>+100超买卖出。",
        "params": {"period": 14, "buy_threshold": -100, "sell_threshold": 100},
        "source": "商品期货经典",
        "suitable": "震荡市场",
        "annual_expected": "10-20%",
    },
    "ichimoku": {
        "name": "IchimokuCloud",
        "name_cn": "一目均衡表策略",
        "category": "趋势跟踪",
        "difficulty": "⭐⭐⭐",
        "description": "基于日本Ichimoku Kinko Hyo系统，使用基准线、转换线、云层突破作为信号。",
        "params": {"tenkan": 9, "kijun": 26, "senkou_b": 52},
        "source": "日本技术分析经典",
        "suitable": "中长期趋势",
        "annual_expected": "12-25%",
    },
}


def get_all_strategies():
    """返回所有策略的元数据列表"""
    return list(STRATEGY_LIBRARY.values())


def get_strategy_by_category(category: str):
    """按分类获取策略"""
    return [s for s in STRATEGY_LIBRARY.values() if s["category"] == category]


def get_strategy_meta(name: str):
    """获取单个策略的元数据"""
    return STRATEGY_LIBRARY.get(name)


def list_categories():
    """列出所有策略分类"""
    cats = {}
    for meta in STRATEGY_LIBRARY.values():
        cat = meta["category"]
        if cat not in cats:
            cats[cat] = []
        cats[cat].append(meta["name"])
    return cats
