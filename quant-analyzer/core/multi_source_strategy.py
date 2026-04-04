"""
多源策略学习模块 v2.0
整合三大来源:
1. 📄 arxiv论文 — 学术前沿量化策略
2. 💻 GitHub开源 — 实战量化策略代码
3. 🌐 量化社区 — 聚宽/米筐/雪球社区策略

核心改进:
- arxiv论文搜索（量化金融/机器学习/交易策略方向）
- GitHub搜索整合（复用strategy_crawler）
- AI知识提取统一入口
- 多源学习与主知识库双向打通
"""

import re
import json
import time
import random
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from urllib.parse import urljoin, quote

import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════

@dataclass
class StrategySource:
    """策略来源信息（统一模型）"""
    platform: str          # 来源平台: arxiv, github, joinquant, ricequant, xueqiu
    url: str               # 策略URL
    title: str             # 标题
    author: str = ""       # 作者
    publish_date: str = "" # 发布日期
    view_count: int = 0    # 浏览量 / 引用数
    like_count: int = 0    # 点赞 / Star数
    code: str = ""         # 策略代码
    description: str = ""  # 策略描述/摘要
    tags: List[str] = field(default_factory=list)
    arxiv_id: str = ""     # arxiv论文ID（仅arxiv来源）
    extra: Dict = field(default_factory=dict)  # 平台额外信息

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.extra is None:
            self.extra = {}


@dataclass
class ExtractedKnowledge:
    """AI提取的结构化策略知识"""
    strategy_type: str = ""         # 策略类型
    core_logic: str = ""            # 核心交易逻辑
    indicators: List[str] = field(default_factory=list)  # 技术指标
    risk_control: str = ""          # 风险控制方法
    market_condition: str = ""      # 适用市场环境
    improvement_suggestions: str = ""  # 改进建议
    key_factors: List[str] = field(default_factory=list)  # 关键因子
    source_platform: str = ""       # 来源平台
    source_title: str = ""          # 来源标题
    source_url: str = ""            # 来源URL
    extraction_date: str = ""       # 提取日期
    quality_score: float = 0.0      # AI评估质量分(0-100)


# ═══════════════════════════════════════════════
# arxiv 论文搜索器
# ═══════════════════════════════════════════════

# 量化策略相关搜索词（英文，arxiv论文以英文为主）
ARXIV_QUANT_KEYWORDS = [
    "quantitative trading strategy",
    "algorithmic trading machine learning",
    "stock market prediction deep learning",
    "portfolio optimization reinforcement learning",
    "momentum factor investing",
    "mean reversion trading",
    "technical analysis neural network",
    "high frequency trading",
    "statistical arbitrage",
    "volatility trading strategy",
    "market microstructure",
    "alpha factor discovery",
    "risk parity portfolio",
    "time series forecasting financial",
    "sentiment analysis trading",
    # 中文量化也可以搜
    "量化交易策略",
    "A股量化",
    "股票预测",
]

# arxiv分类筛选
ARXIV_CATEGORIES = [
    "q-fin",      # 量化金融
    "cs.LG",      # 机器学习
    "stat.ML",    # 统计机器学习
    "q-fin.PM",   # 投资组合管理
    "q-fin.ST",   # 统计金融
    "q-fin.TR",   # 定价与风险
    "q-fin.CP",   # 计算金融
]


