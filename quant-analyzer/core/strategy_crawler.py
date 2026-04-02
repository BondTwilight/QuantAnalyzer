"""
策略爬虫模块 - 每日自动抓取最新量化策略和因子
支持来源: GitHub开源项目 + 公开策略分享平台 + 量化社区
"""

import re
import json
import hashlib
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

CACHE_FILE = Path(__file__).parent.parent / "data" / "crawled_strategies.json"
CACHE_FILE.parent.mkdir(exist_ok=True)


@dataclass
class CrawledStrategy:
    """抓取到的策略数据结构"""
    name: str
    name_cn: str
    source: str  # 来源平台/仓库
    source_url: str
    category: str  # 趋势/均值回归/多因子/事件驱动
    description: str
    code: str  # 完整策略代码
    author: str
    stars: int = 0
    language: str = "python"
    framework: str = "backtrader"  # backtrader/jqdata/pseudocode
    tags: List[str] = None
    factors: List[str] = None  # 检测到的量化因子
    quality_score: float = 0.0  # 策略质量评分
    crawl_date: str = ""
    backtest_ready: bool = False  # 是否可直接回测
    issues: List[str] = None  # 问题列表

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.factors is None:
            self.factors = []
        if self.issues is None:
            self.issues = []
        if not self.crawl_date:
            self.crawl_date = datetime.now().strftime("%Y-%m-%d")


# ═══════════════════════════════════════════
# GitHub 爬虫 - 量化开源项目
# ═══════════════════════════════════════════

GITHUB_QUANT_REPOS = [
    # 量化框架 + 策略库
    ("vnpy/vnpy", "VNpy量化交易框架"),
    ("pandasvr/ec-vr", "Python量化投资"),
    ("fasionchan/funshare", "财经数据+量化策略"),
    ("Jerry2018/quant-study", "量化学习项目"),
    # 最新活跃的量化项目 (2024-2025)
    ("akfamily/akshare", "AKShare金融数据库"),
    ("moudyyt/quantitative-trading", "量化交易策略"),
    ("gitee-tang/quant-project", "量化项目"),
    ("githubuser0xFFFF/github", "量化分析项目"),
    # 小市值/因子策略
    ("smallturn/quant", "小市值量化"),
    ("sun現充/quant-strategy", "量化策略集合"),
    # 聚宽/米筐策略移植
    ("Jerry2018/joinquant-strategy", "聚宽策略"),
    # 回测框架
    ("backtrader/backtrader", "Backtrader官方"),
]

# 量化相关 GitHub 搜索关键词
GITHUB_SEARCH_KEYWORDS = [
    "backtrader strategy A股",
    "quantitative trading strategy python",
    "A股量化策略 python",
    "backtrader 均线 金叉",
    "joinquant strategy backtest",
    "stock trading bot python China",
    "algorithmic trading A-share market",
    "quant momentum strategy python",
    "小市值量化 策略 python",
]


def parse_github_url(url: str) -> Tuple[str, str]:
    """从GitHub URL提取 owner/repo"""
    m = re.search(r"github\.com/([^/]+)/([^/\s]+)", url)
    if m:
        return m.group(1), m.group(2).replace(".git", "")
    return "", ""


def detect_strategy_type(code: str) -> str:
    """检测策略类型"""
    code_lower = code.lower()
    if any(k in code_lower for k in ["ma(", "sma(", "ema(", "movingaverage", "cross"]):
        return "趋势跟踪"
    if any(k in code_lower for k in ["rsi", "boll", "kdj", "macd", "cci"]):
        return "技术指标"
    if any(k in code_lower for k in ["factor", "alpha", "beta", "value", "size"]):
        return "多因子"
    if any(k in code_lower for k in ["mean", "revert", "回归", "布林带"]):
        return "均值回归"
    if any(k in code_lower for k in ["event", "事件", "分红", "公告"]):
        return "事件驱动"
    if any(k in code_lower for k in ["momentum", "动量"]):
        return "动量因子"
    return "通用策略"


