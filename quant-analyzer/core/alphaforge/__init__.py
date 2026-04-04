"""
🧬 AlphaForge — 自动进化量化因子挖掘系统

基于 AlphaAgent + FactorMiner + WorldQuant Alpha Factory 设计，
结合遗传编程、LLM辅助和因子评估的专业量化因子挖掘框架。

核心架构：
  IdeaAgent    → 因子创意生成（市场假设 + 金融理论）
  FactorAgent  → 因子公式构造（遗传编程 + LLM辅助）
  EvalAgent    → 因子评估验证（IC/IR/夏普/回撤）
  EnsembleBot  → 因子组合优化（加权融合 + 风险控制）
  Scheduler    → 自动进化调度（每日/每周自动进化）

使用方法：
  from core.alphaforge import AlphaForge
  forge = AlphaForge()
  forge.run_evolution_cycle()  # 执行一轮完整进化
"""

from core.alphaforge.factor_engine import FactorEngine
from core.alphaforge.genetic_programming import GeneticProgrammer
from core.alphaforge.factor_analyzer import FactorAnalyzer
from core.alphaforge.strategy_ensemble import StrategyEnsemble
from core.alphaforge.auto_scheduler import EvolutionScheduler

__version__ = "1.0.0"
__all__ = [
    "FactorEngine",
    "GeneticProgrammer",
    "FactorAnalyzer",
    "StrategyEnsemble",
    "EvolutionScheduler",
]