class ArxivPaperSearcher:
    """arxiv论文搜索器 — 通过arxiv API搜索量化策略论文"""

    API_BASE = "http://export.arxiv.org/api/query"
    ABSTRACT_BASE = "https://arxiv.org/abs/"
    PDF_BASE = "https://arxiv.org/pdf/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "QuantBrain/4.0 (mailto:quant@example.com)",
            "Accept": "application/atom+xml",
        })

    def search_papers(self, keyword: str, max_results: int = 10,
                      category: str = None, sort_by: str = "relevance") -> List[StrategySource]:
        """
        搜索arxiv论文

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            category: arxiv分类 (如 q-fin)
            sort_by: 排序方式 (relevance / submittedDate)
        """
        strategies = []

        # 构建查询
        query_parts = [f"all:{keyword}"]
        if category:
            query_parts.append(f"cat:{category}")

        query = " AND ".join(query_parts)

        params = {
            "search_query": query,
            "start": 0,
            "max_results": min(max_results, 30),  # arxiv单次最多30
            "sortBy": sort_by,
            "sortOrder": "descending",
        }

        try:
            resp = self.session.get(self.API_BASE, params=params, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"arxiv API返回 {resp.status_code}")
                return []

            # 解析Atom XML
            from xml.etree import ElementTree as ET
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom",
                  "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                try:
                    title_elem = entry.find("atom:title", ns)
                    summary_elem = entry.find("atom:summary", ns)
                    published_elem = entry.find("atom:published", ns)
                    link_elem = entry.find("atom:id", ns)

                    # arxiv ID
                    arxiv_id = ""
                    for link in entry.findall("atom:link", ns):
                        href = link.get("href", "")
                        m = re.search(r'(\d{4}\.\d{4,5})', href)
                        if m:
                            arxiv_id = m.group(1)
                            break

                    title = title_elem.text.strip().replace("\n", " ") if title_elem is not None else "Unknown"
                    summary = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None else ""
                    published = published_elem.text[:10] if published_elem is not None else ""

                    # 只保留与量化/交易相关的论文
                    if not self._is_quant_related(title + " " + summary):
                        continue

                    strategies.append(StrategySource(
                        platform="arxiv",
                        url=f"{self.ABSTRACT_BASE}{arxiv_id}" if arxiv_id else "",
                        title=title,
                        author=self._extract_authors(entry, ns),
                        publish_date=published,
                        view_count=0,  # arxiv不提供引用数
                        description=summary[:800],
                        tags=self._extract_categories(entry, ns),
                        arxiv_id=arxiv_id,
                        extra={
                            "pdf_url": f"{self.PDF_BASE}{arxiv_id}" if arxiv_id else "",
                            "full_abstract": summary,
                        }
                    ))
                except Exception as e:
                    logger.debug(f"解析arxiv条目失败: {e}")
                    continue

        except requests.Timeout:
            logger.warning("arxiv API请求超时")
        except Exception as e:
            logger.error(f"arxiv搜索失败: {e}")

        return strategies[:max_results]

    def _is_quant_related(self, text: str) -> bool:
        """判断论文是否与量化交易相关"""
        keywords = [
            "trading", "strategy", "portfolio", "stock", "market",
            "quantitative", "algorithmic", "alpha", "factor", "return",
            "prediction", "forecast", "price", "volatility", "risk",
            "hedge", "arbitrage", "momentum", "backtest",
            "量化", "交易", "股票", "投资", "策略", "因子", "回测",
        ]
        text_lower = text.lower()
        # 至少匹配2个关键词才认为是相关的
        return sum(1 for kw in keywords if kw in text_lower) >= 2

    def _extract_authors(self, entry, ns) -> str:
        """提取作者列表"""
        authors = []
        for author in entry.findall("atom:author", ns):
            name_elem = author.find("atom:name", ns)
            if name_elem is not None:
                authors.append(name_elem.text.strip())
        if len(authors) > 3:
            return f"{', '.join(authors[:3])} et al."
        return ", ".join(authors)

    def _extract_categories(self, entry, ns) -> List[str]:
        """提取分类标签"""
        tags = []
        for cat in entry.findall("atom:category", ns):
            term = cat.get("term", "")
            if term:
                tags.append(term)
        return tags

    def get_paper_details(self, arxiv_id: str) -> Optional[Dict]:
        """获取论文详情（通过arxiv API）"""
        try:
            params = {
                "id_list": arxiv_id,
                "max_results": 1,
            }
            resp = self.session.get(self.API_BASE, params=params, timeout=15)
            if resp.status_code != 200:
                return None

            from xml.etree import ElementTree as ET
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom",
                  "arxiv": "http://arxiv.org/schemas/atom"}

            entry = root.find("atom:entry", ns)
            if entry is None:
                return None

            summary = entry.find("atom:summary", ns)
            return {
                "abstract": summary.text.strip() if summary is not None else "",
                "arxiv_id": arxiv_id,
            }
        except Exception as e:
            logger.error(f"获取arxiv论文详情失败: {e}")
            return None


# ═══════════════════════════════════════════════
# GitHub 策略搜索器
# ═══════════════════════════════════════════════

GITHUB_SEARCH_KEYWORDS = [
    "backtrader strategy A股",
    "quantitative trading strategy python",
    "A股量化策略",
    "stock trading bot python China",
    "algorithmic trading A-share",
    "量化交易策略 python",
    "momentum strategy backtest",
]