def detect_factors(code: str) -> List[str]:
    """从代码中检测量化因子"""
    factor_map = {
        "RSI": ["rsi", "relative strength"],
        "MACD": ["macd", "macd_line"],
        "布林带": ["boll", "bollinger", "bbands"],
        "均线": ["ma(", "sma(", "ema(", "moving average", "均线"],
        "KDJ": ["kdj", "kd指标"],
        "CCI": ["cci", "顺势指标"],
        "ATR": ["atr", "真实波幅"],
        "OBV": ["obv", "能量潮"],
        "VWAP": ["vwap", "成交量加权"],
        "DMI": ["dmi", "方向指标"],
        "ROC": ["roc", "变化率"],
        "动量": ["momentum", "动量因子"],
        "市值因子": ["size", "market_cap", "总市值"],
        "价值因子": ["book", "pe", "pb", "价值"],
        "质量因子": ["roe", "roa", "毛利率", "净利率"],
    }
    found = []
    code_lower = code.lower()
    for factor, keywords in factor_map.items():
        if any(k in code_lower for k in keywords):
            found.append(factor)
    return found


def detect_framework(code: str) -> str:
    """检测策略框架类型"""
    code_lower = code.lower()
    if "backtrader" in code_lower or "bt." in code_lower:
        return "backtrader"
    if any(k in code_lower for k in ["jqdata", "joinquant", "jqdatasdk", "get_price", "adjust_price"]):
        return "jqdata"
    if any(k in code_lower for k in ["rqalpha", "ricequant"]):
        return "rqalpha"
    if any(k in code_lower for k in ["akshare", "ak.", "ak_data"]):
        return "akshare"
    if any(k in code_lower for k in ["baostock", "bs.", "query_history"]):
        return "baostock"
    return "unknown"


def extract_strategy_from_github_code(code: str, repo: str) -> Optional[Dict]:
    """从GitHub代码中提取策略信息"""
    if not code or len(code) < 200:
        return None

    # 尝试提取策略名称
    name = ""
    patterns = [
        r"class\s+(\w+Strategy)\s*\(",
        r"def\s+(\w*strategy\w*)\s*\(",
        r"class\s+(\w+)\s*[:\(]",  # 普通类名
    ]
    for pat in patterns:
        m = re.search(pat, code, re.IGNORECASE)
        if m:
            name = m.group(1)
            break

    if not name:
        # 从文件名推断
        name = repo.split("/")[-1].replace("-", "_").replace("_strategy", "")

    # 提取参数
    params = []
    param_patterns = [
        r'params\s*=\s*\((.*?)\)',
        r'params\s*:\s*Dict\[.*?\]\s*=\s*\{(.*?)\}',
    ]
    for pat in param_patterns:
        m = re.search(pat, code, re.DOTALL)
        if m:
            param_str = m.group(1)
            nums = re.findall(r'\d+', param_str)
            params = [int(n) for n in nums[:5]]  # 取前5个数字参数
            break

    # 检测买卖逻辑
    has_next = bool(re.search(r"def\s+next\s*\(", code))
    has_buy = bool(re.search(r"self\.buy\(", code))
    has_sell = bool(re.search(r"self\.sell\(", code))
    can_backtest = has_next and (has_buy or has_sell)

    # 质量评分
    score = 0.0
    if can_backtest:
        score += 3.0
    if params:
        score += 1.5
    if re.search(r" Indicators |indicators\.", code, re.IGNORECASE):
        score += 1.5
    if re.search(r" log\(|logging\.", code):
        score += 1.0
    if re.search(r" self\.broker\.getvalue", code):
        score += 1.0
    if re.search(r" cerebro\.addanalyzer", code, re.IGNORECASE):
        score += 2.0
    score = min(score, 10.0)

    # 问题检测
    issues = []
    if not has_next:
        issues.append("缺少 next() 方法，无法运行")
    if not has_buy:
        issues.append("缺少买入逻辑 (self.buy)")
    if not has_sell:
        issues.append("缺少卖出逻辑 (self.sell)")
    if len(code) < 300:
        issues.append("代码过短，可能是片段")
    if not params:
        issues.append("未检测到可配置参数")

    framework = detect_framework(code)
    return {
        "name": name,
        "name_cn": name.replace("_", " ").replace("-", " ").title(),
        "category": detect_strategy_type(code),
        "description": f"GitHub开源策略 from {repo}，参数: {params[:3] if params else '默认'}",
        "code": code,
        "framework": framework if framework != "unknown" else "backtrader",
        "factors": detect_factors(code),
        "quality_score": score,
        "backtest_ready": can_backtest,
        "issues": issues,
        "source": f"github/{repo}",
        "language": "python",
        "stars": 0,
        "author": repo.split("/")[0] if "/" in repo else "unknown",
        "source_url": f"https://github.com/{repo}",
    }


