"""
自动优化模块 (AutoOptimizer)
负责策略参数的自动优化、模型更新和策略进化
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import pickle
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimizationMethod(Enum):
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    GENETIC_ALGORITHM = "genetic_algorithm"


class ModelType(Enum):
    LINEAR_REGRESSION = "linear_regression"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"


@dataclass
class OptimizationResult:
    best_params: Dict[str, Any]
    best_score: float
    optimization_time: float
    method: OptimizationMethod
    timestamp: datetime


@dataclass
class ModelUpdate:
    model_id: str
    model_type: ModelType
    validation_score: float
    update_reason: str
    timestamp: datetime


@dataclass
class StrategyEvolution:
    strategy_id: str
    parent_strategy_id: Optional[str]
    evolution_type: str
    performance_improvement: float
    timestamp: datetime


class AutoOptimizer:
    """自动优化器类"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 配置
        self.optimization_config = config.get("optimization", {
            "default_method": OptimizationMethod.GRID_SEARCH,
            "max_iterations": 100,
            "scoring_metric": "sharpe_ratio"
        })
        
        self.model_update_config = config.get("model_update", {
            "performance_threshold": 0.05,
            "max_models_to_keep": 10
        })
        
        self.strategy_evolution_config = config.get("strategy_evolution", {
            "mutation_rate": 0.1,
            "population_size": 20
        })
        
        # 历史记录
        self.optimization_history: List[OptimizationResult] = []
        self.model_update_history: List[ModelUpdate] = []
        self.strategy_evolution_history: List[StrategyEvolution] = []
        
        logger.info("AutoOptimizer初始化完成")
    
    def optimize_parameters(self, 
                          param_space: Dict[str, List[Any]], 
                          objective_function: Callable[[Dict[str, Any]], float],
                          method: Optional[OptimizationMethod] = None) -> OptimizationResult:
        """优化参数"""
        if method is None:
            method = self.optimization_config["default_method"]
        
        logger.info(f"开始参数优化，方法: {method.value}")
        start_time = datetime.now()
        
        if method == OptimizationMethod.GRID_SEARCH:
            result = self._grid_search(param_space, objective_function)
        elif method == OptimizationMethod.RANDOM_SEARCH:
            result = self._random_search(param_space, objective_function)
        elif method == OptimizationMethod.BAYESIAN_OPTIMIZATION:
            result = self._bayesian_optimization(param_space, objective_function)
        elif method == OptimizationMethod.GENETIC_ALGORITHM:
            result = self._genetic_algorithm(param_space, objective_function)
        else:
            raise ValueError(f"不支持的优化方法: {method}")
        
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        optimization_result = OptimizationResult(
            best_params=result["best_params"],
            best_score=result["best_score"],
            optimization_time=optimization_time,
            method=method,
            timestamp=datetime.now()
        )
        
        self.optimization_history.append(optimization_result)
        logger.info(f"参数优化完成，最佳分数: {result['best_score']:.4f}")
        
        return optimization_result
    
    def _grid_search(self, param_space: Dict[str, List[Any]], 
                    objective_function: Callable[[Dict[str, Any]], float]) -> Dict:
        """网格搜索优化"""
        from itertools import product
        
        param_names = list(param_space.keys())
        param_values = list(param_space.values())
        
        best_score = -np.inf
        best_params = {}
        
        param_combinations = list(product(*param_values))
        logger.info(f"网格搜索: {len(param_combinations)}个参数组合")
        
        for i, combination in enumerate(param_combinations):
            params = dict(zip(param_names, combination))
            
            try:
                score = objective_function(params)
                
                if score > best_score:
                    best_score = score
                    best_params = params.copy()
                    
                if (i + 1) % 10 == 0:
                    logger.debug(f"进度: {i+1}/{len(param_combinations)}")
                    
            except Exception as e:
                logger.warning(f"参数组合评估失败: {e}")
                continue
        
        return {"best_params": best_params, "best_score": best_score}
    
    def _random_search(self, param_space: Dict[str, List[Any]], 
                      objective_function: Callable[[Dict[str, Any]], float]) -> Dict:
        """随机搜索优化"""
        import random
        
        max_iterations = self.optimization_config["max_iterations"]
        
        best_score = -np.inf
        best_params = {}
        
        logger.info(f"随机搜索: {max_iterations}次迭代")
        
        for i in range(max_iterations):
            params = {}
            for param_name, values in param_space.items():
                params[param_name] = random.choice(values)
            
            try:
                score = objective_function(params)
                
                if score > best_score:
                    best_score = score
                    best_params = params.copy()
                    
                if (i + 1) % 10 == 0:
                    logger.debug(f"进度: {i+1}/{max_iterations}")
                    
            except Exception as e:
                logger.warning(f"参数组合评估失败: {e}")
                continue
        
        return {"best_params": best_params, "best_score": best_score}
    
    def _bayesian_optimization(self, param_space: Dict[str, List[Any]], 
                             objective_function: Callable[[Dict[str, Any]], float]) -> Dict:
        """贝叶斯优化"""
        try:
            from skopt import gp_minimize
            from skopt.space import Categorical
            from skopt.utils import use_named_args
            
            dimensions = []
            param_names = []
            
            for param_name, values in param_space.items():
                dimensions.append(Categorical(values, name=param_name))
                param_names.append(param_name)
            
            @use_named_args(dimensions=dimensions)
            def objective(**params):
                try:
                    score = objective_function(params)
                    return -score
                except Exception as e:
                    logger.warning(f"贝叶斯优化评估失败: {e}")
                    return 1e6
            
            result = gp_minimize(
                func=objective,
                dimensions=dimensions,
                n_calls=self.optimization_config["max_iterations"],
                random_state=42,
                verbose=False
            )
            
            best_params = dict(zip(param_names, result.x))
            best_score = -result.fun
            
            return {"best_params": best_params, "best_score": best_score}
            
        except ImportError:
            logger.warning("skopt未安装，回退到随机搜索")
            return self._random_search(param_space, objective_function)
    
    def _genetic_algorithm(self, param_space: Dict[str, List[Any]], 
                          objective_function: Callable[[Dict[str, Any]], float]) -> Dict:
        """遗传算法优化"""
        try:
            import random
            
            population_size = self.strategy_evolution_config["population_size"]
            max_iterations = self.optimization_config["max_iterations"]
            mutation_rate = self.strategy_evolution_config["mutation_rate"]
            
            param_names = list(param_space.keys())
            
            # 初始化种群
            population = []
            for _ in range(population_size):
                individual = {}
                for param_name, values in param_space.items():
                    individual[param_name] = random.choice(values)
                population.append(individual)
            
            best_score = -np.inf
            best_params = {}
            
            logger.info(f"遗传算法: 种群大小={population_size}")
            
            for iteration in range(max_iterations):
                # 评估种群
                scores = []
                for individual in population:
                    try:
                        score = objective_function(individual)
                        scores.append(score)
                    except Exception as e:
                        logger.warning(f"个体评估失败: {e}")
                        scores.append(-np.inf)
                
                # 更新最佳结果
                max_score = max(scores)
                if max_score > best_score:
                    best_score = max_score
                    best_params = population[scores.index(max_score)].copy()
                
                if (iteration + 1) % 10 == 0:
                    logger.debug(f"迭代 {iteration+1}/{max_iterations}: 最佳分数={best_score:.4f}")
                
                # 选择（简单选择）
                selected_indices = np.argsort(scores)[-population_size//2:]
                selected_population = [population[i] for i in selected_indices]
                
                # 交叉和突变
                new_population = []
                while len(new_population) < population_size:
                    parent1 = random.choice(selected_population)
                    parent2 = random.choice(selected_population)
                    
                    child = parent1.copy()
                    
                    # 交叉
                    if random.random() < 0.7:
                        for param_name in param_names:
                            if random.random() < 0.5:
                                child[param_name] = parent2[param_name]
                    
                    # 突变
                    if random.random() < mutation_rate:
                        param_to_mutate = random.choice(param_names)
                        values = param_space[param_to_mutate]
                        child[param_to_mutate] = random.choice(values)
                    
                    new_population.append(child)
                
                population = new_population[:population_size]
            
            return {"best_params": best_params, "best_score": best_score}
            
        except Exception as e:
            logger.warning(f"遗传算法失败: {e}")
            return self._random_search(param_space, objective_function)
    
    def update_model(self, 
                    model_id: str,
                    model_type: ModelType,
                    validation_score: float,
                    update_reason: str = "定期更新") -> ModelUpdate:
        """更新模型记录"""
        model_update = ModelUpdate(
            model_id=model_id,
            model_type=model_type,
            validation_score=validation_score,
            update_reason=update_reason,
            timestamp=datetime.now()
        )
        
        self.model_update_history.append(model_update)
        logger.info(f"模型 {model_id} 更新记录已保存，分数: {validation_score:.4f}")
        
        return model_update
    
    def evolve_strategy(self, 
                       strategy_id: str,
                       parent_strategy_id: Optional[str] = None,
                       performance_improvement: float = 0.0) -> StrategyEvolution:
        """进化策略记录"""
        evolution_type = "mutation" if performance_improvement > 0 else "selection"
        
        strategy_evolution = StrategyEvolution(
            strategy_id=f"{strategy_id}_evolved_{datetime.now().strftime('%Y%m%d')}",
            parent_strategy_id=parent_strategy_id,
            evolution_type=evolution_type,
            performance_improvement=performance_improvement,
            timestamp=datetime.now()
        )
        
        self.strategy_evolution_history.append(strategy_evolution)
        logger.info(f"策略 {strategy_id} 进化记录已保存，提升: {performance_improvement:.4f}")
        
        return strategy_evolution
    
    def get_summary(self) -> Dict[str, Any]:
        """获取优化摘要"""
        summary = {
            "optimization": {
                "total": len(self.optimization_history),
                "best_score": max([h.best_score for h in self.optimization_history]) if self.optimization_history else 0,
                "latest_method": self.optimization_history[-1].method.value if self.optimization_history else "none"
            },
            "model_updates": {
                "total": len(self.model_update_history),
                "best_score": max([m.validation_score for m in self.model_update_history]) if self.model_update_history else 0,
                "latest_reason": self.model_update_history[-1].update_reason if self.model_update_history else "none"
            },
            "strategy_evolutions": {
                "total": len(self.strategy_evolution_history),
                "with_improvement": len([s for s in self.strategy_evolution_history if s.performance_improvement > 0]),
                "latest_type": self.strategy_evolution_history[-1].evolution_type if self.strategy_evolution_history else "none"
            }
        }
        
        return summary
    
    def save_state(self, filepath: str):
        """保存状态到文件"""
        state = {
            "optimization_history": [
                {
                    "best_params": h.best_params,
                    "best_score": h.best_score,
                    "optimization_time": h.optimization_time,
                    "method": h.method.value,
                    "timestamp": h.timestamp.isoformat()
                }
                for h in self.optimization_history
            ],
            "model_update_history": [
                {
                    "model_id": m.model_id,
                    "model_type": m.model_type.value,
                    "validation_score": m.validation_score,
                    "update_reason": m.update_reason,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in self.model_update_history
            ],
            "strategy_evolution_history": [
                {
                    "strategy_id": s.strategy_id,
                    "parent_strategy_id": s.parent_strategy_id,
                    "evolution_type": s.evolution_type,
                    "performance_improvement": s.performance_improvement,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in self.strategy_evolution_history
            ],
            "config": self.config
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
        
        logger.info(f"状态已保存到 {filepath}")
    
    def load_state(self, filepath: str):
        """从文件加载状态"""
        try:
            with open(filepath, 'rb') as f:
                state = pickle.load(f)
            
            # 恢复优化历史
            self.optimization_history = []
            for h in state.get("optimization_history", []):
                self.optimization_history.append(OptimizationResult(
                    best_params=h["best_params"],
                    best_score=h["best_score"],
                    optimization_time=h["optimization_time"],
                    method=OptimizationMethod(h["method"]),
                    timestamp=datetime.fromisoformat(h["timestamp"])
                ))
            
            # 恢复模型更新历史
            self.model_update_history = []
            for m in state.get("model_update_history", []):
                self.model_update_history.append(ModelUpdate(
                    model_id=m["model_id"],
                    model_type=ModelType(m["model_type"]),
                    validation_score=m["validation_score"],
                    update_reason=m["update_reason"],
                    timestamp=datetime.fromisoformat(m["timestamp"])
                ))
            
            # 恢复策略进化历史
            self.strategy_evolution_history = []
            for s in state.get("strategy_evolution_history", []):
                self.strategy_evolution_history.append(StrategyEvolution(
                    strategy_id=s["strategy_id"],
                    parent_strategy_id=s["parent_strategy_id"],
                    evolution_type=s["evolution_type"],
                    performance_improvement=s["performance_improvement"],
                    timestamp=datetime.fromisoformat(s["timestamp"])
                ))
            
            logger.info(f"状态已从 {filepath} 加载")
            
        except Exception as e:
            logger.error(f"加载状态失败: {e}")


def test_auto_optimizer():
    """测试自动优化器"""
    print("测试自动优化器...")
    
    # 创建配置
    config = {
        "optimization": {
            "default_method": OptimizationMethod.RANDOM_SEARCH,
            "max_iterations": 50
        },
        "model_update": {
            "performance_threshold": 0.05
        }
    }
    
    # 创建优化器
    optimizer = AutoOptimizer(config)
    
    # 测试参数优化
    def objective_function(params):
        # 简单的目标函数：最大化 -(x-0.5)^2 - (y-0.5)^2
        x = params.get("x", 0)
        y = params.get("y", 0)
        return -(x-0.5)**2 - (y-0.5)**2
    
    param_space = {
        "x": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
        "y": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    }
    
    # 运行优化
    result = optimizer.optimize_parameters(param_space, objective_function)
    print(f"优化结果: 最佳参数={result.best_params}, 最佳分数={result.best_score:.4f}")
    
    # 测试模型更新
    model_update = optimizer.update_model(
        model_id="test_model_001",
        model_type=ModelType.RANDOM_FOREST,
        validation_score=0.85,
        update_reason="测试更新"
    )
    print(f"模型更新: {model_update.model_id}, 分数={model_update.validation_score:.4f}")
    
    # 测试策略进化
    strategy_evolution = optimizer.evolve_strategy(
        strategy_id="test_strategy_001",
        parent_strategy_id="parent_001",
        performance_improvement=0.12
    )
    print(f"策略进化: {strategy_evolution.strategy_id}, 提升={strategy_evolution.performance_improvement:.4f}")
    
    # 获取摘要
    summary = optimizer.get_summary()
    print(f"优化摘要: {summary}")
    
    # 保存状态
    optimizer.save_state("test_optimizer_state.pkl")
    
    print("自动优化器测试完成！")


if __name__ == "__main__":
    test_auto_optimizer()