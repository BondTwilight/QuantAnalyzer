"""
🧬 全自动策略自进化引擎 — AutoEvolutionEngine

闭环流程:
  搜索策略 → AI提取知识 → 生成可执行代码 → 自动回测 → 评估打分
       ↑                                                      ↓
       ←← 筛选最佳策略 → AI优化迭代 → 提取核心因子 → 因子组合 ←←←

Phase 1: 策略发现（arXiv/GitHub/社区/AI生成）
Phase 2: 策略代码生成（LLM + Backtrader）
Phase 3: 自动回测验证（多标的 + 指标提取）
Phase 4: 因子提取与管理（自动提取 + IC计算）
Phase 5: 策略组合优化（加权ensemble + 回测对比）
"""

import json
import re
import hashlib
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# 数据目录
EVOLUTION_DIR = Path(__file__).parent.parent / "data"
EVOLUTION_DIR.mkdir(exist_ok=True)

# 进化状态持久化文件
EVOLUTION_STATE_FILE = EVOLUTION_DIR / "evolution_state.json"
EVOLUTION_LOG_FILE = EVOLUTION_DIR / "evolution_log.json"
FACTOR_DB_FILE = EVOLUTION_DIR / "factor_database.json"
COMBO_STRATEGY_FILE = EVOLUTION_DIR / "combo_strategies.json"


# ═══════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════

@dataclass
class BacktestMetrics:
    """回测指标"""
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profit_loss_ratio: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)

    def composite_score(self) -> float:
        """综合评分（0-100），基于多维度加权"""
        # 年化收益贡献（满分30）
        ret_score = min(30, max(0, self.annual_return * 10))

        # 夏普比率贡献（满分25），夏普>2算优秀
        sharpe_score = min(25, max(0, self.sharpe_ratio * 12.5))

        # 最大回撤惩罚（满分20），回撤越小越好
        dd_score = max(0, 20 - self.max_drawdown * 100)

        # 胜率贡献（满分15）
        win_score = min(15, self.win_rate * 15)

        # 交易频率合理性（满分10），不要太少也不要太多
        if self.total_trades < 3:
            freq_score = 0
        elif self.total_trades > 500:
            freq_score = 2
        else:
            freq_score = 10

        total = ret_score + sharpe_score + dd_score + win_score + freq_score
        return round(min(100, max(0, total)), 1)


@dataclass
class EvolutionRecord:
    """进化记录"""
    cycle_id: int = 0
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"  # pending, running, completed, failed
    phase: str = ""
    phase_progress: float = 0.0  # 0-100
    strategies_discovered: int = 0
    strategies_generated: int = 0
    strategies_backtested: int = 0
    strategies_passed: int = 0
    strategies_optimized: int = 0
    factors_extracted: int = 0
    combo_created: bool = False
    best_strategy_name: str = ""
    best_strategy_score: float = 0.0
    error: str = ""
    details: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StrategyCandidate:
    """策略候选"""
    name: str = ""
    source: str = ""
    category: str = ""
    code: str = ""
    description: str = ""
    factors: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    backtest_metrics: Optional[BacktestMetrics] = None
    composite_score: float = 0.0
    is_optimized: bool = False
    generation: int = 0  # 第几轮进化产生
    created_at: str = ""

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["backtest_metrics"] = self.backtest_metrics.to_dict() if self.backtest_metrics else None
        return d


# ═══════════════════════════════════════════════
# 搜索关键词库
# ═══════════════════════════════════════════════

SEARCH_KEYWORDS = [
    # 中文
    "A股量化策略", "动量因子策略", "多因子选股", "趋势跟踪策略",
    "均值回归策略", "布林带策略", "MACD优化", "RSI超买超卖",
    "量价分析", "板块轮动策略", "配对交易", "统计套利",
    "机器学习选股", "深度学习量化", "强化学习交易",
    # 英文
    "momentum strategy", "mean reversion", "pairs trading",
    "factor investing", "trend following", "breakout strategy",
    "volatility trading", "machine learning stock",
    "quantitative trading strategy", "backtrader strategy",
    "alpha factor", "statistical arbitrage",
]