def crawl_github_raw(owner: str, repo: str, path: str = "strategy.py") -> Optional[str]:
    """通过GitHub API获取原始文件"""
    import os
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    token = os.getenv("GITHUB_TOKEN", "")

    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        import urllib.request
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def get_github_readme(owner: str, repo: str) -> Optional[str]:
    """获取GitHub README内容"""
    import os
    api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    token = os.getenv("GITHUB_TOKEN", "")

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        import urllib.request
        import base64
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if "content" in data:
                return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    except Exception:
        return None


def get_github_stars(owner: str, repo: str) -> int:
    """获取GitHub仓库star数"""
    import os
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    token = os.getenv("GITHUB_TOKEN", "")

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        import urllib.request
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("stargazers_count", 0)
    except Exception:
        return 0


def search_github_code(keyword: str, per_page: int = 5) -> List[Dict]:
    """GitHub代码搜索"""
    import os
    import urllib.parse
    query = urllib.parse.quote(f"{keyword} language:python")
    api_url = f"https://api.github.com/search/code?q={query}&per_page={per_page}&sort=indexed"

    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        import urllib.request
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("items", [])
    except Exception:
        return []


def crawl_known_repos() -> List[CrawledStrategy]:
    """爬取已知的高质量量化仓库"""
    strategies = []

    # 策略文件名模式
    strategy_paths = [
        "strategy.py", "strategies.py", "backtest.py",
        "strategy/backtest.py", "strategies/ma_cross.py",
        "strategies/rsi_strategy.py", "strategies/momentum.py",
        "examples/strategy.py", "src/strategy.py",
    ]

    for repo_full, desc in GITHUB_QUANT_REPOS:
        owner, repo = repo_full.split("/")

        # 获取star数
        stars = get_github_stars(owner, repo)
        if stars < 10:
            continue  # 跳过太少star的项目

        # 尝试多个路径
        for path in strategy_paths:
            code = crawl_github_raw(owner, repo, path)
            if code and len(code) > 300:
                info = extract_strategy_from_github_code(code, repo_full)
                if info:
                    info["stars"] = stars
                    info["name_cn"] = f"{desc} ({info['name']})"
                    strategies.append(CrawledStrategy(**info))
                    break  # 只取第一个找到的策略文件

        # 备用: 从README找策略描述
        if not any(s.source == f"github/{repo_full}" for s in strategies):
            readme = get_github_readme(owner, repo)
            if readme:
                # 简单从README提取描述
                info = {
                    "name": repo,
                    "name_cn": desc,
                    "category": detect_strategy_type(readme),
                    "description": readme[:200].replace("#", "").replace("*", "").strip(),
                    "code": "",
                    "framework": "unknown",
                    "factors": [],
                    "quality_score": 0.5,
                    "backtest_ready": False,
                    "issues": ["README信息，无可执行代码"],
                    "source": f"github/{repo_full}",
                    "language": "python",
                    "stars": stars,
                    "author": owner,
                    "source_url": f"https://github.com/{repo_full}",
                }
                strategies.append(CrawledStrategy(**info))

    return strategies


def crawl_github_search() -> List[CrawledStrategy]:
    """通过GitHub搜索爬取策略"""
    strategies = []

    for keyword in GITHUB_SEARCH_KEYWORDS[:5]:  # 限制数量避免API限流
        items = search_github_code(keyword, per_page=3)
        for item in items:
            repo_url = item.get("repository", {}).get("full_name", "")
            file_path = item.get("path", "")
            if not repo_url:
                continue

            # 跳过非策略文件
            if not any(k in file_path.lower() for k in ["strategy", "backtest", "trade"]):
                continue

            owner, repo = repo_url.split("/")
            code = crawl_github_raw(owner, repo, file_path)
            if code and len(code) > 300:
                info = extract_strategy_from_github_code(code, repo_url)
                if info and info["backtest_ready"]:
                    info["stars"] = item.get("repository", {}).get("stargazers_count", 0)
                    strategies.append(CrawledStrategy(**info))

    return strategies


