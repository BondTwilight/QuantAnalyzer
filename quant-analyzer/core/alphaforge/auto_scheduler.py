"""
🔄 EvolutionScheduler — 自动进化调度器

核心功能：
1. 自动化进化流程编排（Idea → Factor → Eval → Ensemble）
2. 定时任务（每日/每周自动进化）
3. 进化状态管理和持久化
4. 最佳策略自动更新
5. 进化历史追踪和性能对比

设计参考：AlphaAgent Loop + Qlib Workflow Engine
"""

import json
import logging
import time
import traceback
import threading
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# 数据目录
SCHEDULER_DIR = Path(__file__).parent.parent.parent / "data"
SCHEDULER_DIR.mkdir(exist_ok=True)

SCHEDULER_STATE_FILE = SCHEDULER_DIR / "scheduler_state.json"
EVOLUTION_HISTORY_FILE = SCHEDULER_DIR / "evolution_history.json"
BEST_STRATEGY_FILE = SCHEDULER_DIR / "best_strategy.json"


@dataclass
class EvolutionTask:
    """进化任务"""
    task_id: str = ""
    task_type: str = "full"          # full / quick / factor_only / ensemble_only
    status: str = "pending"          # pending / running / completed / failed
    started_at: str = ""
    completed_at: str = ""
    
    # 进度
    current_phase: str = ""
    progress_pct: float = 0.0
    message: str = ""
    
    # 结果统计
    factors_tested: int = 0
    factors_valid: int = 0
    best_fitness: float = 0.0
    best_expression: str = ""
    ensemble_score: float = 0.0
    
    # 性能
    duration_seconds: float = 0.0
    
    # 错误
    error: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SchedulerConfig:
    """调度器配置"""
    # 进化参数
    gp_population_size: int = 50          # 遗传编程种群大小
    gp_max_generations: int = 20          # 最大进化代数
    max_factors_to_test: int = 100        # 最多测试因子数
    
    # 数据参数
    stock_pool: List[str] = field(default_factory=lambda: [
        "000001", "000333", "600519", "601318", "300750",
        "000858", "002594", "601888", "000568", "600036",
    ])
    lookback_days: int = 730              # 回看2年数据
    
    # 调度参数
    auto_evolve_daily: bool = False       # 每日自动进化
    auto_evolve_weekly: bool = True       # 每周自动进化
    evolve_time: str = "09:30"            # 进化执行时间
    
    # 因子管理
    max_stored_factors: int = 200         # 最多存储因子数
    min_factor_fitness: float = 0.03      # 最低有效因子适应度（降低阈值，避免全部过滤）
    factor_redundancy_threshold: float = 0.8  # 因子冗余阈值
    
    # 组合策略
    ensemble_method: str = "ic_weighted"  # 组合方法
    ensemble_top_n: int = 5               # 取top N因子组合
    
    def to_dict(self) -> Dict:
        return asdict(self)


