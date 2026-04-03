"""
全局配置 — QuantAnalyzer v3.0
AI多模型 + 策略库 + 智能分析
"""
import os
from pathlib import Path

# ── 项目路径 ──
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
UPLOADS_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "quant_analyzer.db"
STRATEGY_LIBRARY_DIR = BASE_DIR / "strategy_library"

# ── 回测参数 ──
INITIAL_CASH = 100_000          # 初始资金 10万
BENCHMARK = "000300.SH"         # 沪深300
DEFAULT_PERIOD = 3650           # 默认回测天数 (约10年)
COMMISSION = 0.0003             # 佣金 万三
STAMP_TAX = 0.001               # 印花税 千一
SLIPPAGE = 0.001                # 滑点 千一

# ── 数据源配置 ──
STOCK_POOL = [
    "000001.SZ",  # 平安银行
    "000002.SZ",  # 万科A
    "000333.SZ",  # 美的集团
    "000568.SZ",  # 泸州老窖
    "000651.SZ",  # 格力电器
    "000858.SZ",  # 五粮液
    "002594.SZ",  # 比亚迪
    "600036.SH",  # 招商银行
    "600276.SH",  # 恒瑞医药
    "600309.SH",  # 万华化学
    "600519.SH",  # 贵州茅台
    "600887.SH",  # 伊利股份
    "601318.SH",  # 中国平安
    "601888.SH",  # 中国中免
    "603259.SH",  # 药明康德
]

# ── 行业分类 ──
SECTORS = {
    "银行": ["000001.SZ", "600036.SH", "601398.SH", "601939.SH"],
    "白酒": ["000568.SZ", "000858.SZ", "600519.SH", "002304.SZ"],
    "医药": ["600276.SH", "603259.SH", "300760.SZ", "000538.SZ"],
    "消费": ["600887.SH", "000333.SZ", "000651.SZ", "601888.SH"],
    "科技": ["002594.SZ", "300750.SZ", "002415.SZ", "600588.SH"],
    "新能源": ["002594.SZ", "300750.SZ", "601012.SH", "002129.SZ"],
}

# ══════════════════════════════════════════════
# 🤖 AI 多模型配置 — v3.0 核心升级
# ══════════════════════════════════════════════

# 免费模型层级：
#   Tier 1 — 无需Key，开箱即用（部分需HF Token）
#   Tier 2 — 需要免费注册获取API Key
#   Tier 3 — 付费或有限免费额度

# ══════════════════════════════════════════════
# 🤖 AI 模型配置 — 已接入智谱GLM
# ══════════════════════════════════════════════

# 智谱API Key（已配置）
ZHIPU_API_KEY = "f73b954ee7ea4e5e9f524130827628c7.pH5VtxD5rUe71JzQ"

AI_MODELS = {
    # ═══ 主力模型: 智谱GLM（已配置Key，直接可用） ═══
    "glm-5": {
        "name": "🧠 智谱 GLM-5（旗舰）",
        "tier": 1,
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": ZHIPU_API_KEY,
        "model": "glm-5",
        "env_key": "ZHIPU_API_KEY",
        "rate_limit": "200K上下文，128K输出",
        "needs_key": False,
        "key_url": "https://open.bigmodel.cn/",
        "desc": "旗舰模型！复杂分析/策略审查用",
        "compatible": "openai",
        "recommended": True,
    },
    "glm-turbo": {
        "name": "⚡ 智谱 GLM-Turbo（快速）",
        "tier": 1,
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": ZHIPU_API_KEY,
        "model": "glm-4-flash",
        "env_key": "ZHIPU_API_KEY",
        "rate_limit": "免费，25 RPM",
        "needs_key": False,
        "key_url": "https://open.bigmodel.cn/",
        "desc": "快速模型！日常分析/批量任务用",
        "compatible": "openai",
        "recommended": True,
    },
}

# 默认使用的模型 (按优先级排序)
DEFAULT_MODEL_PRIORITY = [
    "glm-turbo",    # ⚡ 日常分析用快速模型（免费）
    "glm-5",       # 🧠 复杂分析用旗舰模型
]

# 协同分析配置: 哪些任务用哪些模型
ANALYSIS_TASKS = {
    "strategy_code_parse": {
        "description": "策略代码解析",
        "models": ["glm-turbo"],
        "temperature": 0.3,
    },
    "backtest_analysis": {
        "description": "回测结果分析",
        "models": ["glm-turbo"],
        "temperature": 0.5,
    },
    "strategy_comparison": {
        "description": "策略对比",
        "models": ["glm-5"],
        "temperature": 0.4,
    },
    "market_sentiment": {
        "description": "市场研判",
        "models": ["glm-turbo"],
        "temperature": 0.6,
    },
    "auto_learning": {
        "description": "自学习进化",
        "models": ["glm-5"],
        "temperature": 0.8,
    },
    "investment_advice": {
        "description": "投资建议",
        "models": ["glm-5"],
        "temperature": 0.3,
    },
}

# ── 策略库配置 ──
STRATEGY_CATEGORIES = {
    "趋势跟踪": ["ma_cross", "macd", "dual_thrust", "turtle", "donchian", "breakout"],
    "均值回归": ["bollinger", "mean_reversion", "rsi_strategy", "pair_trading"],
    "动量因子": ["momentum", "sector_momentum", "factor_timing"],
    "多因子": ["multi_factor", "small_cap", "value_invest"],
    "技术指标": ["vwap", "obv", "ichimoku", "supertrend"],
    "事件驱动": ["earnings", "dividend", "rebalance"],
}

# ── 调度配置 ──
SCHEDULER_CRON = "30 15 * * 1-5"  # 工作日 15:30 自动回测

# ── 页面配置 ──
PAGE_CONFIG = {
    "page_title": "QuantAnalyzer v3.0 - 量化策略AI学习平台",
    "page_icon": "🧠",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# ── 主题色 ──
THEME_COLORS = {
    "primary": "#1a73e8",
    "success": "#28a745",
    "danger": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8",
    "dark": "#1a1a2e",
}

# ── 兼容旧版配置 ──
AI_PROVIDERS = AI_MODELS
DEFAULT_AI_PROVIDER = DEFAULT_MODEL_PRIORITY[0] if DEFAULT_MODEL_PRIORITY else "zhipu"
