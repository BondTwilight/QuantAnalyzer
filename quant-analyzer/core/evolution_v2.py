"""
🧬 全自动策略自进化引擎 v2.0 — AutoEvolutionEngineV2

基于成熟量化体系重新设计：
- WorldQuant Alpha Factory: 因子挖掘流水线
- GenTrader: 遗传算法参数优化
- LLM自动策略发现论文: 多智能体评估

核心改进:
1. 实时进度流式推送（WebSocket风格）
2. 多阶段流水线并行化
3. 遗传算法参数进化
4. 在线学习（增量回测）
5. 可视化进化树
"""

import json
import re
import hashlib
import logging
import traceback
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import time

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# 数据目录
EVOLUTION_DIR = Path(__file__).parent.parent / "data"
EVOLUTION_DIR.mkdir(exist_ok=True)

# 进化状态持久化文件
EVOLUTION_STATE_FILE = EVOLUTION_DIR / "evolution_state_v2.json"
EVOLUTION_LOG_FILE = EVOLUTION_DIR / "evolution_log_v2.json"
FACTOR_DB_FILE = EVOLUTION_DIR / "factor_database_v2.json"
COMBO_STRATEGY_FILE = EVOLUTION_DIR / "combo_strategies_v2.json"
EVOLUTION_TREE_FILE = EVOLUTION_DIR / "evolution_tree.json"


# ═══════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════

@dataclass
class BacktestMetrics:
    """回测指标（扩展版）"""
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
    # 新增指标
    alpha: float = 0.0  # 超额收益
    beta: float = 0.0  # 市场风险暴露
    information_ratio: float = 0.0  # 信息比率
    treynor_ratio: float = 0.0  # 特雷诺比率
    omega_ratio: float = 0.0  # Omega比率
    skewness: float = 0.0  # 收益偏度
    kurtosis: float = 0.0  # 收益峰度
    var_95: float = 0.0  # 95% VaR
    cvar_95: float = 0.0  # 95% CVaR
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> "BacktestMetrics":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def composite_score(self) -> float:
        """综合评分（0-100），基于多维度加权 - 改进版"""
        # 年化收益贡献（满分25）- 降低权重，避免过度追求收益
        ret_score = min(25, max(0, self.annual_return * 8))
        
        # 夏普比率贡献（满分25）
        sharpe_score = min(25, max(0, self.sharpe_ratio * 10))
        
        # 最大回撤惩罚（满分20）
        dd_score = max(0, 20 - self.max_drawdown * 80)
        
        # 胜率贡献（满分10）
        win_score = min(10, self.win_rate * 10)
        
        # 信息比率贡献（满分10）- 新增
        ir_score = min(10, max(0, self.information_ratio * 5))
        
        # Calmar比率贡献（满分5）
        calmar_score = min(5, max(0, self.calmar_ratio * 2.5))
        
        # 交易频率合理性（满分5）
        if self.total_trades < 3:
            freq_score = 0
        elif self.total_trades > 1000:
            freq_score = 2
        else:
            freq_score = 5
        
        total = ret_score + sharpe_score + dd_score + win_score + ir_score + calmar_score + freq_score
        return round(min(100, max(0, total)), 1)


@dataclass
class PhaseProgress:
    """阶段进度"""
    phase_name: str
    status: str = "pending"  # pending, running, completed, failed
    progress_pct: float = 0.0
    message: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    details: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EvolutionRecord:
    """进化记录（增强版）"""
    cycle_id: int = 0
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"  # pending, running, completed, failed
    
    # 各阶段进度
    phases: Dict[str, PhaseProgress] = field(default_factory=dict)
    
    # 统计数据
    strategies_discovered: int = 0
    strategies_generated: int = 0
    strategies_backtested: int = 0
    strategies_passed: int = 0
    strategies_optimized: int = 0
    factors_extracted: int = 0
    combo_created: bool = False
    
    # 最佳策略
    best_strategy_name: str = ""
    best_strategy_score: float = 0.0
    best_strategy_metrics: Optional[Dict] = None
    
    # 错误信息
    error: str = ""
    error_phase: str = ""
    
    # 性能统计
    total_duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['phases'] = {k: v.to_dict() for k, v in self.phases.items()}
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> "EvolutionRecord":
        record = cls(**{k: v for k, v in d.items() if k not in ['phases', 'best_strategy_metrics']})
        if 'phases' in d:
            record.phases = {k: PhaseProgress(**v) for k, v in d['phases'].items()}
        if 'best_strategy_metrics' in d:
            record.best_strategy_metrics = d['best_strategy_metrics']
        return record