class EvolutionScheduler:
    """
    自动进化调度器
    
    编排完整的因子挖掘→评估→组合进化流程。
    """
    
    PHASES = [
        "data_loading",       # 数据加载
        "seed_generation",    # 种子因子生成
        "gp_evolution",       # 遗传编程进化
        "factor_evaluation",  # 因子评估
        "ensemble_building",  # 组合策略构建
        "validation",         # 验证
        "update_best",        # 更新最佳策略
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = SchedulerConfig()
        if config:
            for k, v in config.items():
                if hasattr(self.config, k):
                    setattr(self.config, k, v)
        
        self.state: Dict = {}
        self.history: List[EvolutionTask] = []
        self._current_task: Optional[EvolutionTask] = None
        self._is_running = False
        self._lock = threading.Lock()
        
        # 回调
        self._progress_callback: Optional[Callable] = None
        
        # 延迟导入核心模块
        self._factor_engine = None
        self._gp = None
        self._analyzer = None
        self._ensemble = None
        
        self._load_state()
    
    def _load_state(self):
        """加载调度器状态"""
        if SCHEDULER_STATE_FILE.exists():
            try:
                self.state = json.loads(SCHEDULER_STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        if EVOLUTION_HISTORY_FILE.exists():
            try:
                for d in json.loads(EVOLUTION_HISTORY_FILE.read_text(encoding="utf-8")):
                    self.history.append(EvolutionTask(**d))
            except Exception:
                pass
    
    def _save_state(self):
        """保存调度器状态"""
        try:
            SCHEDULER_STATE_FILE.write_text(
                json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            EVOLUTION_HISTORY_FILE.write_text(
                json.dumps([t.to_dict() for t in self.history], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调"""
        self._progress_callback = callback
    
    def _report_progress(self, phase: str, progress: float, message: str):
        """报告进度"""
        if self._current_task:
            self._current_task.current_phase = phase
            self._current_task.progress_pct = progress
            self._current_task.message = message
        
        if self._progress_callback:
            try:
                self._progress_callback(progress, f"[{phase}] {message}")
            except Exception:
                pass
        
        logger.info(f"[{phase}] {progress:.0f}% - {message}")
    
    # ═══════════════════════════════════════════════
    # 主进化流程
    # ═══════════════════════════════════════════════
    
    def run_evolution(self, task_type: str = "full",
                      progress_cb: Optional[Callable] = None) -> EvolutionTask:
        """
        执行一轮进化
        
        Args:
            task_type: full(完整)/quick(快速)/factor_only(仅因子)/ensemble_only(仅组合)
            progress_cb: 进度回调函数 (progress_pct, message) -> None
            
        Returns:
            EvolutionTask
        """
        if self._is_running:
            raise RuntimeError("已有进化任务在运行")
        
        with self._lock:
            self._is_running = True
            self._progress_callback = progress_cb
        
        task = EvolutionTask(
            task_id=f"evo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            task_type=task_type,
            started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status="running",
        )
        self._current_task = task
        start_time = time.time()
        
        try:
            # ═══ Phase 1: 数据加载（多股票） ═══
            self._report_progress("data_loading", 5, "加载多股票历史数据...")
            multi_data = self._load_data()
            if multi_data is None:
                raise ValueError("无法加载历史数据")
            stock_count = len(multi_data)
            total_rows = sum(len(df) for df in multi_data.values())
            self._report_progress("data_loading", 15, f"数据加载完成: {stock_count} 只股票, {total_rows} 条记录")
            
            # ═══ Phase 2: 种子因子生成 ═══
            self._report_progress("seed_generation", 20, "生成种子因子...")
            seed_factors = self._generate_seed_factors()
            self._report_progress("seed_generation", 30, f"生成 {len(seed_factors)} 个种子因子")
            
            # ═══ Phase 3: 遗传编程进化 ═══
            if task_type in ("full", "quick", "factor_only"):
                self._report_progress("gp_evolution", 35, "启动遗传编程搜索...")
                
                gp_config = {
                    "population_size": self.config.gp_population_size if task_type == "full" else 20,
                    "max_generations": self.config.gp_max_generations if task_type == "full" else 5,
                }
                
                evolved_factors = self._run_gp_evolution(multi_data, seed_factors, gp_config)
                task.factors_tested = len(evolved_factors)
                self._report_progress("gp_evolution", 65, f"进化完成: 测试 {len(evolved_factors)} 个因子")
            else:
                evolved_factors = []
                task.factors_tested = 0
            
            # ═══ Phase 4: 因子评估 ═══
            self._report_progress("factor_evaluation", 70, "评估因子质量...")
            valid_factors = self._evaluate_factors(multi_data, evolved_factors)
            task.factors_valid = len(valid_factors)
            
            if valid_factors:
                best = max(valid_factors, key=lambda x: x.get("fitness", 0))
                task.best_fitness = best.get("fitness", 0)
                task.best_expression = best.get("expression", "")
            
            self._report_progress("factor_evaluation", 80, 
                                  f"评估完成: {task.factors_valid}/{task.factors_tested} 有效")
            
            # ═══ Phase 5: 组合策略构建 ═══
            if task_type in ("full", "ensemble_only") and valid_factors:
                self._report_progress("ensemble_building", 85, "构建组合策略...")
                ensemble_result = self._build_ensemble(multi_data, valid_factors)
                task.ensemble_score = ensemble_result.get("composite_score", 0)
                self._report_progress("ensemble_building", 90, 
                                      f"组合策略评分: {task.ensemble_score:.1f}")
            elif task_type == "quick" and valid_factors:
                # 快速模式也做简单组合
                self._report_progress("ensemble_building", 85, "构建快速组合策略...")
                ensemble_result = self._build_ensemble(multi_data, valid_factors[:3])
                task.ensemble_score = ensemble_result.get("composite_score", 0)
            else:
                ensemble_result = None
            
            # ═══ Phase 6: 验证 ═══
            self._report_progress("validation", 95, "验证结果...")
            self._validate_results(task, valid_factors, ensemble_result)
            
            # ═══ Phase 7: 更新最佳策略 ═══
            self._report_progress("update_best", 98, "更新最佳策略...")
            self._update_best_strategy(task, valid_factors, ensemble_result)
            
            task.status = "completed"
            self._report_progress("completed", 100, "进化完成!")
            
        except Exception as e:
            logger.error(f"进化异常: {e}\n{traceback.format_exc()}")
            task.status = "failed"
            task.error = str(e)
            self._report_progress("failed", task.progress_pct, f"进化失败: {e}")
        
        finally:
            task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task.duration_seconds = time.time() - start_time
            self.history.append(task)
            self._save_state()
            self._is_running = False
            self._current_task = None
        
        return task
    
    # ─── 各阶段实现 ───
    
    def _load_data(self) -> Optional[Any]:
        """
        加载多股票历史数据
        
        因子评估需要多股票截面数据来计算 IC（信息系数），
        单股票时间序列 IC 信号太弱，几乎无法发现有效因子。
        
        Returns:
            Dict[str, pd.DataFrame]: {stock_code: OHLCV DataFrame}
        """
        try:
            from core.quant_brain import DataProvider
            
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=self.config.lookback_days)).strftime("%Y-%m-%d")
            
            all_data = {}
            failed = []
            
            # 每次进化使用全部股票池
            for stock_code in self.config.stock_pool:
                try:
                    df = DataProvider.get_stock_daily(stock_code, start_date=start_date, end_date=end_date)
                    if df is not None and not df.empty and len(df) >= 60:
                        all_data[stock_code] = df
                    else:
                        failed.append(stock_code)
                except Exception as e:
                    logger.debug(f"加载 {stock_code} 失败: {e}")
                    failed.append(stock_code)
            
            if all_data:
                logger.info(f"多股票数据加载完成: {len(all_data)} 只成功, {len(failed)} 只失败")
                return all_data
            else:
                logger.error("所有股票数据加载失败")
                return None
            
        except Exception as e:
            logger.error(f"数据加载失败: {e}")
            return None
    
    def _generate_seed_factors(self) -> List[str]:
        """生成种子因子表达式
        
        因子来源（按优先级）:
        1. 情报采集器 — 从 WorldQuant Alpha101、学术论文、GitHub开源项目、
           社交媒体等渠道采集的策略因子
        2. 内置种子 — 已验证有效的基础因子模式
        
        因子分类：
        - 动量类：短期价格变化率
        - 均线类：短期/长期均线偏离
        - 波动率类：价格波动特征
        - 成交量类：量能变化
        - 技术指标类：RSI、Z-Score等
        - 超跌反弹类（ETF抄底策略核心特征）
        - 复合类：多因子交叉
        """
        all_seeds = []

        # ═══ Phase 0: 从情报采集器获取因子 ═══
        try:
            from core.alphaforge.intelligence_collector import IntelligenceCollector
            collector = IntelligenceCollector()
            collected = collector.get_collected_factors()

            if collected:
                intelligence_expressions = [
                    f.expression for f in collected if f.usable
                ]
                all_seeds.extend(intelligence_expressions)
                logger.info(f"从情报采集器注入 {len(intelligence_expressions)} 个因子")
        except Exception as e:
            logger.debug(f"情报采集器加载失败（使用内置种子）: {e}")

        # ═══ 内置种子因子（基础兜底） ═══
        builtin_seeds = [
            # ─── 动量类 ───
            "ts_delta(close, 5) / ts_std(close, 20)",
            "ts_mean(close, 5) / ts_mean(close, 20) - 1",
            "momentum(close, 10)",
            "roc(close, 5)",

            # ─── 均线类 ───
            "sma(close, 5) / sma(close, 20) - 1",
            "ema(close, 5) / ema(close, 20) - 1",
            "close / sma(close, 10) - 1",

            # ─── 波动率类 ───
            "ts_std(close, 5) / ts_std(close, 20)",
            "ts_std(close, 10) / ts_std(close, 30)",

            # ─── 成交量类 ───
            "ts_mean(volume, 5) / ts_mean(volume, 20)",
            "volume / ts_mean(volume, 10)",
            "ts_rank(volume, 10)",

            # ─── 技术指标类 ───
            "rsi(close, 14)",
            "ts_zscore(close, 20)",
            "ts_rank(close, 10)",

            # ─── 超跌反弹类 ───
            "-ts_zscore(close, 10)",
            "-ts_zscore(close, 5)",
            "-rsi(close, 5) / 100",
            "ts_sum(min(close / ts_delay(close, 1) - 1, 0), 5) / ts_sum(abs(close / ts_delay(close, 1) - 1), 5)",

            # ─── 复合类 ───
            "ts_corr(close, volume, 10)",
            "ts_delta(close, 5) * ts_rank(volume, 10)",
            "ts_mean(close, 5) / ts_std(close, 10)",
            "(close - ts_min(close, 10)) / (ts_max(close, 10) - ts_min(close, 10))",

            # ─── 均线增强类 ───
            "sma(close, 5) / sma(close, 60) - 1",
            "ema(close, 12) / ema(close, 26) - 1",

            # ─── 趋势强度类 ───
            "ts_regression(close, 20)",
            "ts_corr(close, volume, 20) * -1",

            # ─── 统计特征类 ───
            "ts_skewness(close / ts_delay(close, 1) - 1, 20)",
            "ts_skewness(close / ts_delay(close, 1) - 1, 20) * -1",
        ]
        all_seeds.extend(builtin_seeds)

        # 去重（保持顺序）
        seen = set()
        unique_seeds = []
        for s in all_seeds:
            if s not in seen:
                seen.add(s)
                unique_seeds.append(s)

        logger.info(f"种子因子: 情报{len(all_seeds) - len(builtin_seeds)} + 内置{len(builtin_seeds)} = 去重后{len(unique_seeds)}")
        return unique_seeds
    
    def _run_gp_evolution(self, multi_data: Dict[str, pd.DataFrame], 
                          seed_factors: List[str], 
                          gp_config: Dict) -> List[Dict]:
        """运行遗传编程进化（多股票截面评估）"""
        from core.alphaforge.genetic_programming import GeneticProgrammer
        from core.alphaforge.factor_analyzer import FactorAnalyzer
        from core.alphaforge.factor_engine import FactorEngine
        
        gp = GeneticProgrammer(config=gp_config)
        analyzer = FactorAnalyzer()
        engine = FactorEngine()
        
        # 使用第一只股票的数据作为 GP 引擎的主数据（用于因子计算）
        primary_code = list(multi_data.keys())[0]
        primary_data = multi_data[primary_code]
        
        def fitness_evaluator(expression: str, data: pd.DataFrame) -> Dict:
            """
            多股票截面适应度评估：
            1. 在主股票上计算因子值
            2. 在多只股票上计算截面 IC
            3. 综合评估适应度
            """
            try:
                # 在主股票上计算因子值
                factor_values = engine.compute(expression, data)
                if factor_values is None or factor_values.empty:
                    return {"fitness": 0, "ic_mean": 0, "ir": 0, "sharpe": 0}
                
                # 在主股票上计算单股票 IC（基础评估）
                forward_returns = data["close"].pct_change().shift(-1)
                aligned = pd.DataFrame({
                    "factor": factor_values.reindex(data.index),
                    "return": forward_returns,
                }).dropna()
                
                if len(aligned) < 30:
                    return {"fitness": 0, "ic_mean": 0, "ir": 0, "sharpe": 0}
                
                eval_result = analyzer.evaluate(aligned["factor"], aligned["return"], expression)
                
                # 如果因子有效，进一步做多股票截面评估
                if eval_result.fitness > 0.01 and len(multi_data) > 1:
                    cross_ic_values = []
                    for code, stock_data in multi_data.items():
                        if len(stock_data) < 60:
                            continue
                        try:
                            fv = engine.compute(expression, stock_data)
                            if fv is not None and not fv.empty:
                                fwd = stock_data["close"].pct_change().shift(-1)
                                cross_aligned = pd.DataFrame({
                                    "factor": fv.reindex(stock_data.index),
                                    "return": fwd,
                                }).dropna()
                                if len(cross_aligned) >= 20:
                                    ic, _ = scipy_stats.spearmanr(
                                        cross_aligned["factor"], cross_aligned["return"]
                                    )
                                    if not np.isnan(ic):
                                        cross_ic_values.append(abs(ic))
                        except Exception:
                            continue
                    
                    if cross_ic_values:
                        cross_ic_mean = np.mean(cross_ic_values)
                        cross_ic_std = np.std(cross_ic_values) if len(cross_ic_values) > 1 else 0.01
                        cross_ir = cross_ic_mean / (cross_ic_std + 1e-8)
                        
                        # 多股票稳定性加分
                        stability_bonus = min(0.2, cross_ir * 0.1)
                        eval_result.fitness = min(1.0, eval_result.fitness + stability_bonus)
                        eval_result.ic_ir = cross_ir
                
                return {
                    "fitness": eval_result.fitness,
                    "ic_mean": eval_result.ic_mean,
                    "ir": eval_result.ic_ir,
                    "sharpe": eval_result.sharpe_ratio,
                }
            except Exception as e:
                return {"fitness": 0, "ic_mean": 0, "ir": 0, "sharpe": 0}
        
        # 执行进化
        top_individuals = gp.evolve(
            data=primary_data,
            warm_start_exprs=seed_factors,
            fitness_evaluator=fitness_evaluator,
        )
        
        # 返回结果
        results = []
        for ind in top_individuals:
            if ind.fitness > 0:
                results.append({
                    "expression": ind.expression,
                    "fitness": ind.fitness,
                    "ic_mean": ind.ic_mean,
                    "ir": ind.ir,
                    "sharpe": ind.sharpe,
                    "generation": ind.generation,
                })
        
        return sorted(results, key=lambda x: -x["fitness"])
    
    def _evaluate_factors(self, multi_data: Dict[str, pd.DataFrame], 
                          factor_results: List[Dict]) -> List[Dict]:
        """评估因子（多股票交叉验证）"""
        valid = []
        for fr in factor_results:
            if fr.get("fitness", 0) >= self.config.min_factor_fitness:
                valid.append(fr)
        return valid
    
    def _build_ensemble(self, multi_data: Dict[str, pd.DataFrame], 
                        valid_factors: List[Dict]) -> Dict:
        """构建组合策略（使用第一只股票做回测）"""
        from core.alphaforge.factor_engine import FactorEngine
        from core.alphaforge.strategy_ensemble import StrategyEnsemble
        
        engine = FactorEngine()
        ensemble = StrategyEnsemble(config={
            "method": self.config.ensemble_method,
        })
        
        # 使用第一只股票的数据做组合回测
        primary_code = list(multi_data.keys())[0]
        data = multi_data[primary_code]
        
        # 计算所有有效因子的值
        factor_values = {}
        factor_meta = {}
        top_factors = valid_factors[:self.config.ensemble_top_n]
        
        for fr in top_factors:
            expr = fr["expression"]
            values = engine.compute(expr, data)
            if values is not None and not values.empty:
                name = f"factor_{hash(expr) % 10000:04d}"
                factor_values[name] = values
                factor_meta[name] = fr
        
        if not factor_values:
            return {"composite_score": 0, "error": "无有效因子值"}
        
        # 构建组合
        result = ensemble.build_ensemble(factor_values, factor_meta, data)
        return result.to_dict()
    
    def _validate_results(self, task: EvolutionTask, 
                          valid_factors: List[Dict],
                          ensemble_result: Optional[Dict]):
        """验证结果"""
        checks = []
        
        if task.factors_valid > 0:
            checks.append(("有效因子数", True))
        else:
            checks.append(("有效因子数", False))
        
        if ensemble_result and ensemble_result.get("composite_score", 0) > 20:
            checks.append(("组合评分", True))
        
        task.message = f"验证: {sum(1 for _, ok in checks if ok)}/{len(checks)} 通过"

    
    def _update_best_strategy(self, task: EvolutionTask,
                               valid_factors: List[Dict],
                               ensemble_result: Optional[Dict]):
        """更新最佳策略"""
        if not valid_factors and not ensemble_result:
            return
        
        current_best_score = self.state.get("best_score", 0)
        new_score = task.ensemble_score if task.ensemble_score > 0 else task.best_fitness * 100
        
        if new_score > current_best_score:
            self.state["best_score"] = new_score
            self.state["best_task_id"] = task.task_id
            self.state["best_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if ensemble_result:
                self.state["best_ensemble"] = {
                    "weights": ensemble_result.get("weights", {}),
                    "score": ensemble_result.get("composite_score", 0),
                    "sharpe": ensemble_result.get("sharpe_ratio", 0),
                    "total_return": ensemble_result.get("total_return", 0),
                }
            
            self.state["best_factors"] = valid_factors[:self.config.ensemble_top_n]
            
            # 保存最佳策略
            try:
                BEST_STRATEGY_FILE.write_text(
                    json.dumps({
                        "updated_at": self.state["best_updated_at"],
                        "score": new_score,
                        "ensemble": self.state.get("best_ensemble", {}),
                        "factors": self.state.get("best_factors", []),
                        "task_id": task.task_id,
                    }, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception:
                pass
            
            logger.info(f"更新最佳策略! 评分: {new_score:.1f}")
    
    # ─── 查询接口 ───
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "is_running": self._is_running,
            "current_task": self._current_task.to_dict() if self._current_task else None,
            "total_evolutions": len(self.history),
            "best_score": self.state.get("best_score", 0),
            "last_evolution": self.history[-1].to_dict() if self.history else None,
            "config": self.config.to_dict(),
        }
    
    def get_best_strategy(self) -> Optional[Dict]:
        """获取当前最佳策略"""
        if BEST_STRATEGY_FILE.exists():
            try:
                return json.loads(BEST_STRATEGY_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None
    
    def get_evolution_history(self, limit: int = 10) -> List[Dict]:
        """获取进化历史"""
        return [t.to_dict() for t in self.history[-limit:]]
    
    def get_factor_ranking(self, limit: int = 20) -> List[Dict]:
        """获取因子排名"""
        all_factors = []
        for task in self.history:
            if task.best_expression:
                all_factors.append({
                    "expression": task.best_expression,
                    "fitness": task.best_fitness,
                    "task_id": task.task_id,
                    "created_at": task.started_at,
                })
        
        # 去重
        seen = set()
        unique = []
        for f in sorted(all_factors, key=lambda x: -x["fitness"]):
            if f["expression"] not in seen:
                seen.add(f["expression"])
                unique.append(f)
        
        return unique[:limit]


# ═══════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════

_scheduler_instance = None

def get_evolution_scheduler() -> EvolutionScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = EvolutionScheduler()
    return _scheduler_instance
