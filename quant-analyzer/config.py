"""
全局配置 — 量化策略分析平台
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

# ── AI分析配置 ──
AI_PROVIDERS = {
    "zhipu": {
        "name": "智谱AI (免费)",
        "api_base": os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4"),
        "api_key": os.getenv("ZHIPU_API_KEY", ""),
        "model": "glm-4-flash",  # 免费模型
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_base": os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
    },
    "openai": {
        "name": "OpenAI",
        "api_base": os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "gpt-4o-mini",
    },
}
DEFAULT_AI_PROVIDER = "zhipu"

# ── 调度配置 ──
SCHEDULER_CRON = "30 15 * * 1-5"  # 工作日 15:30 自动回测

# ── 页面配置 ──
PAGE_CONFIG = {
    "page_title": "QuantAnalyzer - 量化策略分析平台",
    "page_icon": "📊",
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