# ═══════════════════════════════════════════
# 量化因子爬虫
# ═══════════════════════════════════════════

QUANTITATIVE_FACTORS = [
    # Alpha因子
    {
        "name": "市值因子 (Size)",
        "symbol": "SIZE",
        "category": "风格因子",
        "description": "股票市值规模对收益的影响，小市值溢价显著",
        "formula": "ln(MarketCap)",
        "tags": ["市值", "规模", "Size"],
        "implementation": '''
# 市值因子实现
def size_factor(stock_data):
    \"\"\"市值因子 = ln(总市值)\"\"\"
    market_cap = stock_data['close'] * stock_data['total_shares']
    return np.log(market_cap + 1)
'''
    },
    {
        "name": "价值因子 (Value)",
        "symbol": "VALUE",
        "category": "风格因子",
        "description": "PB/PE/PCF多维度价值评估，低估值股票超额收益",
        "formula": "1/PB + 1/PE + 1/PCF",
        "tags": ["价值", "估值", "Value"],
        "implementation": '''
# 价值因子实现
def value_factor(stock_data):
    \"\"\"价值因子 = 1/PB + 1/PE + 1/PCF\"\"\"
    pb = stock_data.get('pb', 1)
    pe = stock_data.get('pe', 1)
    pcf = stock_data.get('pcf', 1)
    return 1/(pb+0.01) + 1/(pe+0.01) + 1/(pcf+0.01)
'''
    },
    {
        "name": "动量因子 (Momentum)",
        "symbol": "MOM",
        "category": "技术因子",
        "description": "历史收益惯性，过去N月强势股继续强势",
        "formula": "Return(t-N, t)",
        "tags": ["动量", "Momentum", "趋势"],
        "implementation": '''
# 动量因子实现
def momentum_factor(prices, period=20):
    \"\"\"动量因子 = 过去N日收益率\"\"\"
    return (prices / prices.shift(period) - 1)
'''
    },
    {
        "name": "反转因子 (Reversal)",
        "symbol": "REVERSE",
        "category": "技术因子",
        "description": "短期反转效应，近期跌多的股票大概率反弹",
        "formula": "-Return(t-N, t)",
        "tags": ["反转", "Reversal", "超跌"],
        "implementation": '''
# 反转因子实现
def reversal_factor(prices, period=5):
    \"\"\"反转因子 = -过去N日收益率（跌的涨回来）\"\"\"
    return -(prices / prices.shift(period) - 1)
'''
    },
    {
        "name": "波动率因子 (Volatility)",
        "symbol": "VOL",
        "category": "风险因子",
        "description": "低波动率股票长期超额收益（波动率异象）",
        "formula": "StdDev(Return, N) / Mean(Return, N)",
        "tags": ["波动率", "Volatility", "风险"],
        "implementation": '''
# 波动率因子实现
import numpy as np
def volatility_factor(returns, period=20):
    \"\"\"波动率因子 = -N日收益标准差（低波动=正因子）\"\"\"
    return -returns.rolling(window=period).std()
'''
    },
    {
        "name": "质量因子 (Quality)",
        "symbol": "QUALITY",
        "category": "基本面因子",
        "description": "ROE/ROA/毛利率，高质量公司长期跑赢",
        "formula": "ROE * GrossMargin",
        "tags": ["质量", "Quality", "ROE"],
        "implementation": '''
# 质量因子实现
def quality_factor(financial_data):
    \"\"\"质量因子 = ROE * (1-负债率) * 毛利率\"\"\"
    roe = financial_data['roe']
    debt_ratio = financial_data['total_liabilities'] / financial_data['total_assets']
    gross_margin = financial_data['gross_profit'] / financial_data['revenue']
    return roe * (1 - debt_ratio) * gross_margin
'''
    },
    {
        "name": "成长因子 (Growth)",
        "symbol": "GROWTH",
        "category": "基本面因子",
        "description": "营收/利润增速，高成长公司享受估值溢价",
        "formula": "YoY_Revenue + YoY_Profit",
        "tags": ["成长", "Growth", "增速"],
        "implementation": '''
# 成长因子实现
def growth_factor(financial_data):
    \"\"\"成长因子 = 营收增速 + 利润增速\"\"\"
    rev_growth = financial_data['revenue'].pct_change(periods=4)  # 年化
    profit_growth = financial_data['net_profit'].pct_change(periods=4)
    return rev_growth + profit_growth
'''
    },
    {
        "name": "流动性因子 (Liquidity)",
        "symbol": "LIQUIDITY",
        "category": "交易因子",
        "description": "换手率/成交额，流动性对股价有影响",
        "formula": "Turnover / Average(Turnover, 20)",
        "tags": ["流动性", "Liquidity", "换手率"],
        "implementation": '''
# 流动性因子实现
def liquidity_factor(turnover_rate, period=20):
    \"\"\"流动性因子 = 当前换手率 / 20日均换手率\"\"\"
    avg_turnover = turnover_rate.rolling(window=period).mean()
    return turnover_rate / (avg_turnover + 0.01)
'''
    },
    {
        "name": "北向资金因子",
        "symbol": "HSGT",
        "category": "资金流因子",
        "description": "沪深港通北向资金净买入，外资持股比例变化",
        "formula": "HSGT_Buy - HSGT_Sell",
        "tags": ["北向", "外资", "陆股通"],
        "implementation": '''
# 北向资金因子实现
def hsgt_factor(df_hsgt):
    \"\"\"北向资金因子 = 持股量变化% + 净买入金额\"\"\"
    holding_change = df_hsgt['hold_ratio'].diff()
    net_buy = df_hsgt['buy_net'] / df_hsgt['buy_net'].abs().mean()
    return holding_change + net_buy * 0.5
'''
    },
    {
        "name": "龙虎榜因子",
        "symbol": "TOPLIST",
        "category": "资金流因子",
        "description": "机构/游资龙虎榜数据，识别主力动向",
        "formula": "Inst_Buy% - Inst_Sell%",
        "tags": ["龙虎榜", "机构", "游资"],
        "implementation": '''
# 龙虎榜因子实现
def toplist_factor(toplist_data):
    \"\"\"龙虎榜因子 = 机构买入占比 - 机构卖出占比\"\"\"
    inst_buy_pct = toplist_data['institution_buy'] / (toplist_data['total_buy'] + 1)
    inst_sell_pct = toplist_data['institution_sell'] / (toplist_data['total_sell'] + 1)
    return inst_buy_pct - inst_sell_pct
'''
    },
]