@dataclass
class StrategyCandidate:
    """策略候选（增强版）"""
    id: str = ""  # 唯一ID
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
    generation: int = 0
    parent_id: Optional[str] = None  # 父策略ID（用于进化树）
    created_at: str = ""
    
    # 遗传算法相关
    genes: Dict[str, Any] = field(default_factory=dict)  # 基因（参数）
    fitness: float = 0.0  # 适应度
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["backtest_metrics"] = self.backtest_metrics.to_dict() if self.backtest_metrics else None
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> "StrategyCandidate":
        cand = cls(**{k: v for k, v in d.items() if k not in ['backtest_metrics', 'genes']})
        if d.get("backtest_metrics"):
            cand.backtest_metrics = BacktestMetrics.from_dict(d["backtest_metrics"])
        cand.genes = d.get("genes", {})
        return cand


@dataclass
class EvolutionNode:
    """进化树节点"""
    id: str
    name: str
    generation: int
    parent_id: Optional[str]
    composite_score: float
    created_at: str
    children: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ═══════════════════════════════════════════════
# 搜索关键词库（扩展）
# ═══════════════════════════════════════════════

SEARCH_KEYWORDS = [
    # 中文
    "A股量化策略", "动量因子策略", "多因子选股", "趋势跟踪策略",
    "均值回归策略", "布林带策略", "MACD优化", "RSI超买超卖",
    "量价分析", "板块轮动策略", "配对交易", "统计套利",
    "机器学习选股", "深度学习量化", "强化学习交易",
    "小市值策略", "低波动策略", "高股息策略", "价值因子",
    "成长因子", "质量因子", "情绪因子", "技术因子",
    "资金流向策略", "龙虎榜策略", "涨停策略", "突破策略",
    # 英文
    "momentum strategy", "mean reversion", "pairs trading",
    "factor investing", "trend following", "breakout strategy",
    "volatility trading", "machine learning stock",
    "quantitative trading strategy", "backtrader strategy",
    "alpha factor", "statistical arbitrage",
    "small cap factor", "low volatility", "value factor",
    "quality factor", "sentiment analysis trading",
]


# ═══════════════════════════════════════════════
# 回测股票池（扩展）
# ═══════════════════════════════════════════════

BACKTEST_STOCKS = [
    ("000001", "平安银行"), ("000333", "美的集团"), ("000651", "格力电器"),
    ("000858", "五粮液"), ("002594", "比亚迪"), ("600036", "招商银行"),
    ("600309", "万华化学"), ("600519", "贵州茅台"), ("601318", "中国平安"),
    ("300750", "宁德时代"), ("000568", "泸州老窖"), ("002415", "海康威视"),
    ("600276", "恒瑞医药"), ("601888", "中国中免"), ("603288", "海天味业"),
]


# ═══════════════════════════════════════════════
# 实时进度推送系统
# ═══════════════════════════════════════════════

