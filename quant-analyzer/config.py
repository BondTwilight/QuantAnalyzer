"""
全局配置 — QuantBrain AlphaForge
精简版：只保留全自动进化引擎所需的配置
"""

import os
from pathlib import Path

# ── 项目路径 ──
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ── 回测参数 ──
INITIAL_CASH = 100_000          # 初始资金 10万
BENCHMARK = "000300.SH"         # 沪深300
DEFAULT_PERIOD = 3650           # 默认回测天数 (约10年)
COMMISSION = 0.0003             # 佣金 万三
STAMP_TAX = 0.001               # 印花税 千一
SLIPPAGE = 0.001                # 滑点 千一

# ── 股票池（用于多股票截面因子评估） ──
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

# ── AI 模型配置（LLM 用于策略知识提取和情报分析） ──

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "c304b850fa0f4aabb2adc062a7804023.AsHe1BGNWJ3kbVgr")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-e0992c60751f49a0998397b28632d1e9")
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-rmdmqfxevhyodfecqsbfswccxmmkjauuakbmwlhaarrmohhm")

AI_MODELS = {
    "glm-5": {
        "name": "🧠 智谱 GLM-5（旗舰）",
        "provider": "zhipu",
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": ZHIPU_API_KEY,
        "model": "glm-5",
        "compatible": "openai",
        "recommended": True,
    },
    "glm-turbo": {
        "name": "⚡ 智谱 GLM-Turbo（快速）",
        "provider": "zhipu",
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": ZHIPU_API_KEY,
        "model": "glm-4-flash",
        "compatible": "openai",
        "recommended": True,
    },
    "deepseek-v3": {
        "name": "🔥 DeepSeek V3",
        "provider": "deepseek",
        "api_base": "https://api.deepseek.com",
        "api_key": DEEPSEEK_API_KEY,
        "model": "deepseek-chat",
        "compatible": "openai",
        "recommended": True,
    },
}

DEFAULT_MODEL_PRIORITY = ["glm-turbo", "deepseek-v3", "glm-5"]

# ── 页面配置 ──
PAGE_CONFIG = {
    "page_title": "🧬 QuantBrain 智能量化进化平台",
    "page_icon": "🧬",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# ── 兼容旧引用 ──
AI_PROVIDERS = AI_MODELS
DEFAULT_AI_PROVIDER = DEFAULT_MODEL_PRIORITY[0]