# ═══════════════════════════════════════════════
# 用于回测的默认股票池
# ═══════════════════════════════════════════════

BACKTEST_STOCKS = [
    ("000001", "平安银行"), ("000333", "美的集团"), ("000651", "格力电器"),
    ("000858", "五粮液"), ("002594", "比亚迪"), ("600036", "招商银行"),
    ("600309", "万华化学"), ("600519", "贵州茅台"), ("601318", "中国平安"),
    ("300750", "宁德时代"),
]


# ═══════════════════════════════════════════════
# 核心引擎
# ═══════════════════════════════════════════════

class AutoEvolutionEngine:
    """全自动策略自进化引擎

    核心闭环: 搜索 → 学习 → 回测 → 评估 → 优化 → 因子提取 → 组合
    """

    def __init__(self):
        self.cycle_count = 0
        self.state: Dict = {}
        self.log: List[EvolutionRecord] = []
        self.candidates: List[StrategyCandidate] = []
        self._load_state()

    # ─── 持久化 ───

    def _load_state(self):
        """加载进化状态"""
        if EVOLUTION_STATE_FILE.exists():
            try:
                self.state = json.loads(EVOLUTION_STATE_FILE.read_text(encoding="utf-8"))
                self.cycle_count = self.state.get("cycle_count", 0)
                # 恢复候选策略
                for cd in self.state.get("candidates", []):
                    try:
                        bt = None
                        if cd.get("backtest_metrics"):
                            bt = BacktestMetrics(**cd["backtest_metrics"])
                        self.candidates.append(StrategyCandidate(
                            name=cd.get("name", ""),
                            source=cd.get("source", ""),
                            category=cd.get("category", ""),
                            code=cd.get("code", ""),
                            description=cd.get("description", ""),
                            factors=cd.get("factors", []),
                            quality_score=cd.get("quality_score", 0),
                            backtest_metrics=bt,
                            composite_score=cd.get("composite_score", 0),
                            is_optimized=cd.get("is_optimized", False),
                            generation=cd.get("generation", 0),
                            created_at=cd.get("created_at", ""),
                        ))
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"加载进化状态失败: {e}")
        if EVOLUTION_LOG_FILE.exists():
            try:
                for d in json.loads(EVOLUTION_LOG_FILE.read_text(encoding="utf-8")):
                    self.log.append(EvolutionRecord(**d))
            except Exception as e:
                logger.warning(f"加载进化日志失败: {e}")

    def _save_state(self):
        """保存进化状态"""
        self.state["cycle_count"] = self.cycle_count
        self.state["last_run"] = datetime.now().isoformat()
        self.state["total_candidates"] = len(self.candidates)
        # 持久化候选策略
        self.state["candidates"] = [c.to_dict() for c in self.candidates[-50:]]
        try:
            EVOLUTION_STATE_FILE.write_text(
                json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            EVOLUTION_LOG_FILE.write_text(
                json.dumps([r.to_dict() for r in self.log], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"保存进化状态失败: {e}")

    def _record_detail(self, record: EvolutionRecord, phase: str, detail: str):
        """追加运行详情"""
        record.details.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "phase": phase,
            "detail": detail,
        })

    # ─── 进度回调 ───

    def run_cycle(self, progress_cb=None) -> EvolutionRecord:
        """执行一轮完整的进化循环

        Args:
            progress_cb: 回调函数 (progress: float, message: str)

        Returns:
            EvolutionRecord 本次进化记录
        """
        self.cycle_count += 1
        record = EvolutionRecord(
            cycle_id=self.cycle_count,
            started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status="running",
        )

        def _progress(pct: float, msg: str):
            record.phase_progress = pct
            if progress_cb:
                progress_cb(pct, msg)
            logger.info(f"[Cycle {self.cycle_count}] {pct:.0f}% - {msg}")

        try:
            # ═══ Phase 1: 策略发现 ═══
            _progress(2, "🧬 Phase 1/5: 策略发现...")
            record.phase = "discovery"
            discovered = self._phase1_discover(record, _progress)

            if not discovered:
                _progress(15, "⚠️ Phase 1 未发现新策略，尝试AI生成...")
                discovered = self._ai_generate_strategies(record, _progress, count=3)

            record.strategies_discovered = len(discovered)
            _progress(18, f"✅ Phase 1 完成，发现 {len(discovered)} 个策略候选")

            # ═══ Phase 2: 代码生成与审计 ═══
            _progress(20, "🔧 Phase 2/5: 代码生成与审计...")
            record.phase = "code_generation"
            generated = self._phase2_generate_code(discovered, record, _progress)
            record.strategies_generated = len(generated)
            _progress(40, f"✅ Phase 2 完成，生成 {len(generated)} 个可执行策略")

            if not generated:
                _progress(100, "❌ 没有可回测的策略，本轮终止")
                record.status = "completed"
                record.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log.append(record)
                self._save_state()
                return record

            # ═══ Phase 3: 自动回测验证 ═══
            _progress(42, "📊 Phase 3/5: 自动回测验证...")
            record.phase = "backtest"
            backtested = self._phase3_backtest(generated, record, _progress)
            record.strategies_backtested = len(backtested)
            _progress(65, f"✅ Phase 3 完成，回测 {len(backtested)} 个策略")

            # 筛选通过的策略
            passed = [s for s in backtested if s.composite_score >= 30]
            record.strategies_passed = len(passed)
            _progress(68, f"筛选通过: {len(passed)}/{len(backtested)} (composite_score >= 30)")

            # ═══ Phase 4: AI优化迭代 ═══
            _progress(70, "🤖 Phase 4/5: AI优化迭代...")
            record.phase = "optimize"
            optimized = self._phase4_optimize(passed[:5], record, _progress)  # 只优化Top5
            record.strategies_optimized = len(optimized)
            _progress(85, f"✅ Phase 4 完成，优化 {len(optimized)} 个策略")

            # ═══ Phase 5: 因子提取 + 策略组合 ═══
            _progress(87, "🧪 Phase 5/5: 因子提取与策略组合...")
            record.phase = "factor_and_combo"

            # 提取因子
            all_good = passed + optimized
            factors = self._extract_factors(all_good, record)
            record.factors_extracted = len(factors)
            _progress(92, f"提取 {len(factors)} 个因子")

            # 策略组合
            if len(all_good) >= 2:
                combo_ok = self._try_create_combo(all_good, record)
                record.combo_created = combo_ok

            # 记录最佳策略
            if all_good:
                best = max(all_good, key=lambda s: s.composite_score)
                record.best_strategy_name = best.name
                record.best_strategy_score = best.composite_score

            # 保存到主策略库
            self._sync_to_main_knowledge_base(all_good)

            # 将所有高质量策略保存到引擎候选列表
            for cand in all_good:
                if cand.composite_score >= 30:
                    # 去重
                    exists = any(c.name == cand.name for c in self.candidates)
                    if not exists:
                        self.candidates.append(cand)

            _progress(100, "🎉 进化循环完成！")

        except Exception as e:
            logger.error(f"进化循环异常: {e}\n{traceback.format_exc()}")
            record.status = "failed"
            record.error = str(e)
            _progress(100, f"❌ 进化失败: {e}")
        else:
            record.status = "completed"

        record.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log.append(record)
        self._save_state()
        return record

    # ═══════════════════════════════════════════════
    # Phase 1: 策略发现
    # ═══════════════════════════════════════════════

    def _phase1_discover(self, record: EvolutionRecord, _progress) -> List[Dict]:
        """从多个来源发现策略"""
        candidates = []

        # 随机选3个关键词搜索
        import random
        keywords = random.sample(SEARCH_KEYWORDS, min(3, len(SEARCH_KEYWORDS)))

        for i, kw in enumerate(keywords):
            pct = 3 + (i / 3) * 13
            _progress(pct, f"搜索: {kw}")

            # 尝试多源学习
            try:
                results = self._search_from_sources(kw)
                candidates.extend(results)
                self._record_detail(record, "discovery",
                    f"关键词 '{kw}' 发现 {len(results)} 个策略")
            except Exception as e:
                logger.warning(f"搜索 '{kw}' 失败: {e}")
                self._record_detail(record, "discovery", f"搜索 '{kw}' 失败: {e}")

        return candidates

    def _search_from_sources(self, keyword: str) -> List[Dict]:
        """从多个来源搜索策略"""
        results = []

        # 来源1: GitHub爬取
        try:
            from core.strategy_crawler import StrategyCrawler
            crawler = StrategyCrawler()
            strategies = crawler.crawl_all()
            for s in strategies:
                if s.code and s.backtest_ready:
                    results.append({
                        "name": s.name_cn or s.name,
                        "source": f"GitHub/{s.source}",
                        "category": s.category,
                        "code": s.code,
                        "description": s.description,
                        "factors": s.factors or [],
                        "quality_score": s.quality_score * 10,
                    })
        except Exception as e:
            logger.debug(f"GitHub搜索失败: {e}")

        # 来源2: arXiv论文
        try:
            from core.multi_source_strategy import get_multi_source_learner
            learner = get_multi_source_learner()
            en_kw = learner._to_english_keyword(keyword) if hasattr(learner, '_to_english_keyword') else keyword
            arxiv_results = learner.learn_from_arxiv(en_kw, limit=2)
            for entry in arxiv_results:
                results.append({
                    "name": entry.get("name", f"arXiv_{entry.get('id', '')[:8]}"),
                    "source": "arXiv",
                    "category": entry.get("category", "论文策略"),
                    "code": entry.get("code", ""),
                    "description": entry.get("description", ""),
                    "factors": entry.get("factors", []),
                    "quality_score": entry.get("quality_score", 50),
                })
        except Exception as e:
            logger.debug(f"arXiv搜索失败: {e}")

        # 来源3: 量化社区
        try:
            from core.multi_source_strategy import get_multi_source_learner
            learner = get_multi_source_learner()
            community_results = learner.learn_from_community(keyword, limit=2)
            for entry in community_results:
                results.append({
                    "name": entry.get("name", f"社区_{entry.get('id', '')[:8]}"),
                    "source": f"社区/{entry.get('source', 'unknown')}",
                    "category": entry.get("category", "社区策略"),
                    "code": entry.get("code", ""),
                    "description": entry.get("description", ""),
                    "factors": entry.get("factors", []),
                    "quality_score": entry.get("quality_score", 50),
                })
        except Exception as e:
            logger.debug(f"社区搜索失败: {e}")

        return results

    def _ai_generate_strategies(self, record: EvolutionRecord, _progress, count: int = 3) -> List[Dict]:
        """用AI直接生成策略作为后备"""
        results = []

        # 多样化提示
        prompts = [
            "生成一个基于多因子评分的A股量化策略，包含至少3个技术因子和1个量价因子",
            "生成一个趋势跟踪+均值回归混合策略，适合A股震荡市",
            "生成一个基于波动率突破的策略，使用ATR动态止损",
            "生成一个基于MACD+布林带的组合策略，加入成交量确认",
            "生成一个基于RSI和KDJ的超买超卖反转策略，适合短线交易",
        ]

        import random
        selected = random.sample(prompts, min(count, len(prompts)))

        for i, prompt in enumerate(selected):
            pct = 5 + (i / count) * 10
            _progress(pct, f"AI生成策略 {i+1}/{count}...")

            try:
                from core.llm_manager import get_llm_manager
                llm = get_llm_manager()
                code = llm.generate_strategy(prompt, temperature=0.9)

                if code:
                    code = self._extract_code_block(code)
                    if code and "class " in code and "def next" in code:
                        results.append({
                            "name": self._extract_strategy_name(code) or f"AI生成_{self.cycle_count}_{i+1}",
                            "source": "AI生成",
                            "category": "AI生成",
                            "code": code,
                            "description": prompt[:100],
                            "factors": ["AI生成"],
                            "quality_score": 50.0,
                        })
                        self._record_detail(record, "discovery", f"AI生成策略: {results[-1]['name']}")
            except Exception as e:
                logger.warning(f"AI生成失败: {e}")

        return results

    # ═══════════════════════════════════════════════
    # Phase 2: 代码生成与审计
    # ═══════════════════════════════════════════════

    def _phase2_generate_code(self, discovered: List[Dict], record: EvolutionRecord,
                              _progress) -> List[StrategyCandidate]:
        """将发现的策略转化为可回测的Backtrader代码"""
        generated = []

        for i, item in enumerate(discovered):
            pct = 22 + (i / max(len(discovered), 1)) * 16
            _progress(pct, f"审计策略: {item.get('name', '?')}")

            # 已有代码的，直接验证
            code = item.get("code", "")
            if code and "class " in code and "def next" in code:
                candidate = StrategyCandidate(
                    name=item.get("name", f"策略_{i+1}"),
                    source=item.get("source", "unknown"),
                    category=item.get("category", ""),
                    code=code,
                    description=item.get("description", ""),
                    factors=item.get("factors", []),
                    quality_score=item.get("quality_score", 50),
                    generation=self.cycle_count,
                    created_at=datetime.now().strftime("%Y-%m-%d"),
                )
                generated.append(candidate)
                self._record_detail(record, "code_generation",
                    f"策略 '{candidate.name}' 代码验证通过")
                continue

            # 没有代码的，用AI从描述生成
            description = item.get("description", item.get("name", ""))
            if not description:
                continue

            try:
                from core.llm_manager import get_llm_manager
                llm = get_llm_manager()

                gen_prompt = f"""请根据以下策略描述，生成一个完整的Backtrader策略代码。

策略描述: {description}
策略分类: {item.get('category', '未知')}

要求:
1. 继承 bt.Strategy
2. 包含清晰的买入和卖出逻辑
3. 适合A股T+1规则
4. 加入止损逻辑
5. 直接输出代码，不要解释"""

                code = llm.generate_strategy(gen_prompt, temperature=0.7)
                if code:
                    code = self._extract_code_block(code)
                    if code and "class " in code and "def next" in code:
                        candidate = StrategyCandidate(
                            name=item.get("name", f"AI转化_{i+1}"),
                            source=item.get("source", "AI转化"),
                            category=item.get("category", ""),
                            code=code,
                            description=description,
                            factors=item.get("factors", []),
                            quality_score=50.0,
                            generation=self.cycle_count,
                            created_at=datetime.now().strftime("%Y-%m-%d"),
                        )
                        generated.append(candidate)
                        self._record_detail(record, "code_generation",
                            f"AI转化策略 '{candidate.name}' 成功")
            except Exception as e:
                logger.warning(f"代码生成失败: {e}")

        return generated

    # ═══════════════════════════════════════════════
    # Phase 3: 自动回测验证
    # ═══════════════════════════════════════════════

    def _phase3_backtest(self, candidates: List[StrategyCandidate],
                         record: EvolutionRecord, _progress) -> List[StrategyCandidate]:
        """对每个候选策略进行多标的回测"""
        backtested = []
        total = len(candidates)

        for i, cand in enumerate(candidates):
            pct = 44 + (i / max(total, 1)) * 18
            _progress(pct, f"回测: {cand.name} ({i+1}/{total})")

            try:
                metrics = self._backtest_single_strategy(cand.code)
                if metrics:
                    cand.backtest_metrics = metrics
                    cand.composite_score = metrics.composite_score()
                    backtested.append(cand)

                    self._record_detail(record, "backtest",
                        f"{cand.name}: 年化={metrics.annual_return:.1%} "
                        f"夏普={metrics.sharpe_ratio:.2f} "
                        f"回撤={metrics.max_drawdown:.1%} "
                        f"综合={cand.composite_score:.1f}")
                else:
                    self._record_detail(record, "backtest",
                        f"{cand.name}: 回测失败或无交易")
            except Exception as e:
                logger.warning(f"回测 {cand.name} 失败: {e}")
                self._record_detail(record, "backtest", f"{cand.name}: 异常 {e}")

        # 按综合评分排序
        backtested.sort(key=lambda s: -s.composite_score)
        return backtested

    def _backtest_single_strategy(self, code: str) -> Optional[BacktestMetrics]:
        """对单策略进行多标的回测，返回平均指标"""
        import backtrader as bt
        from core.engine import BacktestEngine
        from core.quant_brain import DataProvider

        # 动态加载策略类
        namespace = {}
        try:
            exec(code, namespace)
        except Exception:
            return None

        strategy_class = None
        for name, obj in namespace.items():
            if isinstance(obj, type) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
                strategy_class = obj
                break

        if not strategy_class:
            return None

        # 在3个标的上回测（平衡速度和可靠性）
        test_stocks = BACKTEST_STOCKS[:3]
        all_metrics = []

        for stock_code, _ in test_stocks:
            try:
                # 获取2年数据
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
                data = DataProvider.get_stock_daily(stock_code, start_date=start_date, end_date=end_date)

                if data is None or data.empty or len(data) < 100:
                    continue

                data = DataProvider.calculate_indicators(data)

                engine = BacktestEngine(initial_cash=100000)
                result = engine.run(strategy_class, data)

                if "error" in result:
                    continue

                metrics = BacktestMetrics(
                    total_return=result.get("total_return", 0),
                    annual_return=result.get("annual_return", 0),
                    sharpe_ratio=result.get("sharpe_ratio", 0) or 0,
                    max_drawdown=result.get("max_drawdown", 0),
                    win_rate=result.get("win_rate", 0),
                    total_trades=result.get("total_trades", 0),
                    profit_loss_ratio=result.get("profit_loss_ratio", 0),
                    volatility=result.get("volatility", 0),
                    calmar_ratio=result.get("calmar_ratio", 0) or 0,
                    sortino_ratio=result.get("sortino_ratio", 0) or 0,
                )

                # 过滤掉没有交易的
                if metrics.total_trades > 0:
                    all_metrics.append(metrics)

            except Exception as e:
                logger.debug(f"回测 {stock_code} 失败: {e}")
                continue

        if not all_metrics:
            return None

        # 返回多标的平均指标
        avg = BacktestMetrics()
        n = len(all_metrics)
        avg.total_return = sum(m.total_return for m in all_metrics) / n
        avg.annual_return = sum(m.annual_return for m in all_metrics) / n
        avg.sharpe_ratio = sum(m.sharpe_ratio for m in all_metrics) / n
        avg.max_drawdown = sum(m.max_drawdown for m in all_metrics) / n
        avg.win_rate = sum(m.win_rate for m in all_metrics) / n
        avg.total_trades = int(sum(m.total_trades for m in all_metrics) / n)
        avg.profit_loss_ratio = sum(m.profit_loss_ratio for m in all_metrics) / n
        avg.volatility = sum(m.volatility for m in all_metrics) / n

        return avg

    # ═══════════════════════════════════════════════
    # Phase 4: AI优化迭代
    # ═══════════════════════════════════════════════

    def _phase4_optimize(self, candidates: List[StrategyCandidate],
                         record: EvolutionRecord, _progress) -> List[StrategyCandidate]:
        """用AI优化表现中等的策略"""
        optimized = []

        for i, cand in enumerate(candidates):
            pct = 72 + (i / max(len(candidates), 1)) * 12
            _progress(pct, f"优化: {cand.name} ({i+1}/{len(candidates)})")

            try:
                from core.llm_manager import get_llm_manager
                llm = get_llm_manager()

                perf_data = cand.backtest_metrics.to_dict() if cand.backtest_metrics else {}

                optimized_code = llm.optimize_strategy(cand.code, perf_data)
                if not optimized_code:
                    self._record_detail(record, "optimize", f"{cand.name}: AI未返回优化结果")
                    continue

                optimized_code = self._extract_code_block(optimized_code)
                if not optimized_code or "class " not in optimized_code:
                    continue

                # 回测优化后的策略
                new_metrics = self._backtest_single_strategy(optimized_code)
                if new_metrics and new_metrics.composite_score() > cand.composite_score:
                    opt_cand = StrategyCandidate(
                        name=f"{cand.name}_V2",
                        source=cand.source,
                        category=cand.category,
                        code=optimized_code,
                        description=f"优化自 {cand.name}",
                        factors=cand.factors[:],
                        quality_score=min(100, cand.quality_score + 10),
                        generation=self.cycle_count,
                        created_at=datetime.now().strftime("%Y-%m-%d"),
                        is_optimized=True,
                    )
                    opt_cand.backtest_metrics = new_metrics
                    opt_cand.composite_score = new_metrics.composite_score()
                    optimized.append(opt_cand)

                    improvement = opt_cand.composite_score - cand.composite_score
                    self._record_detail(record, "optimize",
                        f"{cand.name} → {opt_cand.name}: "
                        f"综合分 {cand.composite_score:.1f} → {opt_cand.composite_score:.1f} (+{improvement:.1f})")
                else:
                    self._record_detail(record, "optimize",
                        f"{cand.name}: 优化后无提升，保留原版")

            except Exception as e:
                logger.warning(f"优化 {cand.name} 失败: {e}")

        return optimized

    # ═══════════════════════════════════════════════
    # Phase 5: 因子提取与策略组合
    # ═══════════════════════════════════════════════

    def _extract_factors(self, candidates: List[StrategyCandidate],
                         record: EvolutionRecord) -> List[Dict]:
        """从策略代码中自动提取因子"""
        factors = []

        for cand in candidates:
            code = cand.code
            # 从代码中提取技术指标
            indicators = set()

            # 常见指标关键词
            indicator_patterns = {
                "SMA": r"\.SMA\s*\(|sma\s*\(|SimpleMovingAverage",
                "EMA": r"\.EMA\s*\(|ema\s*\(|ExponentialMovingAverage",
                "RSI": r"\.RSI\s*\(|rsi\s*\(|RSI",
                "MACD": r"\.MACD\s*\(|macd\s*\(|MACD",
                "BOLL": r"\.BollingerBands|boll|BOLL|bollinger",
                "ATR": r"\.ATR\s*\(|atr\s*\(|ATR",
                "KDJ": r"[Kk][Dd][Jj]|stochastic",
                "OBV": r"\.OBV\s*\(|obv\s*\(|OBV",
                "VWAP": r"[Vv][Ww][Aa][Pp]",
                "CCI": r"\.CCI\s*\(|cci\s*\(",
                "Williams": r"[Ww]illiams%[Rr]|WilliamsR",
                "Volume_MA": r"vol.*ma|volume.*rolling",
                "Price_Momentum": r"pct_change|momentum|roc",
                "Mean_Reversion": r"mean.*revert|zscore|z-score",
            }

            for factor_name, pattern in indicator_patterns.items():
                if re.search(pattern, code, re.IGNORECASE):
                    indicators.add(factor_name)

            # 也从已有factors列表中获取
            for f in cand.factors:
                if f and f != "AI生成":
                    indicators.add(f)

            for ind in indicators:
                factors.append({
                    "name": ind,
                    "source_strategy": cand.name,
                    "composite_score": cand.composite_score,
                    "extracted_at": datetime.now().strftime("%Y-%m-%d"),
                })

        # 保存因子到因子数据库
        try:
            from core.factor_manager import FactorManager
            fm = FactorManager()
            for f in factors:
                fm.add_factor(f["name"], source=f["source_strategy"])
        except ImportError:
            # FactorManager 尚未创建，先跳过
            logger.debug("FactorManager 尚未创建，因子暂存")

        return factors

    def _try_create_combo(self, candidates: List[StrategyCandidate],
                          record: EvolutionRecord) -> bool:
        """尝试创建策略组合"""
        if len(candidates) < 2:
            return False

        # 取Top3策略
        top = sorted(candidates, key=lambda s: -s.composite_score)[:3]
        total_score = sum(s.composite_score for s in top)

        # 按综合评分加权
        combo_desc = f"组合策略: " + " + ".join(
            f"{s.name}({s.composite_score/total_score*100:.0f}%)" for s in top
        )

        self._record_detail(record, "combo", combo_desc)

        # 记录组合策略（实际回测在 StrategyCombiner 中完成）
        combo = {
            "name": f"Combo_V{self.cycle_count}",
            "components": [s.name for s in top],
            "weights": [round(s.composite_score / total_score, 3) for s in top],
            "avg_composite_score": round(sum(s.composite_score for s in top) / len(top), 1),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
        }

        try:
            combos = []
            if COMBO_STRATEGY_FILE.exists():
                combos = json.loads(COMBO_STRATEGY_FILE.read_text(encoding="utf-8"))
            combos.append(combo)
            COMBO_STRATEGY_FILE.write_text(
                json.dumps(combos, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"保存组合策略失败: {e}")

        return True

    # ═══════════════════════════════════════════════
    # 同步到主策略库
    # ═══════════════════════════════════════════════

    def _sync_to_main_knowledge_base(self, candidates: List[StrategyCandidate]):
        """将高质量策略同步到主策略知识库"""
        try:
            from core.quant_brain import StrategyLearner, StrategyKnowledge
            learner = StrategyLearner()

            for cand in candidates:
                # 只同步综合评分 >= 35 的策略
                if cand.composite_score < 35:
                    continue

                # 检查去重
                exists = any(k.name == cand.name for k in learner.knowledge_base)
                if exists:
                    continue

                kb_entry = StrategyKnowledge(
                    name=cand.name,
                    category=cand.category or "自进化",
                    source=cand.source,
                    code=cand.code,
                    description=cand.description,
                    factors=cand.factors,
                    quality_score=cand.composite_score,
                    backtest_result=cand.backtest_metrics.to_dict() if cand.backtest_metrics else {},
                    learned_at=datetime.now().strftime("%Y-%m-%d"),
                    last_optimized=datetime.now().strftime("%Y-%m-%d") if cand.is_optimized else "",
                )
                learner.knowledge_base.append(kb_entry)

            # 记录学习日志
            from core.quant_brain import LearningRecord
            for cand in candidates:
                if cand.composite_score >= 35:
                    learner.learning_log.append(LearningRecord(
                        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                        action="evolution",
                        strategy=cand.name,
                        result=f"第{self.cycle_count}轮自进化，综合分{cand.composite_score:.1f}",
                        metrics=cand.backtest_metrics.to_dict() if cand.backtest_metrics else {},
                    ))

            learner._save_data()
            logger.info(f"同步 {len(candidates)} 个策略到主知识库")

        except Exception as e:
            logger.error(f"同步主知识库失败: {e}")

    # ═══════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════

    @staticmethod
    def _extract_code_block(text: str) -> str:
        """从LLM回复中提取代码块"""
        if not text:
            return ""
        if "```python" in text:
            text = text.split("```python")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return text

    @staticmethod
    def _extract_strategy_name(code: str) -> Optional[str]:
        """从策略代码中提取类名"""
        m = re.search(r"class\s+(\w+(?:Strategy)?)", code)
        return m.group(1) if m else None

    # ═══════════════════════════════════════════════
    # 查询接口（供前端使用）
    # ═══════════════════════════════════════════════

    def get_status(self) -> Dict:
        """获取当前进化状态"""
        return {
            "cycle_count": self.cycle_count,
            "total_candidates": len(self.candidates),
            "last_run": self.state.get("last_run", "从未运行"),
            "recent_cycles": [r.to_dict() for r in self.log[-5:]],
        }

    def get_latest_cycle(self) -> Optional[Dict]:
        """获取最近一次进化结果"""
        if self.log:
            return self.log[-1].to_dict()
        return None

    def get_strategy_ranking(self) -> List[Dict]:
        """获取策略排行榜"""
        ranked = sorted(self.candidates, key=lambda s: -s.composite_score)
        return [s.to_dict() for s in ranked[:20]]

    def get_evolution_history(self, limit: int = 10) -> List[Dict]:
        """获取进化历史"""
        return [r.to_dict() for r in self.log[-limit:]]

    def get_factor_summary(self) -> List[Dict]:
        """获取因子摘要"""
        try:
            if FACTOR_DB_FILE.exists():
                data = json.loads(FACTOR_DB_FILE.read_text(encoding="utf-8"))
                return data.get("factors", [])[:20]
        except Exception:
            pass
        return []


# ═══════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════

_engine_instance = None

def get_evolution_engine() -> AutoEvolutionEngine:
    """获取全局进化引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AutoEvolutionEngine()
    return _engine_instance