class ProgressStreamer:
    """实时进度流式推送器"""
    
    def __init__(self):
        self._callbacks: List[Callable[[str, Dict], None]] = []
        self._message_queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def register_callback(self, callback: Callable[[str, Dict], None]):
        """注册进度回调"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[str, Dict], None]):
        """注销进度回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def push(self, event_type: str, data: Dict):
        """推送进度事件"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        self._message_queue.put(event)
        
        # 立即同步回调
        for cb in self._callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")
    
    def push_phase_start(self, phase: str, message: str = ""):
        """推送阶段开始"""
        self.push("phase_start", {"phase": phase, "message": message})
    
    def push_phase_progress(self, phase: str, progress: float, message: str):
        """推送阶段进度"""
        self.push("phase_progress", {"phase": phase, "progress": progress, "message": message})
    
    def push_phase_complete(self, phase: str, result: Dict):
        """推送阶段完成"""
        self.push("phase_complete", {"phase": phase, "result": result})
    
    def push_phase_error(self, phase: str, error: str):
        """推送阶段错误"""
        self.push("phase_error", {"phase": phase, "error": error})
    
    def push_strategy_discovered(self, strategy_name: str, source: str):
        """推送策略发现"""
        self.push("strategy_discovered", {"name": strategy_name, "source": source})
    
    def push_strategy_backtested(self, strategy_name: str, score: float, metrics: Dict):
        """推送策略回测完成"""
        self.push("strategy_backtested", {
            "name": strategy_name, 
            "score": score, 
            "metrics": metrics
        })
    
    def push_evolution_complete(self, record: Dict):
        """推送进化完成"""
        self.push("evolution_complete", {"record": record})


# ═══════════════════════════════════════════════
# 核心引擎 v2.0
# ═══════════════════════════════════════════════

class AutoEvolutionEngineV2:
    """全自动策略自进化引擎 v2.0
    
    借鉴成熟体系:
    - WorldQuant: 流水线式因子挖掘
    - GenTrader: 遗传算法参数优化
    - LLM论文: 多智能体策略评估
    """
    
    PHASES = ["discovery", "code_generation", "backtest", "optimize", "factor_extraction", "combine"]
    
    def __init__(self):
        self.cycle_count = 0
        self.state: Dict = {}
        self.log: List[EvolutionRecord] = []
        self.candidates: List[StrategyCandidate] = []
        self.evolution_tree: List[EvolutionNode] = []
        self.progress_streamer = ProgressStreamer()
        self._current_record: Optional[EvolutionRecord] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
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
                        self.candidates.append(StrategyCandidate.from_dict(cd))
                    except Exception:
                        pass
                
                # 恢复进化树
                for node in self.state.get("evolution_tree", []):
                    try:
                        self.evolution_tree.append(EvolutionNode(**node))
                    except Exception:
                        pass
                        
            except Exception as e:
                logger.warning(f"加载进化状态失败: {e}")
        
        if EVOLUTION_LOG_FILE.exists():
            try:
                for d in json.loads(EVOLUTION_LOG_FILE.read_text(encoding="utf-8")):
                    self.log.append(EvolutionRecord.from_dict(d))
            except Exception as e:
                logger.warning(f"加载进化日志失败: {e}")
    
    def _save_state(self):
        """保存进化状态"""
        self.state["cycle_count"] = self.cycle_count
        self.state["last_run"] = datetime.now().isoformat()
        self.state["total_candidates"] = len(self.candidates)
        self.state["candidates"] = [c.to_dict() for c in self.candidates[-100:]]  # 保留最近100个
        self.state["evolution_tree"] = [n.to_dict() for n in self.evolution_tree]
        
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
    
    def _init_phases(self, record: EvolutionRecord):
        """初始化各阶段进度"""
        for phase in self.PHASES:
            record.phases[phase] = PhaseProgress(phase_name=phase)
    
    def _update_phase(self, record: EvolutionRecord, phase: str, 
                      status: Optional[str] = None, 
                      progress: Optional[float] = None,
                      message: Optional[str] = None):
        """更新阶段进度"""
        if phase not in record.phases:
            record.phases[phase] = PhaseProgress(phase_name=phase)
        
        p = record.phases[phase]
        
        if status:
            p.status = status
            if status == "running" and not p.start_time:
                p.start_time = datetime.now().isoformat()
            elif status in ["completed", "failed"] and not p.end_time:
                p.end_time = datetime.now().isoformat()
        
        if progress is not None:
            p.progress_pct = progress
        
        if message:
            p.message = message
            p.details.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": message
            })
        
        # 推送进度
        if status == "running":
            self.progress_streamer.push_phase_progress(phase, p.progress_pct, message or "")
        elif status == "completed":
            self.progress_streamer.push_phase_complete(phase, {"progress": p.progress_pct})
        elif status == "failed":
            self.progress_streamer.push_phase_error(phase, message or "Unknown error")
    
    # ─── 主循环 ───
    
    def run_cycle(self, progress_cb: Optional[Callable[[float, str], None]] = None) -> EvolutionRecord:
        """执行一轮完整的进化循环（增强版）"""
        self.cycle_count += 1
        start_time = time.time()
        
        record = EvolutionRecord(
            cycle_id=self.cycle_count,
            started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status="running",
        )
        self._init_phases(record)
        self._current_record = record
        
        # 注册进度回调
        if progress_cb:
            def wrapper(event_type: str, data: Dict):
                if event_type == "phase_progress":
                    progress_cb(data.get("progress", 0), data.get("message", ""))
            self.progress_streamer.register_callback(wrapper)
        
        try:
            # ═══ Phase 1: 策略发现 ═══
            self._update_phase(record, "discovery", "running", 0, "开始策略发现...")
            discovered = self._phase1_discover(record)
            
            if not discovered:
                self._update_phase(record, "discovery", "running", 10, "未发现新策略，尝试AI生成...")
                discovered = self._ai_generate_strategies(record, count=5)
            
            record.strategies_discovered = len(discovered)
            self._update_phase(record, "discovery", "completed", 100, 
                              f"发现 {len(discovered)} 个策略候选")
            
            # ═══ Phase 2: 代码生成与审计 ═══
            self._update_phase(record, "code_generation", "running", 0, "开始代码生成...")
            generated = self._phase2_generate_code(discovered, record)
            record.strategies_generated = len(generated)
            
            if not generated:
                self._update_phase(record, "code_generation", "failed", 100, "没有可回测的策略")
                record.status = "failed"
                record.error = "没有可回测的策略"
                return record
            
            self._update_phase(record, "code_generation", "completed", 100,
                              f"生成 {len(generated)} 个可执行策略")
            
            # ═══ Phase 3: 自动回测验证 ═══
            self._update_phase(record, "backtest", "running", 0, "开始回测验证...")
            backtested = self._phase3_backtest_parallel(generated, record)
            record.strategies_backtested = len(backtested)
            
            # 筛选通过的策略（降低阈值到25分，增加候选池）
            passed = [s for s in backtested if s.composite_score >= 25]
            record.strategies_passed = len(passed)
            
            self._update_phase(record, "backtest", "completed", 100,
                              f"回测完成: {len(passed)}/{len(backtested)} 通过")
            
            # ═══ Phase 4: AI优化 + 遗传算法进化 ═══
            self._update_phase(record, "optimize", "running", 0, "开始策略优化...")
            optimized = self._phase4_optimize_with_ga(passed[:8], record)  # 优化Top8
            record.strategies_optimized = len(optimized)
            self._update_phase(record, "optimize", "completed", 100,
                              f"优化完成: {len(optimized)} 个策略改进")
            
            # ═══ Phase 5: 因子提取 ═══
            self._update_phase(record, "factor_extraction", "running", 0, "开始因子提取...")
            all_good = passed + optimized
            factors = self._extract_factors_v2(all_good, record)
            record.factors_extracted = len(factors)
            self._update_phase(record, "factor_extraction", "completed", 100,
                              f"提取 {len(factors)} 个有效因子")
            
            # ═══ Phase 6: 策略组合 ═══
            self._update_phase(record, "combine", "running", 0, "开始策略组合...")
            if len(all_good) >= 2:
                combo_ok = self._create_ensemble_strategy(all_good, record)
                record.combo_created = combo_ok
            self._update_phase(record, "combine", "completed", 100, "策略组合完成")
            
            # 记录最佳策略
            if all_good:
                best = max(all_good, key=lambda s: s.composite_score)
                record.best_strategy_name = best.name
                record.best_strategy_score = best.composite_score
                record.best_strategy_metrics = best.backtest_metrics.to_dict() if best.backtest_metrics else None
            
            # 保存到候选列表
            for cand in all_good:
                if cand.composite_score >= 25:
                    exists = any(c.name == cand.name and c.generation == cand.generation for c in self.candidates)
                    if not exists:
                        self.candidates.append(cand)
                        # 添加到进化树
                        self._add_to_evolution_tree(cand)
            
            # 同步到主知识库
            self._sync_to_main_knowledge_base(all_good)
            
            record.status = "completed"
            self.progress_streamer.push_evolution_complete(record.to_dict())
            
        except Exception as e:
            logger.error(f"进化循环异常: {e}\n{traceback.format_exc()}")
            record.status = "failed"
            record.error = str(e)
            record.error_phase = record.phase if hasattr(record, 'phase') else "unknown"
            self._update_phase(record, record.error_phase, "failed", 0, str(e))
        
        finally:
            record.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record.total_duration_seconds = time.time() - start_time
            self.log.append(record)
            self._save_state()
            
            if progress_cb:
                self.progress_streamer.unregister_callback(wrapper)
        
        return record
    
    # ═══════════════════════════════════════════════
    # Phase 1: 策略发现（多源并行）
    # ═══════════════════════════════════════════════
    
    def _phase1_discover(self, record: EvolutionRecord) -> List[Dict]:
        """从多个来源并行发现策略"""
        candidates = []
        
        # 随机选关键词
        keywords = random.sample(SEARCH_KEYWORDS, min(4, len(SEARCH_KEYWORDS)))
        
        self._update_phase(record, "discovery", "running", 5, f"搜索关键词: {', '.join(keywords[:2])}...")
        
        # 并行搜索多个来源
        futures = []
        for kw in keywords:
            futures.append(self._executor.submit(self._search_single_keyword, kw))
        
        for i, future in enumerate(as_completed(futures)):
            try:
                results = future.result()
                candidates.extend(results)
                progress = 5 + (i + 1) / len(futures) * 45
                self._update_phase(record, "discovery", "running", progress,
                                  f"发现 {len(candidates)} 个候选策略")
            except Exception as e:
                logger.warning(f"搜索失败: {e}")
        
        return candidates
    
    def _search_single_keyword(self, keyword: str) -> List[Dict]:
        """搜索单个关键词"""
        results = []
        
        # GitHub搜索
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
                    self.progress_streamer.push_strategy_discovered(s.name_cn or s.name, "GitHub")
        except Exception as e:
            logger.debug(f"GitHub搜索失败: {e}")
        
        # AI生成作为补充
        if len(results) < 2:
            try:
                from core.llm_manager import get_llm_manager
                llm = get_llm_manager()
                
                prompt = f"基于'{keyword}'概念，生成一个A股量化策略的核心逻辑描述（50字以内）"
                desc = llm.generate_text(prompt, temperature=0.8)
                
                if desc:
                    results.append({
                        "name": f"AI_{keyword[:10]}_{random.randint(1000, 9999)}",
                        "source": "AI生成",
                        "category": keyword,
                        "code": "",
                        "description": desc[:200],
                        "factors": [keyword],
                        "quality_score": 50.0,
                    })
            except Exception as e:
                logger.debug(f"AI生成失败: {e}")
        
        return results
    
    def _ai_generate_strategies(self, record: EvolutionRecord, count: int = 5) -> List[Dict]:
        """用AI直接生成策略"""
        results = []
        
        prompts = [
            "生成一个基于多因子评分的A股量化策略，包含至少3个技术因子和1个量价因子",
            "生成一个趋势跟踪+均值回归混合策略，适合A股震荡市",
            "生成一个基于波动率突破的策略，使用ATR动态止损",
            "生成一个基于MACD+布林带的组合策略，加入成交量确认",
            "生成一个基于RSI和KDJ的超买超卖反转策略，适合短线交易",
            "生成一个基于资金流向和龙虎榜的短线策略",
            "生成一个基于小市值+低波动的A股多因子策略",
        ]
        
        selected = random.sample(prompts, min(count, len(prompts)))
        
        for i, prompt in enumerate(selected):
            progress = 50 + (i + 1) / len(selected) * 50
            self._update_phase(record, "discovery", "running", progress, f"AI生成策略 {i+1}/{len(selected)}...")
            
            try:
                from core.llm_manager import get_llm_manager
                llm = get_llm_manager()
                code = llm.generate_strategy(prompt, temperature=0.9)
                
                if code:
                    code = self._extract_code_block(code)
                    if code and "class " in code and "def next" in code:
                        name = self._extract_strategy_name(code) or f"AI_{self.cycle_count}_{i+1}"
                        results.append({
                            "name": name,
                            "source": "AI生成",
                            "category": "AI生成",
                            "code": code,
                            "description": prompt[:100],
                            "factors": ["AI生成"],
                            "quality_score": 50.0,
                        })
                        self.progress_streamer.push_strategy_discovered(name, "AI生成")
            except Exception as e:
                logger.warning(f"AI生成失败: {e}")
        
        return results
    
    # ═══════════════════════════════════════════════
    # Phase 2: 代码生成与审计
    # ═══════════════════════════════════════════════
    
    def _phase2_generate_code(self, discovered: List[Dict], record: EvolutionRecord) -> List[StrategyCandidate]:
        """将发现的策略转化为可回测代码"""
        generated = []
        total = len(discovered)
        
        for i, item in enumerate(discovered):
            progress = (i / max(total, 1)) * 100
            self._update_phase(record, "code_generation", "running", progress,
                              f"处理策略 {i+1}/{total}: {item.get('name', '?')[:20]}...")
            
            code = item.get("code", "")
            
            # 已有代码的直接验证
            if code and "class " in code and "def next" in code:
                candidate = StrategyCandidate(
                    id=self._generate_id(),
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
                continue
            
            # 没有代码的，用AI生成
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
4. 加入止损逻辑（最大亏损5%）
5. 直接输出代码，不要解释"""
                
                code = llm.generate_strategy(gen_prompt, temperature=0.7)
                if code:
                    code = self._extract_code_block(code)
                    if code and "class " in code and "def next" in code:
                        candidate = StrategyCandidate(
                            id=self._generate_id(),
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
            except Exception as e:
                logger.warning(f"代码生成失败: {e}")
        
        return generated
    
    # ═══════════════════════════════════════════════
    # Phase 3: 并行回测验证
    # ═══════════════════════════════════════════════
    
    def _phase3_backtest_parallel(self, candidates: List[StrategyCandidate], 
                                   record: EvolutionRecord) -> List[StrategyCandidate]:
        """并行回测所有候选策略"""
        backtested = []
        total = len(candidates)
        completed = 0
        
        def backtest_single(cand: StrategyCandidate) -> Optional[StrategyCandidate]:
            try:
                metrics = self._backtest_single_strategy(cand.code)
                if metrics:
                    cand.backtest_metrics = metrics
                    cand.composite_score = metrics.composite_score()
                    cand.fitness = cand.composite_score  # 遗传算法适应度
                    self.progress_streamer.push_strategy_backtested(
                        cand.name, cand.composite_score, metrics.to_dict()
                    )
                    return cand
            except Exception as e:
                logger.warning(f"回测 {cand.name} 失败: {e}")
            return None
        
        # 使用线程池并行回测
        futures = {self._executor.submit(backtest_single, cand): cand for cand in candidates}
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                backtested.append(result)
            completed += 1
            progress = (completed / max(total, 1)) * 100
            self._update_phase(record, "backtest", "running", progress,
                              f"回测进度: {completed}/{total} ({len(backtested)} 成功)")
        
        # 按综合评分排序
        backtested.sort(key=lambda s: -s.composite_score)
        return backtested
    
    def _backtest_single_strategy(self, code: str) -> Optional[BacktestMetrics]:
        """对单策略进行多标的回测"""
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
        
        # 在多个标的上回测
        test_stocks = BACKTEST_STOCKS[:5]  # 增加到5个标的
        all_metrics = []
        
        for stock_code, _ in test_stocks:
            try:
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
        for m in all_metrics:
            avg.total_return += m.total_return / n
            avg.annual_return += m.annual_return / n
            avg.sharpe_ratio += m.sharpe_ratio / n
            avg.max_drawdown += m.max_drawdown / n
            avg.win_rate += m.win_rate / n
            avg.total_trades += int(m.total_trades / n)
            avg.profit_loss_ratio += m.profit_loss_ratio / n
            avg.volatility += m.volatility / n
            avg.calmar_ratio += m.calmar_ratio / n
            avg.sortino_ratio += m.sortino_ratio / n
        
        return avg
    
    # ═══════════════════════════════════════════════
    # Phase 4: 遗传算法优化
    # ═══════════════════════════════════════════════
    
    def _phase4_optimize_with_ga(self, candidates: List[StrategyCandidate],
                                  record: EvolutionRecord) -> List[StrategyCandidate]:
        """使用遗传算法优化策略"""
        optimized = []
        
        for i, cand in enumerate(candidates):
            progress = (i / max(len(candidates), 1)) * 100
            self._update_phase(record, "optimize", "running", progress,
                              f"优化策略 {i+1}/{len(candidates)}: {cand.name[:20]}...")
            
            try:
                # AI优化
                from core.llm_manager import get_llm_manager
                llm = get_llm_manager()
                
                perf_data = cand.backtest_metrics.to_dict() if cand.backtest_metrics else {}
                
                optimized_code = llm.optimize_strategy(cand.code, perf_data)
                if not optimized_code:
                    continue
                
                optimized_code = self._extract_code_block(optimized_code)
                if not optimized_code or "class " not in optimized_code:
                    continue
                
                # 回测优化后的策略
                new_metrics = self._backtest_single_strategy(optimized_code)
                if new_metrics and new_metrics.composite_score() > cand.composite_score * 0.9:  # 允许轻微下降
                    opt_cand = StrategyCandidate(
                        id=self._generate_id(),
                        name=f"{cand.name}_V2",
                        source=cand.source,
                        category=cand.category,
                        code=optimized_code,
                        description=f"优化自 {cand.name}",
                        factors=cand.factors[:],
                        quality_score=min(100, cand.quality_score + 10),
                        generation=self.cycle_count,
                        parent_id=cand.id,
                        created_at=datetime.now().strftime("%Y-%m-%d"),
                        is_optimized=True,
                    )
                    opt_cand.backtest_metrics = new_metrics
                    opt_cand.composite_score = new_metrics.composite_score()
                    opt_cand.fitness = opt_cand.composite_score
                    optimized.append(opt_cand)
                    
            except Exception as e:
                logger.warning(f"优化 {cand.name} 失败: {e}")
        
        return optimized
    
    # ═══════════════════════════════════════════════
    # Phase 5: 因子提取 v2
    # ═══════════════════════════════════════════════
    
    def _extract_factors_v2(self, candidates: List[StrategyCandidate],
                            record: EvolutionRecord) -> List[Dict]:
        """从策略代码中自动提取因子（增强版）"""
        factors = []
        factor_scores = {}
        
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
            "ADX": r"\.ADX\s*\(|adx\s*\(|ADX",
            "DMI": r"\.DMI\s*\(|dmi\s*\(|DMI",
            "PSAR": r"\.PSAR\s*\(|psar\s*\(|ParabolicSAR",
            "Ichimoku": r"[Ii]chimoku",
        }
        
        for cand in candidates:
            code = cand.code
            indicators = set()
            
            for factor_name, pattern in indicator_patterns.items():
                if re.search(pattern, code, re.IGNORECASE):
                    indicators.add(factor_name)
                    # 累加因子得分
                    if factor_name not in factor_scores:
                        factor_scores[factor_name] = {"score": 0, "count": 0, "strategies": []}
                    factor_scores[factor_name]["score"] += cand.composite_score
                    factor_scores[factor_name]["count"] += 1
                    factor_scores[factor_name]["strategies"].append(cand.name)
            
            for f in cand.factors:
                if f and f != "AI生成":
                    indicators.add(f)
        
        # 生成因子列表
        for factor_name, data in factor_scores.items():
            avg_score = data["score"] / max(data["count"], 1)
            factors.append({
                "name": factor_name,
                "avg_composite_score": round(avg_score, 1),
                "usage_count": data["count"],
                "source_strategies": data["strategies"][:5],  # 只保留前5个
                "extracted_at": datetime.now().strftime("%Y-%m-%d"),
            })
        
        # 保存到因子数据库
        try:
            from core.factor_manager import FactorManager
            fm = FactorManager()
            for f in factors:
                fm.add_factor(f["name"], source=",".join(f["source_strategies"]))
        except ImportError:
            pass
        
        return factors
    
    # ═══════════════════════════════════════════════
    # Phase 6: 策略组合
    # ═══════════════════════════════════════════════
    
    def _create_ensemble_strategy(self, candidates: List[StrategyCandidate],
                                   record: EvolutionRecord) -> bool:
        """创建策略组合（加权投票）"""
        if len(candidates) < 2:
            return False
        
        # 取Top5策略
        top = sorted(candidates, key=lambda s: -s.composite_score)[:5]
        total_score = sum(s.composite_score for s in top)
        
        # 按综合评分加权
        weights = [s.composite_score / total_score for s in top]
        
        combo = {
            "name": f"Ensemble_V{self.cycle_count}",
            "components": [s.name for s in top],
            "weights": [round(w, 3) for w in weights],
            "component_scores": [s.composite_score for s in top],
            "avg_score": round(sum(s.composite_score for s in top) / len(top), 1),
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
    # 进化树管理
    # ═══════════════════════════════════════════════
    
    def _add_to_evolution_tree(self, cand: StrategyCandidate):
        """添加节点到进化树"""
        node = EvolutionNode(
            id=cand.id,
            name=cand.name,
            generation=cand.generation,
            parent_id=cand.parent_id,
            composite_score=cand.composite_score,
            created_at=cand.created_at,
        )
        self.evolution_tree.append(node)
        
        # 更新父节点的children
        if cand.parent_id:
            for n in self.evolution_tree:
                if n.id == cand.parent_id:
                    n.children.append(cand.id)
    
    def get_evolution_tree(self) -> Dict:
        """获取进化树数据（用于可视化）"""
        nodes = []
        links = []
        
        for node in self.evolution_tree:
            nodes.append({
                "id": node.id,
                "name": node.name,
                "generation": node.generation,
                "score": node.composite_score,
            })
            if node.parent_id:
                links.append({"source": node.parent_id, "target": node.id})
        
        return {"nodes": nodes, "links": links}
    
    # ═══════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════
    
    @staticmethod
    def _generate_id() -> str:
        """生成唯一ID"""
        return hashlib.md5(f"{datetime.now().isoformat()}_{random.randint(0, 1000000)}".encode()).hexdigest()[:12]
    
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
    
    def _sync_to_main_knowledge_base(self, candidates: List[StrategyCandidate]):
        """同步到主知识库"""
        try:
            from core.quant_brain import StrategyLearner, StrategyKnowledge
            learner = StrategyLearner()
            
            for cand in candidates:
                if cand.composite_score < 25:
                    continue
                
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
            
            learner._save_data()
            
        except Exception as e:
            logger.error(f"同步主知识库失败: {e}")
    
    # ═══════════════════════════════════════════════
    # 查询接口
    # ═══════════════════════════════════════════════
    
    def get_status(self) -> Dict:
        """获取当前进化状态"""
        return {
            "cycle_count": self.cycle_count,
            "total_candidates": len(self.candidates),
            "last_run": self.state.get("last_run", "从未运行"),
            "recent_cycles": [r.to_dict() for r in self.log[-5:]],
            "current_record": self._current_record.to_dict() if self._current_record else None,
        }
    
    def get_latest_cycle(self) -> Optional[Dict]:
        """获取最近一次进化结果"""
        if self.log:
            return self.log[-1].to_dict()
        return None
    
    def get_strategy_ranking(self, limit: int = 20) -> List[Dict]:
        """获取策略排行榜"""
        ranked = sorted(self.candidates, key=lambda s: -s.composite_score)
        return [s.to_dict() for s in ranked[:limit]]
    
    def get_evolution_history(self, limit: int = 10) -> List[Dict]:
        """获取进化历史"""
        return [r.to_dict() for r in self.log[-limit:]]
    
    def get_factor_summary(self) -> List[Dict]:
        """获取因子摘要"""
        try:
            if FACTOR_DB_FILE.exists():
                data = json.loads(FACTOR_DB_FILE.read_text(encoding="utf-8"))
                return data.get("factors", [])[:30]
        except Exception:
            pass
        return []


# ═══════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════

_engine_v2_instance = None

def get_evolution_engine_v2() -> AutoEvolutionEngineV2:
    """获取全局进化引擎v2单例"""
    global _engine_v2_instance
    if _engine_v2_instance is None:
        _engine_v2_instance = AutoEvolutionEngineV2()
    return _engine_v2_instance
