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
# 🤖 AI 多模型配置 — v4.0 全面升级
# ══════════════════════════════════════════════

# 免费模型层级：
#   Tier 1 — 无需Key，开箱即用
#   Tier 2 — 免费注册获取API Key
#   Tier 3 — 付费或有限免费额度

# ══════════════════════════════════════════════
# 🤖 AI 模型配置 — 已接入 4 家免费/低成本模型
# ══════════════════════════════════════════════

# 智谱API Key（已配置 ✅ 2026-04-04 更新）
ZHIPU_API_KEY = "c304b850fa0f4aabb2adc062a7804023.AsHe1BGNWJ3kbVgr"

# DeepSeek API Key（已配置 ✅ 2026-04-04 更新）
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-e0992c60751f49a0998397b28632d1e9")

# 硅基流动 API Key（已配置 ✅ 2026-04-04）
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-rmdmqfxevhyodfecqsbfswccxmmkjauuakbmwlhaarrmohhm")

# Ollama 本地模型（无需Key，需本地安装 ollama）
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

AI_MODELS = {
    # ═══ Tier 1: 智谱GLM（已配置Key，直接可用） ═══
    "glm-5": {
        "name": "🧠 智谱 GLM-5（旗舰）",
        "provider": "zhipu",
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
        "strengths": ["复杂推理", "策略分析", "代码生成"],
    },
    "glm-turbo": {
        "name": "⚡ 智谱 GLM-Turbo（快速）",
        "provider": "zhipu",
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
        "strengths": ["快速响应", "批量处理", "日常分析"],
    },

    # ═══ Tier 2: DeepSeek（极低成本，推荐） ═══
    "deepseek-v3": {
        "name": "🔥 DeepSeek V3（旗舰）",
        "provider": "deepseek",
        "tier": 2,
        "api_base": "https://api.deepseek.com",
        "api_key": DEEPSEEK_API_KEY,
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "rate_limit": "¥1/M tokens（极便宜）",
        "needs_key": True,
        "key_url": "https://platform.deepseek.com/",
        "desc": "国产旗舰！性价比最高，适合策略分析",
        "compatible": "openai",
        "recommended": True,
        "strengths": ["长上下文", "代码能力强", "成本极低"],
    },
    "deepseek-coder": {
        "name": "💻 DeepSeek Coder（代码）",
        "provider": "deepseek",
        "tier": 2,
        "api_base": "https://api.deepseek.com",
        "api_key": DEEPSEEK_API_KEY,
        "model": "deepseek-coder",
        "env_key": "DEEPSEEK_API_KEY",
        "rate_limit": "¥1/M tokens",
        "needs_key": True,
        "key_url": "https://platform.deepseek.com/",
        "desc": "代码专用！策略代码生成/优化极强",
        "compatible": "openai",
        "recommended": False,
        "strengths": ["代码生成", "策略实现", "Bug修复"],
    },

    # ═══ Tier 2: 硅基流动（聚合多模型） ═══
    "siliconflow-qwen": {
        "name": "🌊 硅基流动 Qwen（免费）",
        "provider": "siliconflow",
        "tier": 2,
        "api_base": "https://api.siliconflow.cn/v1",
        "api_key": SILICONFLOW_API_KEY,
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "env_key": "SILICONFLOW_API_KEY",
        "rate_limit": "免费额度每日可用",
        "needs_key": True,
        "key_url": "https://siliconflow.cn/",
        "desc": "免费额度！阿里Qwen72B大模型",
        "compatible": "openai",
        "recommended": False,
        "strengths": ["大模型", "免费额度", "中文理解"],
    },
    "siliconflow-deepseek": {
        "name": "🌊 硅基流动 DeepSeek（低价）",
        "provider": "siliconflow",
        "tier": 2,
        "api_base": "https://api.siliconflow.cn/v1",
        "api_key": SILICONFLOW_API_KEY,
        "model": "deepseek-ai/DeepSeek-V2.5",
        "env_key": "SILICONFLOW_API_KEY",
        "rate_limit": "¥0.5/M tokens",
        "needs_key": True,
        "key_url": "https://siliconflow.cn/",
        "desc": "低价好用的DeepSeek！聚合平台",
        "compatible": "openai",
        "recommended": False,
        "strengths": ["低价", "稳定", "多模型切换"],
    },

    # ═══ Tier 3: Ollama 本地模型（完全免费） ═══
    "ollama-qwen": {
        "name": "🏠 Ollama Qwen（本地）",
        "provider": "ollama",
        "tier": 3,
        "api_base": OLLAMA_BASE_URL,
        "api_key": "",  # 不需要Key
        "model": "qwen2.5:72b",
        "env_key": "OLLAMA_BASE_URL",
        "rate_limit": "本地运行，完全免费",
        "needs_key": False,
        "key_url": "https://ollama.com/",
        "desc": "本地部署！需要安装Ollama + 下载模型",
        "compatible": "ollama",
        "recommended": False,
        "strengths": ["完全免费", "隐私保护", "无API限制"],
    },
    "ollama-llama": {
        "name": "🏠 Ollama Llama（本地）",
        "provider": "ollama",
        "tier": 3,
        "api_base": OLLAMA_BASE_URL,
        "api_key": "",
        "model": "llama3.1:8b",
        "env_key": "OLLAMA_BASE_URL",
        "rate_limit": "本地运行，完全免费",
        "needs_key": False,
        "key_url": "https://ollama.com/",
        "desc": "本地部署！Meta开源Llama3.1",
        "compatible": "ollama",
        "recommended": False,
        "strengths": ["完全免费", "开源", "无限制调用"],
    },
}

# 默认使用的模型 (按优先级排序)
DEFAULT_MODEL_PRIORITY = [
    "glm-turbo",      # ⚡ 日常分析用快速模型（已配置Key）
    "deepseek-v3",    # 🔥 DeepSeek旗舰（需配置Key，极便宜）
    "glm-5",          # 🧠 复杂分析用旗舰模型
]

# 协同分析配置: 哪些任务用哪些模型
ANALYSIS_TASKS = {
    "strategy_code_parse": {
        "description": "策略代码解析",
        "models": ["glm-turbo", "deepseek-coder"],
        "temperature": 0.3,
    },
    "backtest_analysis": {
        "description": "回测结果分析",
        "models": ["glm-turbo", "deepseek-v3"],
        "temperature": 0.5,
    },
    "strategy_comparison": {
        "description": "策略对比",
        "models": ["glm-5", "deepseek-v3"],
        "temperature": 0.4,
    },
    "strategy_generate": {
        "description": "策略代码生成",
        "models": ["deepseek-coder", "glm-5"],
        "temperature": 0.8,
    },
    "strategy_optimize": {
        "description": "策略优化",
        "models": ["deepseek-v3", "glm-5"],
        "temperature": 0.6,
    },
    "market_sentiment": {
        "description": "市场研判",
        "models": ["glm-turbo", "deepseek-v3"],
        "temperature": 0.6,
    },
    "auto_learning": {
        "description": "自学习进化",
        "models": ["glm-5", "deepseek-v3"],
        "temperature": 0.8,
    },
    "investment_advice": {
        "description": "投资建议",
        "models": ["glm-5"],
        "temperature": 0.3,
    },
    "stock_diagnosis": {
        "description": "AI诊断股票",
        "models": ["glm-turbo", "deepseek-v3"],
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