class GitHubStrategySearcher:
    """GitHub策略搜索器 — 通过GitHub API搜索开源量化策略"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "QuantBrain/4.0",
            "Accept": "application/vnd.github.v3+json",
        })
        # 尝试获取GitHub Token
        import os
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            self.session.headers["Authorization"] = f"token {token}"

    def search_repositories(self, keyword: str, max_results: int = 10) -> List[StrategySource]:
        """搜索GitHub量化项目"""
        strategies = []
        query = f"{keyword} language:python stars:>5 pushed:2023-01-01"

        try:
            resp = self.session.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc", "per_page": max_results},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"GitHub API返回 {resp.status_code}")
                return []

            data = resp.json()
            for item in data.get("items", []):
                desc = item.get("description", "") or ""
                # 过滤非策略相关项目
                if not self._is_strategy_repo(desc + " " + item.get("name", "")):
                    continue

                strategies.append(StrategySource(
                    platform="github",
                    url=item.get("html_url", ""),
                    title=item.get("full_name", ""),
                    author=item.get("owner", {}).get("login", ""),
                    publish_date=item.get("updated_at", "")[:10],
                    view_count=0,
                    like_count=item.get("stargazers_count", 0),
                    description=desc[:500],
                    tags=[item.get("language", "python")],
                    extra={
                        "forks": item.get("forks_count", 0),
                        "topics": item.get("topics", []),
                    }
                ))

        except Exception as e:
            logger.error(f"GitHub搜索失败: {e}")

        return strategies[:max_results]

    def search_code(self, keyword: str, max_results: int = 10) -> List[StrategySource]:
        """搜索GitHub代码片段（搜索包含策略代码的文件）"""
        strategies = []
        # 搜索 backtrader Strategy 类定义
        code_queries = [
            f"{keyword} class Strategy bt.Strategy",
            f"{keyword} def next self buy self sell",
        ]

        for query in code_queries[:1]:  # 只执行一个查询避免API限制
            try:
                resp = self.session.get(
                    "https://api.github.com/search/code",
                    params={"q": query, "per_page": max_results},
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                for item in data.get("items", []):
                    repo_name = item.get("repository", {}).get("full_name", "")
                    file_name = item.get("name", "")
                    file_path = item.get("path", "")

                    strategies.append(StrategySource(
                        platform="github",
                        url=item.get("html_url", ""),
                        title=f"{repo_name}: {file_name}",
                        author=repo_name.split("/")[0] if "/" in repo_name else "",
                        description=f"文件路径: {file_path}",
                        tags=["code", "python"],
                        extra={
                            "repo_name": repo_name,
                            "file_path": file_path,
                            "raw_url": f"https://raw.githubusercontent.com/{repo_name}/main/{file_path}",
                        }
                    ))
            except Exception as e:
                logger.debug(f"GitHub代码搜索失败: {e}")
                continue

        return strategies[:max_results]

    def _is_strategy_repo(self, text: str) -> bool:
        """判断是否是策略相关的仓库"""
        keywords = [
            "strategy", "trading", "quant", "backtest", "backtrader",
            "策略", "量化", "交易", "回测", "factor", "alpha",
        ]
        text_lower = text.lower()
        return sum(1 for kw in keywords if kw in text_lower) >= 1

    def fetch_raw_code(self, raw_url: str) -> Optional[str]:
        """获取原始代码内容"""
        try:
            resp = self.session.get(raw_url, timeout=10)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logger.debug(f"获取GitHub原始代码失败: {e}")
        return None


# ═══════════════════════════════════════════════
# 量化社区爬取器（聚宽/米筐/雪球）
# ═══════════════════════════════════════════════

class CommunityStrategyCrawler:
    """量化社区策略爬取器 — 保留原有接口，增加容错"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def search_strategies(self, keyword: str, platforms: List[str] = None,
                          limit: int = 10) -> List[StrategySource]:
        """
        从社区平台搜索策略

        Args:
            keyword: 搜索关键词
            platforms: 平台列表 ["joinquant", "ricequant", "xueqiu"]
            limit: 每个平台返回数量
        """
        if platforms is None:
            platforms = ["joinquant", "ricequant", "xueqiu"]

        all_results = []

        for platform in platforms:
            try:
                if platform == "joinquant":
                    results = self._search_joinquant(keyword, limit)
                elif platform == "ricequant":
                    results = self._search_ricequant(keyword, limit)
                elif platform == "xueqiu":
                    results = self._search_xueqiu(keyword, limit)
                else:
                    continue

                all_results.extend(results)
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                logger.debug(f"{platform} 搜索失败: {e}")

        # 按相关性排序
        all_results.sort(key=lambda x: self._relevance_score(x, keyword), reverse=True)
        return all_results[:limit]

    def _search_joinquant(self, keyword: str, limit: int) -> List[StrategySource]:
        """搜索聚宽策略（使用搜索API）"""
        strategies = []
        try:
            # 聚宽策略搜索页面
            search_url = f"https://www.joinquant.com/view/community/detail?page=1&type=strategy&keyword={quote(keyword)}"
            resp = self.session.get(search_url, timeout=10)
            if resp.status_code != 200:
                return strategies

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            # 尝试多种选择器
            items = (
                soup.find_all("div", class_="strategy-item") or
                soup.find_all("div", class_="strategy-card") or
                soup.find_all("div", class_="list-item") or
                soup.find_all("a", href=re.compile(r"/view/strategy/"))
            )

            for item in items[:limit]:
                try:
                    title_elem = item.find("a") or item
                    title = title_elem.get_text(strip=True)[:100]
                    url = title_elem.get("href", "")
                    if url and not url.startswith("http"):
                        url = urljoin("https://www.joinquant.com", url)

                    if title and len(title) > 5:
                        strategies.append(StrategySource(
                            platform="joinquant",
                            url=url,
                            title=title,
                            description=f"聚宽社区策略: {title}",
                        ))
                except:
                    continue

        except Exception as e:
            logger.debug(f"聚宽搜索异常: {e}")

        return strategies

    def _search_ricequant(self, keyword: str, limit: int) -> List[StrategySource]:
        """搜索米筐策略"""
        strategies = []
        try:
            search_url = f"https://www.ricequant.com/community/search?q={quote(keyword)}"
            resp = self.session.get(search_url, timeout=10)
            if resp.status_code != 200:
                return strategies

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.find_all("div", class_="strategy-card") or
                soup.find_all("div", class_="result-item") or
                soup.find_all("a", href=re.compile(r"/community/strategy"))
            )

            for item in items[:limit]:
                try:
                    title_elem = item.find("a") or item
                    title = title_elem.get_text(strip=True)[:100]
                    url = title_elem.get("href", "")
                    if url and not url.startswith("http"):
                        url = urljoin("https://www.ricequant.com", url)

                    if title and len(title) > 5:
                        strategies.append(StrategySource(
                            platform="ricequant",
                            url=url,
                            title=title,
                            description=f"米筐社区策略: {title}",
                        ))
                except:
                    continue

        except Exception as e:
            logger.debug(f"米筐搜索异常: {e}")

        return strategies

    def _search_xueqiu(self, keyword: str, limit: int) -> List[StrategySource]:
        """搜索雪球策略帖子"""
        strategies = []
        try:
            search_url = f"https://xueqiu.com/k?q={quote(keyword)}"
            resp = self.session.get(search_url, timeout=10)
            if resp.status_code != 200:
                return strategies

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.find_all("div", class_="article-item") or
                soup.find_all("div", class_="search__item") or
                soup.find_all("a", href=re.compile(r"/k/"))
            )

            strategy_keywords = [
                "策略", "量化", "回测", "选股", "择时", "因子", "模型",
                "strategy", "quant", "backtest", "trading",
            ]

            for item in items[:limit * 2]:
                try:
                    title_elem = item.find("a") or item
                    title = title_elem.get_text(strip=True)[:100]
                    url = title_elem.get("href", "")
                    if url and not url.startswith("http"):
                        url = urljoin("https://xueqiu.com", url)

                    # 过滤非策略相关
                    if not any(kw in title.lower() for kw in strategy_keywords):
                        continue

                    if title and len(title) > 5:
                        strategies.append(StrategySource(
                            platform="xueqiu",
                            url=url,
                            title=title,
                            description=f"雪球社区策略帖子: {title}",
                        ))
                except:
                    continue

        except Exception as e:
            logger.debug(f"雪球搜索异常: {e}")

        return strategies

    def _relevance_score(self, strategy: StrategySource, keyword: str) -> float:
        """相关性评分"""
        score = 0.0
        if keyword.lower() in strategy.title.lower():
            score += 3.0
        score += min(strategy.view_count / 1000, 2.0)
        score += min(strategy.like_count / 100, 1.0)
        if strategy.platform in ["joinquant", "ricequant"]:
            score += 1.0  # 专业平台加权
        return score