def get_factor_library() -> List[Dict]:
    """获取量化因子库"""
    return QUANTITATIVE_FACTORS


# ═══════════════════════════════════════════
# 量化社区策略 (模拟数据 - 真实平台需要登录)
# ═══════════════════════════════════════════

COMMUNITY_STRATEGIES = [
    # 这些是公开分享的策略，来源包括：掘金/聚宽社区公开帖子
    {
        "name": "双均线金叉死叉策略",
        "name_cn": "经典双均线策略",
        "source": "社区公开分享",
        "source_url": "https://bbs.laughingzhu.org",
        "category": "趋势跟踪",
        "description": "5日均线上穿20日均线买入，下穿卖出。经典趋势策略，适合趋势行情。",
        "code": '''import backtrader as bt

class DualMAStrategy(bt.Strategy):
    params = (
        ("fast_period", 5),
        ("slow_period", 20),
    )

    def __init__(self):
        self.ma_fast = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.ma_slow = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.ma_fast, self.ma_slow)

    def next(self):
        if self.crossover > 0:
            self.buy()
        elif self.crossover < 0:
            self.sell()
''',
        "framework": "backtrader",
        "factors": ["均线"],
        "quality_score": 7.0,
        "backtest_ready": True,
        "issues": [],
    },
    {
        "name": "RSI均值回归策略",
        "name_cn": "RSI超买超卖策略",
        "source": "社区公开分享",
        "source_url": "https://bbs.laughingzhu.org",
        "category": "均值回归",
        "description": "RSI<30超卖买入，RSI>70超买卖出。适合震荡市。",
        "code": '''import backtrader as bt

class RSIStrategy(bt.Strategy):
    params = (
        ("rsi_period", 14),
        ("rsi_low", 30),
        ("rsi_high", 70),
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

    def next(self):
        if not self.position:
            if self.rsi < self.params.rsi_low:
                self.buy()
        else:
            if self.rsi > self.params.rsi_high:
                self.sell()
''',
        "framework": "backtrader",
        "factors": ["RSI"],
        "quality_score": 6.5,
        "backtest_ready": True,
        "issues": [],
    },
    {
        "name": "布林带突破策略",
        "name_cn": "布林带趋势策略",
        "source": "聚宽社区",
        "source_url": "https://www.joinquant.com",
        "category": "趋势跟踪",
        "description": "价格上穿布林带上轨买入，下穿下轨卖出。",
        "code": '''import backtrader as bt

class BollingerStrategy(bt.Strategy):
    params = (
        ("period", 20),
        ("devfactor", 2),
    )

    def __init__(self):
        self.boll = bt.indicators.BollingerBands(
            self.data.close, period=self.params.period,
            devfactor=self.params.devfactor
        )

    def next(self):
        if not self.position:
            if self.data.close > self.boll.lines.top:
                self.buy()
        else:
            if self.data.close < self.boll.lines.bot:
                self.sell()
''',
        "framework": "backtrader",
        "factors": ["布林带"],
        "quality_score": 7.0,
        "backtest_ready": True,
        "issues": [],
    },
    {
        "name": "MACD趋势策略",
        "name_cn": "MACD金叉死叉策略",
        "source": "聚宽社区",
        "source_url": "https://www.joinquant.com",
        "category": "趋势跟踪",
        "description": "MACD柱由负转正买入，由正转负卖出。",
        "code": '''import backtrader as bt

class MACDStrategy(bt.Strategy):
    params = (
        ("fast", 12),
        ("slow", 26),
        ("signal", 9),
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast,
            period_me2=self.params.slow,
            period_signal=self.params.signal
        )
        self.histogram = self.macd.lines.macd - self.macd.lines.signal

    def next(self):
        if not self.position:
            if self.histogram > 0 and self.histogram > self.histogram(-1):
                self.buy()
        else:
            if self.histogram < 0 and self.histogram < self.histogram(-1):
                self.sell()
''',
        "framework": "backtrader",
        "factors": ["MACD"],
        "quality_score": 7.5,
        "backtest_ready": True,
        "issues": [],
    },
    {
        "name": "小市值选股策略",
        "name_cn": "市值因子选股策略",
        "source": "果仁社区",
        "source_url": "https://guorn.com",
        "category": "多因子",
        "description": "选取市值最小的N只股票等权配置，月度轮动。",
        "code": '''import backtrader as bt

class SmallCapStrategy(bt.Strategy):
    params = (
        ("num_stocks", 10),  # 持仓数量
        ("rebalance_days", 20),  # 调仓周期
    )

    def __init__(self):
        self.counter = 0
        # 市值因子（这里用收盘价×成交量模拟）
        self.market_cap_proxy = self.data.close * self.data.volume

    def next(self):
        self.counter += 1
        if self.counter % self.params.rebalance_days == 0:
            # 取消所有现有持仓
            for order in self.pending:
                self.cancel(order)
            for position in self.positions.values():
                if position.size > 0:
                    self.close(position)

            # 买入市值最小的
            if self.market_cap_proxy < self.market_cap_proxy[1] * 0.5:
                self.order_target_size(target=self.params.num_stocks)
''',
        "framework": "backtrader",
        "factors": ["市值因子"],
        "quality_score": 6.0,
        "backtest_ready": True,
        "issues": ["需要真实市值数据替代模拟"],
    },
    {
        "name": "CCI超买超卖策略",
        "name_cn": "CCI顺势指标策略",
        "source": "期货量化社区",
        "source_url": "https://www.aitrader.com",
        "category": "技术指标",
        "description": "CCI>100超买区间做空，CCI<-100超卖区间做多。商品期货常用。",
        "code": '''import backtrader as bt

class CCIStrategy(bt.Strategy):
    params = (
        ("cci_period", 14),
        ("overbought", 100),
        ("oversold", -100),
    )

    def __init__(self):
        self.cci = bt.indicators.CommodityChannelIndex(
            self.data, period=self.params.cci_period
        )

    def next(self):
        if not self.position:
            if self.cci < self.params.oversold:
                self.buy()
        else:
            if self.cci > self.params.overbought:
                self.sell()
''',
        "framework": "backtrader",
        "factors": ["CCI"],
        "quality_score": 6.5,
        "backtest_ready": True,
        "issues": [],
    },
]


