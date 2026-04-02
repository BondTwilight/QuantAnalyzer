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

AI_MODELS = {
    # ═══ 精选Tier 1: 完全免费无限制 ═══
    "cerebras": {
        "name": "🔥 Cerebras (Llama 3.3 70B)",
        "tier": 1,
        "api_base": "https://api.cerebras.ai/v1",
        "api_key": os.getenv("CEREBRAS_API_KEY", ""),
        "model": "llama-3.3-70b",
        "env_key": "CEREBRAS_API_KEY",
        "rate_limit": "✅ 完全免费无限制",
        "needs_key": True,
        "key_url": "https://cloud.cerebras.ai/",
        "desc": "免费无限制! 极速推理70B大模型",
        "compatible": "openai",
        "recommended": True,
    },
    
    # ═══ 精选Tier 2: 免费注册可用 ═══
    "zhipu": {
        "name": "⭐ 智谱 GLM-4-Flash (推荐)",
        "tier": 2,
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": os.getenv("ZHIPU_API_KEY", ""),
        "model": "glm-4-flash",
        "env_key": "ZHIPU_API_KEY",
        "rate_limit": "免费, 25 RPM",
        "needs_key": True,
        "key_url": "https://open.bigmodel.cn/",
        "desc": "国产首选! 中文理解强，免费额度",
        "compatible": "openai",
        "recommended": True,
    },
    "groq": {
        "name": "⚡ Groq (Llama 3.3 70B)",
        "tier": 2,
        "api_base": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "rate_limit": "30 RPM / 6K TPM",
        "needs_key": True,
        "key_url": "https://console.groq.com/keys",
        "desc": "超快推理! 免费额度慷慨",
        "compatible": "openai",
        "recommended": True,
    },
    "siliconflow": {
        "name": "🇨🇳 SiliconFlow (Qwen 2.5)",
        "tier": 2,
        "api_base": "https://api.siliconflow.cn/v1",
        "api_key": os.getenv("SILICONFLOW_API_KEY", ""),
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "env_key": "SILICONFLOW_API_KEY",
        "rate_limit": "14元/天免费额度",
        "needs_key": True,
        "key_url": "https://cloud.siliconflow.cn/",
        "desc": "国内首选! 多模型可选",
        "compatible": "openai",
        "recommended": False,
    },
    "deepseek": {
        "name": "🧠 DeepSeek V3",
        "tier": 2,
        "api_base": "https://api.deepseek.com/v1",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "rate_limit": "新用户500万token免费",
        "needs_key": True,
        "key_url": "https://platform.deepseek.com/",
        "desc": "推理能力强! 新用户送大量额度",
        "compatible": "openai",
        "recommended": False,
    },
    
    # ═══ Tier 3: 高级付费模型 ═══
    "google-gemini": {
        "name": "🤖 Google Gemini 2.0 Flash",
        "tier": 3,
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key": os.getenv("GOOGLE_API_KEY", ""),
        "model": "gemini-2.0-flash",
        "env_key": "GOOGLE_API_KEY",
        "rate_limit": "15 RPM / 1M TPM",
        "needs_key": True,
        "key_url": "https://aistudio.google.com/apikey",
        "desc": "Google免费! 最强免费模型之一",
        "compatible": "openai",
        "recommended": False,
    },
    "openai": {
        "name": "💎 OpenAI GPT-4o-mini",
        "tier": 3,
        "api_base": "https://api.openai.com/v1",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "rate_limit": "付费",
        "needs_key": True,
        "key_url": "https://platform.openai.com/api-keys",
        "desc": "OpenAI官方! 顶级推理能力",
        "compatible": "openai",
        "recommended": False,
    },
}

# 默认使用的模型 (按优先级排序, 自动尝试)
DEFAULT_MODEL_PRIORITY = [
    "cerebras",     # 🔥 完全免费无限制首选
    "zhipu",        # ⭐ 国产免费首选
    "groq",         # ⚡ 超快推理
    "siliconflow",  # 🇨🇳 国内首选
    "deepseek",     # 🧠 推理能力强
]

# 协同分析配置: 哪些任务用哪些模型
ANALYSIS_TASKS = {
    "strategy_code_parse": {
        "description": "策略代码解析",
        "models": ["zhipu", "deepseek", "groq"],  # 3模型并行
        "temperature": 0.3,
    },
    "backtest_analysis": {
        "description": "回测结果分析",
        "models": ["deepseek", "google-gemini", "qwen"],  # 深度分析
        "temperature": 0.5,
    },
    "strategy_comparison": {
        "description": "策略对比",
        "models": ["zhipu", "groq", "moonshot"],
        "temperature": 0.4,
    },
    "market_sentiment": {
        "description": "市场情绪分析",
        "models": ["deepseek", "qwen", "moonshot"],
        "temperature": 0.6,
    },
    "auto_learning": {
        "description": "自学习进化",
        "models": ["deepseek", "google-gemini", "qwen"],
        "temperature": 0.8,
    },
    "investment_advice": {
        "description": "投资建议",
        "models": ["deepseek", "google-gemini"],
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
