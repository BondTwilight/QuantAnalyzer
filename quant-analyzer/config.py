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
    # ── Tier 1: 免费无Key ──
    "google-gemini": {
        "name": "Google Gemini 2.0 Flash",
        "tier": 1,
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key": os.getenv("GOOGLE_API_KEY", ""),
        "model": "gemini-2.0-flash",
        "env_key": "GOOGLE_API_KEY",
        "rate_limit": "15 RPM / 1M TPM",
        "needs_key": True,  # 需要免费Google AI Studio Key
        "key_url": "https://aistudio.google.com/apikey",
        "desc": "Google免费, 最强免费模型之一",
        "compatible": "openai",  # 兼容OpenAI SDK格式
    },
    "groq": {
        "name": "Groq (Llama 3.3 70B)",
        "tier": 1,
        "api_base": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "rate_limit": "30 RPM / 6K TPM",
        "needs_key": True,
        "key_url": "https://console.groq.com/keys",
        "desc": "超快推理速度, 免费额度慷慨",
        "compatible": "openai",
    },
    "cerebras": {
        "name": "Cerebras (Llama 3.3 70B)",
        "tier": 1,
        "api_base": "https://api.cerebras.ai/v1",
        "api_key": os.getenv("CEREBRAS_API_KEY", ""),
        "model": "llama-3.3-70b",
        "env_key": "CEREBRAS_API_KEY",
        "rate_limit": "免费无限制",
        "needs_key": True,
        "key_url": "https://cloud.cerebras.ai/",
        "desc": "免费无限制, 极速推理",
        "compatible": "openai",
    },
    "siliconflow": {
        "name": "SiliconFlow (Qwen 2.5 72B)",
        "tier": 1,
        "api_base": "https://api.siliconflow.cn/v1",
        "api_key": os.getenv("SILICONFLOW_API_KEY", ""),
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "env_key": "SILICONFLOW_API_KEY",
        "rate_limit": "14元/天免费额度",
        "needs_key": True,
        "key_url": "https://cloud.siliconflow.cn/",
        "desc": "国内聚合平台, 多模型可选",
        "compatible": "openai",
    },

    # ── Tier 2: 免费注册Key ──
    "zhipu": {
        "name": "智谱 GLM-4-Flash",
        "tier": 2,
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": os.getenv("ZHIPU_API_KEY", ""),
        "model": "glm-4-flash",
        "env_key": "ZHIPU_API_KEY",
        "rate_limit": "免费, 25 RPM",
        "needs_key": True,
        "key_url": "https://open.bigmodel.cn/",
        "desc": "国产免费, 中文理解强",
        "compatible": "openai",
    },
    "deepseek": {
        "name": "DeepSeek V3",
        "tier": 2,
        "api_base": "https://api.deepseek.com/v1",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "rate_limit": "新用户500万token免费",
        "needs_key": True,
        "key_url": "https://platform.deepseek.com/",
        "desc": "顶级推理能力, 性价比极高",
        "compatible": "openai",
    },
    "qwen": {
        "name": "通义千问 Qwen-Max",
        "tier": 2,
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
        "model": "qwen-max",
        "env_key": "DASHSCOPE_API_KEY",
        "rate_limit": "100万token免费/月",
        "needs_key": True,
        "key_url": "https://dashscope.console.aliyun.com/",
        "desc": "阿里通义, 中文强",
        "compatible": "openai",
    },
    "moonshot": {
        "name": "Moonshot / Kimi",
        "tier": 2,
        "api_base": "https://api.moonshot.cn/v1",
        "api_key": os.getenv("MOONSHOT_API_KEY", ""),
        "model": "moonshot-v1-8k",
        "env_key": "MOONSHOT_API_KEY",
        "rate_limit": "15元免费额度",
        "needs_key": True,
        "key_url": "https://platform.moonshot.cn/",
        "desc": "Kimi, 长文本处理强",
        "compatible": "openai",
    },
    "yi": {
        "name": "零一万物 Yi-Lightning",
        "tier": 2,
        "api_base": "https://api.lingyiwanwu.com/v1",
        "api_key": os.getenv("YI_API_KEY", ""),
        "model": "yi-lightning",
        "env_key": "YI_API_KEY",
        "rate_limit": "免费额度",
        "needs_key": True,
        "key_url": "https://platform.lingyiwanwu.com/",
        "desc": "零一万物, 李开复团队",
        "compatible": "openai",
    },
    "stepfun": {
        "name": "阶跃星辰 Step-1V",
        "tier": 2,
        "api_base": "https://api.stepfun.com/v1",
        "api_key": os.getenv("STEPFUN_API_KEY", ""),
        "model": "step-1-8k",
        "env_key": "STEPFUN_API_KEY",
        "rate_limit": "免费额度",
        "needs_key": True,
        "key_url": "https://platform.stepfun.com/",
        "desc": "阶跃星辰",
        "compatible": "openai",
    },
    "baichuan": {
        "name": "百川 Baichuan4",
        "tier": 2,
        "api_base": "https://api.baichuan-ai.com/v1",
        "api_key": os.getenv("BAICHUAN_API_KEY", ""),
        "model": "Baichuan4",
        "env_key": "BAICHUAN_API_KEY",
        "rate_limit": "免费额度",
        "needs_key": True,
        "key_url": "https://platform.baichuan-ai.com/",
        "desc": "百川智能",
        "compatible": "openai",
    },
    "minimax": {
        "name": "MiniMax abab7",
        "tier": 2,
        "api_base": "https://api.minimax.chat/v1",
        "api_key": os.getenv("MINIMAX_API_KEY", ""),
        "model": "abab7-chat",
        "env_key": "MINIMAX_API_KEY",
        "rate_limit": "免费额度",
        "needs_key": True,
        "key_url": "https://platform.minimaxi.com/",
        "desc": "MiniMax, 多模态强",
        "compatible": "openai",
    },
    "doubao": {
        "name": "豆包 (字节跳动)",
        "tier": 2,
        "api_base": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": os.getenv("DOUBAO_API_KEY", ""),
        "model": "doubao-pro-32k",
        "env_key": "DOUBAO_API_KEY",
        "rate_limit": "免费额度",
        "needs_key": True,
        "key_url": "https://console.volcengine.com/ark",
        "desc": "字节跳动豆包",
        "compatible": "openai",
    },
    "together": {
        "name": "Together AI",
        "tier": 2,
        "api_base": "https://api.together.xyz/v1",
        "api_key": os.getenv("TOGETHER_API_KEY", ""),
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
        "rate_limit": "$25免费额度",
        "needs_key": True,
        "key_url": "https://api.together.xyz/",
        "desc": "开源模型聚合, 免费额度多",
        "compatible": "openai",
    },
    "sambanova": {
        "name": "SambaNova",
        "tier": 2,
        "api_base": "https://api.sambanova.ai/v1",
        "api_key": os.getenv("SAMBANOVA_API_KEY", ""),
        "model": "Meta-Llama-3.3-70B-Instruct",
        "env_key": "SAMBANOVA_API_KEY",
        "rate_limit": "免费无限制",
        "needs_key": True,
        "key_url": "https://cloud.sambanova.ai/",
        "desc": "免费无限制, 高性能推理",
        "compatible": "openai",
    },

    # ── Tier 3: 付费/有限免费 ──
    "openai": {
        "name": "OpenAI GPT-4o-mini",
        "tier": 3,
        "api_base": "https://api.openai.com/v1",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "rate_limit": "付费",
        "needs_key": True,
        "key_url": "https://platform.openai.com/api-keys",
        "desc": "OpenAI官方",
        "compatible": "openai",
    },
    "claude": {
        "name": "Claude (via OpenRouter)",
        "tier": 3,
        "api_base": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "model": "anthropic/claude-3.5-sonnet",
        "env_key": "OPENROUTER_API_KEY",
        "rate_limit": "按量付费",
        "needs_key": True,
        "key_url": "https://openrouter.ai/keys",
        "desc": "Claude 3.5, 顶级推理",
        "compatible": "openai",
    },
}

# 默认使用的模型 (按优先级排序, 自动尝试)
DEFAULT_MODEL_PRIORITY = [
    "zhipu",        # 国产免费首选
    "groq",         # 国际免费首选
    "cerebras",     # 免费无限制
    "google-gemini",# Google免费
    "siliconflow",  # 国内聚合
    "deepseek",     # 推理强
    "sambanova",    # 免费无限制
    "qwen",         # 通义千问
    "moonshot",     # Kimi
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