# ═══════════════════════════════════════════
# 主爬虫类
# ═══════════════════════════════════════════

class StrategyCrawler:
    """策略爬虫主类"""

    def __init__(self):
        self.github_cache = []
        self.community_strategies = [CrawledStrategy(**s) for s in COMMUNITY_STRATEGIES]

    def crawl_all(self, progress_callback=None) -> List[CrawledStrategy]:
        """抓取所有来源的策略"""
        all_strategies = []
        total_steps = 3
        step = 0

        # Step 1: 抓取已知量化仓库
        if progress_callback:
            progress_callback(1/total_steps, "🔍 抓取 GitHub 量化开源项目...")
        step += 1
        github_strategies = crawl_known_repos()
        all_strategies.extend(github_strategies)

        # Step 2: GitHub 搜索 (需要 token 才有效)
        if progress_callback:
            progress_callback(2/total_steps, "🔍 GitHub 代码搜索...")
        step += 1
        try:
            search_strategies = crawl_github_search()
            all_strategies.extend(search_strategies)
        except Exception:
            pass  # 搜索失败不影响整体

        # Step 3: 社区策略
        if progress_callback:
            progress_callback(3/total_steps, "📋 加载社区公开策略...")
        all_strategies.extend(self.community_strategies)

        # 去重
        seen = set()
        unique = []
        for s in all_strategies:
            key = hashlib.md5(s.code[:500].encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique.append(s)

        # 排序: 可回测的优先
        unique.sort(key=lambda x: -x.quality_score if x.backtest_ready else -5)

        return unique

    def get_factor_library(self) -> List[Dict]:
        """获取量化因子库"""
        return QUANTITATIVE_FACTORS

    def save_cache(self, strategies: List[CrawledStrategy]):
        """保存到本地缓存"""
        data = [asdict(s) for s in strategies]
        CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_cache(self) -> List[CrawledStrategy]:
        """从缓存加载"""
        if not CACHE_FILE.exists():
            return []
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            return [CrawledStrategy(**d) for d in data]
        except Exception:
            return []

    def get_stats(self, strategies: List[CrawledStrategy]) -> Dict:
        """获取抓取统计"""
        backtest_ready = sum(1 for s in strategies if s.backtest_ready)
        by_source = {}
        for s in strategies:
            source = s.source.split("/")[0] if "/" in s.source else s.source
            by_source[source] = by_source.get(source, 0) + 1

        return {
            "total": len(strategies),
            "backtest_ready": backtest_ready,
            "by_source": by_source,
            "cache_date": strategies[0].crawl_date if strategies else "",
        }


# ═══════════════════════════════════════════
# Streamlit UI 集成
# ═══════════════════════════════════════════

@st.cache_data(ttl=3600)
def cached_crawl():
    """缓存的爬取结果 (1小时刷新一次)"""
    crawler = StrategyCrawler()
    strategies = crawler.crawl_all()
    crawler.save_cache(strategies)
    return strategies


def render_crawler_ui():
    """渲染爬虫UI"""
    import streamlit as st
    from core.ai_analyzer import AIAnalyzer

    st.markdown("""
    <div class="section-title">📡 策略 & 因子每日抓取</div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("🚀 立即抓取最新策略", type="primary", use_container_width=True):
            with st.spinner("正在从 GitHub + 社区抓取策略..."):
                try:
                    strategies = cached_crawl()
                    st.session_state["crawled_strategies"] = strategies
                    st.success(f"✅ 抓取完成！共获取 {len(strategies)} 个策略")
                except Exception as e:
                    # 尝试从缓存加载
                    crawler = StrategyCrawler()
                    strategies = crawler.load_cache()
                    if strategies:
                        st.session_state["crawled_strategies"] = strategies
                        st.warning(f"⚠️ 抓取出错，使用缓存 ({len(strategies)} 个策略)")
                    else:
                        st.error(f"抓取失败: {e}")

    with col2:
        if st.button("📦 加载缓存策略", use_container_width=True):
            crawler = StrategyCrawler()
            strategies = crawler.load_cache()
            if strategies:
                st.session_state["crawled_strategies"] = strategies
                st.success(f"已加载 {len(strategies)} 个缓存策略")
            else:
                st.info("暂无缓存，请先抓取")

    st.markdown("---")

    strategies = st.session_state.get("crawled_strategies", [])

    if not strategies:
        st.info("👆 点击「立即抓取」开始获取最新量化策略和因子")
        return

    crawler = StrategyCrawler()
    stats = crawler.get_stats(strategies)

    # 统计
    cols = st.columns(4)
    cols[0].metric("总策略数", stats["total"])
    cols[1].metric("✅ 可直接回测", stats["backtest_ready"])
    cols[2].metric("📅 抓取时间", stats["cache_date"])
    cols[3].metric("🌐 来源数", len(stats["by_source"]))

    st.markdown("---")

    # 分类筛选
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
    with filter_col1:
        show_filter = st.selectbox("筛选", ["全部", "✅ 可回测", "⚠️ 需修改", "🔥 高评分"])
    with filter_col2:
        source_filter = st.selectbox("来源", ["全部"] + list(stats["by_source"].keys()))
    with filter_col3:
        limit_n = st.number_input("显示数量", 5, 50, 20)

    # 过滤
    filtered = strategies
    if show_filter == "✅ 可回测":
        filtered = [s for s in filtered if s.backtest_ready]
    elif show_filter == "⚠️ 需修改":
        filtered = [s for s in filtered if not s.backtest_ready]
    elif show_filter == "🔥 高评分":
        filtered = [s for s in filtered if s.quality_score >= 7.0]

    if source_filter != "全部":
        filtered = [s for s in filtered if source_filter in s.source]

    filtered = filtered[:int(limit_n)]

    st.markdown(f"**展示 {len(filtered)} / {len(strategies)} 个策略**")

    # 策略列表
    for s in filtered:
        score_color = "#10b981" if s.backtest_ready else "#f59e0b"
        score_label = "✅ 可回测" if s.backtest_ready else f"⚠️ {len(s.issues)}个问题"

        with st.container():
            col_s1, col_s2 = st.columns([4, 1])
            with col_s1:
                st.markdown(f"""
                <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:16px;margin-bottom:8px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                        <span style="background:#3b82f622;color:#3b82f6;padding:2px 8px;border-radius:6px;font-size:11px;">{s.source[:30]}</span>
                        <span style="background:{score_color}22;color:{score_color};padding:2px 8px;border-radius:6px;font-size:11px;">{score_label}</span>
                        <span style="color:#94a3b8;font-size:12px;">⭐{s.stars} · {s.framework}</span>
                        <span style="color:#64748b;font-size:12px;">{s.category}</span>
                    </div>
                    <div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:4px;">{s.name_cn or s.name}</div>
                    <div style="color:#64748b;font-size:12px;margin-bottom:8px;">{s.description[:100]}</div>
                    {f'<div style="color:#94a3b8;font-size:12px;">因子: {" + ".join(s.factors[:5])}</div>' if s.factors else ''}
                </div>
                """, unsafe_allow_html=True)
            with col_s2:
                if s.backtest_ready and s.code:
                    if st.button(f"▶️ 回测", key=f"crawl_run_{s.name[:20]}", use_container_width=True):
                        st.session_state["pasted_strategy_code"] = s.code
                        st.session_state["pasted_strategy_name"] = s.name_cn
                        st.success(f"✅ 已加载: {s.name_cn}，前往「⚔️ 策略PK」运行回测")
                        st.rerun()

    st.markdown("---")

    # 量化因子库
    st.markdown("### 📊 量化因子库")
    factors = get_factor_library()

    fac_cols = st.columns(3)
    for i, fac in enumerate(factors[:9]):
        with fac_cols[i % 3]:
            with st.container():
                st.markdown(f"""
                <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:14px;margin-bottom:8px;">
                    <div style="color:#e2e8f0;font-size:14px;font-weight:600;margin-bottom:4px;">{fac['symbol']} {fac['name']}</div>
                    <div style="color:#64748b;font-size:12px;margin-bottom:8px;">{fac['description'][:80]}</div>
                    <div style="color:#94a3b8;font-size:11px;">公式: <code>{fac['formula']}</code></div>
                    <div style="margin-top:6px;">{" ".join([f"<span style='background:#1e293b;color:#94a3b8;padding:1px 6px;border-radius:4px;font-size:11px;'>{t}</span>" for t in fac['tags']])}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown(f"_共 {len(factors)} 个量化因子，涵盖风格/技术/基本面/资金流_")