# ═══════════════════════════════════════════════
# 统一多源策略学习器
# ═══════════════════════════════════════════════

class MultiSourceStrategyLearner:
    """
    统一多源策略学习器 v2.0
    整合 arxiv + GitHub + 量化社区，统一搜索、学习、提取、推荐
    """

    DATA_FILE = Path(__file__).parent.parent / "data" / "multi_source_strategies.json"

    def __init__(self):
        self.arxiv_searcher = ArxivPaperSearcher()
        self.github_searcher = GitHubStrategySearcher()
        self.community_crawler = CommunityStrategyCrawler()
        self.learned_strategies: List[Dict] = []
        self._load_learned()

    def _load_learned(self):
        """加载已学习的策略"""
        try:
            if self.DATA_FILE.exists():
                data = json.loads(self.DATA_FILE.read_text(encoding="utf-8"))
                self.learned_strategies = data if isinstance(data, list) else []
        except Exception as e:
            logger.debug(f"加载多源策略失败: {e}")
            self.learned_strategies = []

    def _save_learned(self):
        """保存已学习的策略"""
        self.DATA_FILE.parent.mkdir(exist_ok=True)
        try:
            self.DATA_FILE.write_text(
                json.dumps(self.learned_strategies, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"保存多源策略失败: {e}")

    # ─── 搜索接口 ───

    def search_arxiv(self, keyword: str = None, max_results: int = 10) -> List[StrategySource]:
        """搜索arxiv论文"""
        if not keyword:
            # 默认搜索词
            keyword = random.choice(ARXIV_QUANT_KEYWORDS[:5])
        return self.arxiv_searcher.search_papers(keyword, max_results)

    def search_github(self, keyword: str = None, max_results: int = 10) -> List[StrategySource]:
        """搜索GitHub策略"""
        if not keyword:
            keyword = random.choice(GITHUB_SEARCH_KEYWORDS)
        return self.github_searcher.search_repositories(keyword, max_results)

    def search_community(self, keyword: str = None,
                        platforms: List[str] = None, max_results: int = 10) -> List[StrategySource]:
        """搜索量化社区策略"""
        if not keyword:
            keyword = "量化策略"
        return self.community_crawler.search_strategies(keyword, platforms, max_results)

    def search_all(self, keyword: str, max_per_source: int = 5) -> Dict[str, List[StrategySource]]:
        """
        全源搜索 — 同时搜索 arxiv + GitHub + 量化社区

        Returns:
            {"arxiv": [...], "github": [...], "community": [...]}
        """
        results = {}

        # arxiv搜索（用英文关键词）
        try:
            results["arxiv"] = self.search_arxiv(keyword, max_per_source)
        except Exception as e:
            logger.warning(f"arxiv搜索失败: {e}")
            results["arxiv"] = []

        # GitHub搜索
        try:
            results["github"] = self.search_github(keyword, max_per_source)
        except Exception as e:
            logger.warning(f"GitHub搜索失败: {e}")
            results["github"] = []

        # 量化社区搜索（用中文关键词）
        try:
            results["community"] = self.search_community(keyword, max_results=max_per_source)
        except Exception as e:
            logger.warning(f"社区搜索失败: {e}")
            results["community"] = []

        return results

    # ─── 知识提取 ───

    def extract_knowledge(self, source: StrategySource) -> Optional[ExtractedKnowledge]:
        """
        使用AI从策略来源中提取结构化知识

        Args:
            source: 策略来源信息

        Returns:
            ExtractedKnowledge 或 None
        """
        if not source.description and not source.code:
            return None

        # 根据来源类型构建不同的提取提示
        if source.platform == "arxiv":
            prompt = self._build_arxiv_extraction_prompt(source)
        elif source.platform == "github":
            prompt = self._build_github_extraction_prompt(source)
        else:
            prompt = self._build_community_extraction_prompt(source)

        try:
            from core.llm_manager import get_llm_manager
            llm = get_llm_manager()
            response = llm.chat([{"role": "user", "content": prompt}])
            return self._parse_knowledge_response(response, source)
        except Exception as e:
            logger.error(f"AI提取知识失败: {e}")
            return None

    def _build_arxiv_extraction_prompt(self, source: StrategySource) -> str:
        return f"""请分析以下量化金融学术论文，提取可实施的交易策略知识：

论文标题：{source.title}
作者：{source.author}
发布日期：{source.publish_date}

论文摘要：
{source.description[:1500] if source.description else "无"}

请以量化交易实践者的角度，提取以下信息：
1. strategy_type: 策略类型（如动量、均值回归、多因子、机器学习等）
2. core_logic: 核心交易逻辑（用简洁的中文描述，200字以内）
3. indicators: 论文提到的技术指标或因子列表
4. key_factors: 关键因子名称列表
5. risk_control: 风险控制方法
6. market_condition: 适用市场环境（牛市/熊市/震荡市/通用）
7. improvement_suggestions: 如何将论文方法应用到A股实践的建议
8. quality_score: 论文对实际交易的参考价值评分（0-100分）

请用JSON格式返回，字段名如上。"""

    def _build_github_extraction_prompt(self, source: StrategySource) -> str:
        return f"""请分析以下GitHub开源量化策略，提取关键知识：

项目名称：{source.title}
作者：{source.author}
Star数：{source.like_count}
项目描述：{source.description[:1000] if source.description else "无"}

策略代码片段：
{source.code[:2000] if source.code else "无"}

请提取：
1. strategy_type: 策略类型
2. core_logic: 核心交易逻辑（中文，200字以内）
3. indicators: 使用的技术指标列表
4. key_factors: 关键因子列表
5. risk_control: 风险控制方法
6. market_condition: 适用市场环境
7. improvement_suggestions: 改进建议
8. quality_score: 策略质量评分（0-100分，考虑代码完整性和策略逻辑）

请用JSON格式返回。"""

    def _build_community_extraction_prompt(self, source: StrategySource) -> str:
        return f"""请分析以下量化社区策略，提取关键知识：

策略标题：{source.title}
平台：{source.platform}
作者：{source.author}

策略描述/内容：
{source.description[:1000] if source.description else "无"}

策略代码：
{source.code[:2000] if source.code else "无"}

请提取：
1. strategy_type: 策略类型
2. core_logic: 核心交易逻辑（中文，200字以内）
3. indicators: 使用的技术指标列表
4. key_factors: 关键因子列表
5. risk_control: 风险控制方法
6. market_condition: 适用市场环境
7. improvement_suggestions: 改进建议
8. quality_score: 策略参考价值评分（0-100分）

请用JSON格式返回。"""

    def _parse_knowledge_response(self, response: str, source: StrategySource) -> ExtractedKnowledge:
        """解析AI返回的JSON知识"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {}

            return ExtractedKnowledge(
                strategy_type=data.get("strategy_type", "未知"),
                core_logic=data.get("core_logic", "未提取到核心逻辑"),
                indicators=data.get("indicators", []),
                risk_control=data.get("risk_control", "未提及"),
                market_condition=data.get("market_condition", "通用"),
                improvement_suggestions=data.get("improvement_suggestions", "需要进一步分析"),
                key_factors=data.get("key_factors", []),
                source_platform=source.platform,
                source_title=source.title,
                source_url=source.url,
                extraction_date=datetime.now().isoformat(),
                quality_score=float(data.get("quality_score", 50)),
            )
        except Exception as e:
            logger.debug(f"解析AI知识响应失败: {e}")
            return ExtractedKnowledge(
                strategy_type="未知",
                core_logic="解析失败",
                source_platform=source.platform,
                source_title=source.title,
                source_url=source.url,
                extraction_date=datetime.now().isoformat(),
            )

    # ─── 学习流程 ───

    def learn_from_arxiv(self, keyword: str = None, limit: int = 5) -> List[Dict]:
        """从arxiv论文学习策略"""
        papers = self.search_arxiv(keyword, limit)
        return self._learn_from_sources(papers)

    def learn_from_github(self, keyword: str = None, limit: int = 5) -> List[Dict]:
        """从GitHub学习策略"""
        repos = self.search_github(keyword, limit)
        return self._learn_from_sources(repos)

    def learn_from_community(self, keyword: str = None,
                             platforms: List[str] = None, limit: int = 5) -> List[Dict]:
        """从量化社区学习策略"""
        strategies = self.search_community(keyword, platforms, limit)
        return self._learn_from_sources(strategies)

    def learn_from_all_sources(self, keyword: str = "量化策略", limit_per_source: int = 3) -> Dict[str, List[Dict]]:
        """
        从所有来源学习策略

        Returns:
            {"arxiv": [...], "github": [...], "community": [...], "total": N}
        """
        results = {}

        # arxiv（用英文搜索）
        en_keyword = self._to_english_keyword(keyword)
        try:
            results["arxiv"] = self.learn_from_arxiv(en_keyword, limit_per_source)
        except Exception as e:
            logger.warning(f"arxiv学习失败: {e}")
            results["arxiv"] = []

        # GitHub
        try:
            results["github"] = self.learn_from_github(keyword, limit_per_source)
        except Exception as e:
            logger.warning(f"GitHub学习失败: {e}")
            results["github"] = []

        # 量化社区
        try:
            results["community"] = self.learn_from_community(keyword, limit=limit_per_source)
        except Exception as e:
            logger.warning(f"社区学习失败: {e}")
            results["community"] = []

        total = sum(len(v) for v in results.values())
        results["total"] = total

        self._save_learned()
        return results

    def _learn_from_sources(self, sources: List[StrategySource]) -> List[Dict]:
        """对一组策略来源执行学习流程"""
        learned = []

        for source in sources:
            # 去重检查
            exists = any(
                item.get("strategy", {}).get("url") == source.url and
                item.get("strategy", {}).get("platform") == source.platform
                for item in self.learned_strategies
            )
            if exists:
                continue

            # 获取详情（GitHub可获取代码）
            if source.platform == "github" and source.extra.get("raw_url"):
                raw_code = self.github_searcher.fetch_raw_code(source.extra["raw_url"])
                if raw_code:
                    source.code = raw_code

            # AI提取知识
            knowledge = self.extract_knowledge(source)
            if not knowledge:
                continue

            entry = {
                "strategy": asdict(source),
                "knowledge": asdict(knowledge),
                "learned_at": datetime.now().isoformat(),
            }

            self.learned_strategies.append(entry)
            learned.append(entry)

            time.sleep(random.uniform(0.3, 1.0))

        if learned:
            self._save_learned()

        return learned

    def _to_english_keyword(self, keyword: str) -> str:
        """将中文关键词转换为英文（用于arxiv搜索）"""
        mapping = {
            "量化": "quantitative",
            "交易": "trading",
            "策略": "strategy",
            "股票": "stock",
            "预测": "prediction",
            "回测": "backtest",
            "因子": "factor",
            "动量": "momentum",
            "均值回归": "mean reversion",
            "机器学习": "machine learning",
            "深度学习": "deep learning",
            "选股": "stock selection",
            "择时": "market timing",
            "多因子": "multi-factor",
        }

        result = keyword
        for cn, en in mapping.items():
            result = result.replace(cn, en)
        return result or "quantitative trading strategy"

    # ─── 推荐 ───

    def get_recommendations(self, market_condition: str = None,
                            top_n: int = 10) -> List[Dict]:
        """
        获取策略推荐

        Args:
            market_condition: 市场环境（牛市/熊市/震荡市）
            top_n: 返回数量
        """
        if not self.learned_strategies:
            return []

        scored = []
        for item in self.learned_strategies:
            knowledge = item.get("knowledge", {})
            strategy = item.get("strategy", {})

            # 市场环境过滤
            if market_condition and market_condition != "不确定":
                cond = knowledge.get("market_condition", "")
                if cond and market_condition not in cond:
                    continue

            score = self._calculate_score(strategy, knowledge)
            scored.append({**item, "recommend_score": score})

        scored.sort(key=lambda x: x.get("recommend_score", 0), reverse=True)
        return scored[:top_n]

    def _calculate_score(self, strategy: Dict, knowledge: Dict) -> float:
        """计算推荐分数"""
        score = 0.0

        # 来源权重
        platform = strategy.get("platform", "")
        if platform == "arxiv":
            score += 3.0  # 论文权威性高
        elif platform == "github":
            score += 2.0 + min(strategy.get("like_count", 0) / 1000, 3.0)  # Star加权
        elif platform in ["joinquant", "ricequant"]:
            score += 2.0  # 专业平台
        else:
            score += 1.0

        # 知识完整性
        if knowledge.get("core_logic") and knowledge["core_logic"] != "未提取到核心逻辑":
            score += 2.0
        if knowledge.get("indicators") and len(knowledge["indicators"]) > 0:
            score += 1.0
        if knowledge.get("risk_control") and knowledge["risk_control"] != "未提及":
            score += 1.0
        if knowledge.get("key_factors") and len(knowledge["key_factors"]) > 0:
            score += 1.0

        # AI质量评分
        quality = float(knowledge.get("quality_score", 50))
        score += quality / 20  # 0-5分

        return round(score, 2)

    # ─── 统计 ───

    def get_stats(self) -> Dict:
        """获取学习统计"""
        total = len(self.learned_strategies)
        by_platform = {}
        by_type = {}

        for item in self.learned_strategies:
            platform = item.get("strategy", {}).get("platform", "unknown")
            by_platform[platform] = by_platform.get(platform, 0) + 1

            stype = item.get("knowledge", {}).get("strategy_type", "未知")
            by_type[stype] = by_type.get(stype, 0) + 1

        return {
            "total": total,
            "by_platform": by_platform,
            "by_type": by_type,
        }

    def get_recent_learned(self, n: int = 20) -> List[Dict]:
        """获取最近学习的策略"""
        return self.learned_strategies[-n:] if self.learned_strategies else []


# ═══════════════════════════════════════════════
# 向主知识库添加策略
# ═══════════════════════════════════════════════

def add_to_main_knowledge_base(learned_item: Dict, brain_learner=None) -> bool:
    """
    将多源学习的策略添加到主知识库（StrategyLearner.knowledge_base）

    Args:
        learned_item: 多源学习的策略条目
        brain_learner: StrategyLearner实例（如果为None则自动创建）

    Returns:
        是否成功
    """
    if brain_learner is None:
        try:
            from core.quant_brain import StrategyLearner
            brain_learner = StrategyLearner()
        except Exception as e:
            logger.error(f"无法创建StrategyLearner: {e}")
            return False

    knowledge = learned_item.get("knowledge", {})
    strategy = learned_item.get("strategy", {})

    # 构建策略名
    name = strategy.get("title", "")[:50]
    if len(name) > 50:
        name = name[:47] + "..."
    if not name:
        name = f"多源策略_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 构建策略代码
    source_code = strategy.get("code", "")
    if not source_code:
        # 从知识构建伪代码注释
        core_logic = knowledge.get("core_logic", "")
        indicators = ", ".join(knowledge.get("indicators", []))
        risk = knowledge.get("risk_control", "")
        source_code = f"""# 多源策略: {strategy.get('title', '未知')}
# 来源: {strategy.get('platform', '未知')} - {strategy.get('url', '')}
# 策略类型: {knowledge.get('strategy_type', '未知')}
# 学到时间: {datetime.now().strftime('%Y-%m-%d')}

# === 核心逻辑 ===
# {core_logic}

# === 技术指标 ===
# {indicators}

# === 风险控制 ===
# {risk}

# === 改进建议 ===
# {knowledge.get('improvement_suggestions', '')}

# 注意: 此策略从论文/社区学习提取，需要根据以下因子实现Backtrader代码:
# 关键因子: {', '.join(knowledge.get('key_factors', []))}
"""

    # 去重
    for kb in brain_learner.knowledge_base:
        if kb.source == f"multi_source/{strategy.get('platform', 'unknown')}" and \
           strategy.get("url", "") in (kb.description or ""):
            logger.info(f"策略已在主知识库中: {name}")
            return False

    # 添加到主知识库
    from core.quant_brain import StrategyKnowledge
    kb_entry = StrategyKnowledge(
        name=name,
        category=knowledge.get("strategy_type", "多源学习"),
        source=f"multi_source/{strategy.get('platform', 'unknown')}",
        code=source_code,
        description=f"来源: {strategy.get('platform', '未知')} | {strategy.get('title', '')[:100]} | {strategy.get('url', '')}",
        factors=knowledge.get("indicators", []) + knowledge.get("key_factors", []),
        quality_score=float(knowledge.get("quality_score", 50)),
        learned_at=datetime.now().strftime("%Y-%m-%d"),
    )

    brain_learner.knowledge_base.append(kb_entry)

    # 记录学习日志
    from core.quant_brain import LearningRecord
    brain_learner.learning_log.append(LearningRecord(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        action="learn",
        strategy=name,
        result=f"从{strategy.get('platform', '未知')}学习，质量评分{kb_entry.quality_score:.0f}",
        metrics={"source": strategy.get("platform"), "quality": kb_entry.quality_score},
    ))

    brain_learner._save_data()
    return True


# ═══════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════

_learner_instance = None

def get_multi_source_learner() -> MultiSourceStrategyLearner:
    """获取多源策略学习器单例"""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = MultiSourceStrategyLearner()
    return _learner_instance
