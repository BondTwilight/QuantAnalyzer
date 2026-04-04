"""
🧬 GeneticProgrammer — 字符串表达式遗传编程因子发现

基于 Warm Start GP + 算子感知字符串变异。

核心设计：
- 个体直接存储表达式字符串，不需要解析为表达式树
- 遗传操作（变异/交叉）在字符串层面进行
- 算子感知：变异操作理解算子结构（name/args/arity），确保生成合法表达式
- Warm Start 直接接受字符串表达式，无需解析

参考论文：
- Alpha Mining and Enhancing via Warm Start GP (2024)
- AutoAlpha: Hierarchical EA for Alpha Factors (AAAI 2022)
"""

import random
import re
import copy
import hashlib
import logging
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 算子注册表
# ═══════════════════════════════════════════════

# (name, arity) — arity=1: 一元无参, arity=2: 二元(带参数或双数据), arity=3: 三元
REGISTERED_OPERATORS: List[Tuple[str, int]] = [
    # 时序算子: op(data, param)
    ("ts_mean", 2), ("ts_std", 2), ("ts_sum", 2), ("ts_max", 2), ("ts_min", 2),
    ("ts_rank", 2), ("ts_delta", 2), ("ts_delay", 2), ("ts_zscore", 2),
    ("ts_decay_linear", 2), ("ts_regression", 2), ("ts_skewness", 2),
    ("ts_kurtosis", 2), ("ts_arg_max", 2), ("ts_arg_min", 2), ("ts_product", 2),
    # 技术指标: op(data, param)
    ("sma", 2), ("ema", 2), ("rsi", 2), ("roc", 2), ("momentum", 2),
    # 截面算子: op(data)
    ("rank", 1), ("zscore", 1), ("normalize", 1), ("sign", 1), ("log", 1), ("abs", 1),
    # 双数据算子: op(data1, data2)
    ("max", 2), ("min", 2),
    # 三元算子: op(data1, data2, param)
    ("ts_corr", 3), ("ts_cov", 3),
]

# 带参数的算子及参数范围 (第二个参数是数字)
PARAMETRIC_OPS: Dict[str, Tuple[int, int]] = {
    "ts_mean": (2, 120), "ts_std": (2, 120), "ts_sum": (2, 120),
    "ts_max": (2, 120), "ts_min": (2, 120), "ts_rank": (3, 60),
    "ts_delta": (1, 20), "ts_delay": (1, 20),
    "ts_zscore": (5, 120), "ts_decay_linear": (2, 30),
    "ts_regression": (5, 60), "ts_arg_max": (3, 30), "ts_arg_min": (3, 30),
    "ts_skewness": (5, 60), "ts_kurtosis": (5, 60),
    "ts_product": (2, 20),
    "sma": (2, 120), "ema": (2, 120), "rsi": (5, 30),
    "roc": (2, 30), "momentum": (2, 30),
    "ts_corr": (5, 60), "ts_cov": (5, 60),
}

# 双数据输入算子 (arity=2 但第二个参数是数据表达式，不是数字)
DUAL_DATA_OPS: Set[str] = {"max", "min"}

# 数据终端
DATA_TERMINALS: List[str] = ["close", "high", "low", "open", "volume", "v"]

# 算子选择权重
OPERATOR_WEIGHTS: Dict[str, int] = {
    "ts_mean": 4, "ts_std": 3, "ts_rank": 4, "ts_delta": 4,
    "sma": 4, "ema": 4, "rsi": 5, "roc": 3, "momentum": 3,
    "ts_zscore": 4, "rank": 3, "normalize": 2, "sign": 2,
    "ts_corr": 3, "ts_skewness": 2,
    "ts_sum": 2, "ts_max": 2, "ts_min": 2, "ts_delay": 2,
    "ts_decay_linear": 2, "ts_regression": 2, "zscore": 2,
    "log": 1, "abs": 1, "ts_cov": 2,
    "ts_arg_max": 1, "ts_arg_min": 1, "ts_product": 1, "ts_kurtosis": 1,
    "max": 1, "min": 1,
}

# 算子分组（用于同类替换）
OPERATOR_GROUPS: Dict[str, List[str]] = {
    "arity_1": [name for name, arity in REGISTERED_OPERATORS if arity == 1],
    "arity_2_param": [name for name, arity in REGISTERED_OPERATORS if arity == 2 and name not in DUAL_DATA_OPS],
    "arity_2_data": list(DUAL_DATA_OPS),
    "arity_3": [name for name, arity in REGISTERED_OPERATORS if arity == 3],
}

# 算术组合运算符（交叉操作用）
COMBINE_OPS = ["+", "-", "*", "/"]


# ═══════════════════════════════════════════════
# 字符串表达式解析工具
# ═══════════════════════════════════════════════

def _parse_top_level_call(expr: str) -> Optional[Tuple[str, str]]:
    """
    解析表达式的最外层函数调用。

    Returns:
        (func_name, inner_content) 或 None

    Examples:
        "ts_mean(close, 10)" -> ("ts_mean", "close, 10")
        "rank(ts_mean(close, 5))" -> ("rank", "ts_mean(close, 5)")
        "close" -> None
        "ts_mean(close, 5) / ts_std(close, 5)" -> None
    """
    expr = expr.strip()
    match = re.match(r'^([a-zA-Z_]\w*)\((.+)\)$', expr, re.DOTALL)
    if not match:
        return None
    func_name = match.group(1)
    inner = match.group(2)
    # 验证括号匹配
    depth = 0
    for ch in inner:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth < 0:
                return None
    if depth != 0:
        return None
    return (func_name, inner)


def _split_args(arg_string: str) -> List[str]:
    """
    按逗号分割参数，正确处理嵌套括号。
    """
    args = []
    current = []
    depth = 0
    for ch in arg_string:
        if ch == ',' and depth == 0:
            args.append(''.join(current).strip())
            current = []
        else:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            current.append(ch)
    if current:
        args.append(''.join(current).strip())
    return args


def _extract_parametric_ops(expr: str) -> List[Tuple[str, int, int, int]]:
    """
    从表达式中提取所有带参数的算子调用。

    Returns:
        [(op_name, param_start_pos, param_end_pos, param_value), ...]
    """
    results = []
    op_pattern = '|'.join(re.escape(op) for op in PARAMETRIC_OPS)
    pattern = re.compile(
        r'(' + op_pattern + r')'
        r'\(([^)]*(?:\([^)]*\))*[^)]*),\s*(\d+)\)',
        re.DOTALL
    )
    for m in pattern.finditer(expr):
        op_name = m.group(1)
        param_value = int(m.group(3))
        param_start = m.start(3)
        param_end = m.end(3)
        results.append((op_name, param_start, param_end, param_value))
    return results


def _extract_data_terminals(expr: str) -> List[Tuple[str, int, int]]:
    """
    从表达式中提取数据终端。

    Returns:
        [(terminal_name, start_pos, end_pos), ...]
    """
    results = []
    for term in DATA_TERMINALS:
        for m in re.finditer(rf'\b{re.escape(term)}\b', expr):
            results.append((term, m.start(), m.end()))
    return results


def _extract_operator_tokens(expr: str) -> List[str]:
    """提取表达式中的算子名称列表（按出现顺序）"""
    all_op_names = {op[0] for op in REGISTERED_OPERATORS}
    tokens = []
    for m in re.finditer(r'\b([a-zA-Z_]\w*)\s*\(', expr):
        if m.group(1) in all_op_names:
            tokens.append(m.group(1))
    return tokens


def _get_op_info(op_name: str) -> Optional[Tuple[str, int]]:
    """获取算子 (name, arity)"""
    for name, arity in REGISTERED_OPERATORS:
        if name == op_name:
            return (name, arity)
    return None


def _get_ops_by_arity(arity: int) -> List[Tuple[str, int]]:
    """获取指定 arity 的所有算子"""
    return [(name, ar) for name, ar in REGISTERED_OPERATORS if ar == arity]


def _get_same_arity_ops(op_name: str) -> List[str]:
    """获取与给定算子同 arity 的其他算子"""
    info = _get_op_info(op_name)
    if not info:
        return []
    _, arity = info
    return [name for name, ar in REGISTERED_OPERATORS if ar == arity and name != op_name]


def _is_parametric(op_name: str) -> bool:
    return op_name in PARAMETRIC_OPS


def _is_dual_data(op_name: str) -> bool:
    return op_name in DUAL_DATA_OPS


def _expression_depth(expr: str) -> int:
    """估算表达式嵌套深度"""
    depth = 0
    max_depth = 0
    for ch in expr:
        if ch == '(':
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == ')':
            depth -= 1
    return max_depth


def _expression_hash(expr: str) -> str:
    """生成表达式哈希"""
    return hashlib.md5(expr.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════
# 个体（候选因子）
# ═══════════════════════════════════════════════

@dataclass
class GPIndividual:
    """遗传编程个体（一个因子候选）"""
    expression: str = ""
    fitness: float = 0.0
    ic_mean: float = 0.0
    ir: float = 0.0
    sharpe: float = 0.0
    generation: int = 0
    is_elite: bool = False
    diversity_score: float = 0.0
    evaluation_time: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "expression": self.expression,
            "fitness": self.fitness,
            "ic_mean": self.ic_mean,
            "ir": self.ir,
            "sharpe": self.sharpe,
            "generation": self.generation,
            "is_elite": self.is_elite,
        }

    def clone(self) -> "GPIndividual":
        """深拷贝个体"""
        return GPIndividual(
            expression=self.expression,
            fitness=self.fitness,
            ic_mean=self.ic_mean,
            ir=self.ir,
            sharpe=self.sharpe,
            generation=self.generation,
            is_elite=self.is_elite,
            diversity_score=self.diversity_score,
            evaluation_time=self.evaluation_time,
        )

    # 兼容别名
    copy = clone


# ═══════════════════════════════════════════════
# 遗传编程引擎
# ═══════════════════════════════════════════════

class GeneticProgrammer:
    """
    遗传编程因子发现引擎（字符串表达式版）

    使用遗传编程自动搜索有效的量化因子表达式。
    个体直接存储表达式字符串，遗传操作在字符串层面进行。

    特性：
    - 算子感知变异：理解算子结构，确保生成合法表达式
    - Warm Start：直接接受字符串表达式
    - 多样性控制：基于表达式哈希去重
    - 并行评估：ThreadPoolExecutor
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = {
            # 种群参数
            "population_size": 100,
            "max_generations": 50,
            "elite_size": 10,
            "tournament_size": 3,

            # 表达式结构参数
            "max_depth": 4,
            "min_depth": 2,
            "max_expression_length": 200,

            # 遗传操作概率
            "crossover_rate": 0.6,
            "mutation_rate": 0.3,
            "reproduction_rate": 0.1,

            # 多样性控制
            "novelty_ratio": 0.3,
            "max_similar": 5,

            # 停止条件
            "stagnation_limit": 10,
            "target_fitness": 0.8,

            # 并行
            "parallel_workers": 4,
        }
        if config:
            self.config.update(config)

        self.population: List[GPIndividual] = []
        self.elite_archive: List[GPIndividual] = []
        self.generation = 0
        self.best_individual: Optional[GPIndividual] = None
        self.history: List[Dict] = []
        self._expression_hashes: Set[str] = set()

    def set_fitness_evaluator(self, evaluator):
        """设置适应度评估函数"""
        self._fitness_evaluator = evaluator

    # ─── 随机表达式生成 ───

    def _generate_random_expression(self, max_depth: int = 3) -> str:
        """
        生成随机因子表达式字符串

        Args:
            max_depth: 最大嵌套深度
        """
        if max_depth is None:
            max_depth = self.config["max_depth"]

        if max_depth <= 0:
            return random.choice(DATA_TERMINALS)

        # 15% 概率在非叶节点也直接返回终端
        if max_depth == 1 or random.random() < 0.15:
            return random.choice(DATA_TERMINALS)

        # 按权重选择算子
        op_name, arity = self._pick_random_operator()

        if arity == 1:
            # 一元截面算子: op(data)
            inner = self._generate_random_expression(max_depth - 1)
            return f"{op_name}({inner})"

        elif arity == 2:
            if _is_dual_data(op_name):
                # 双数据算子: max(data1, data2)
                inner1 = self._generate_random_expression(max_depth - 1)
                inner2 = self._generate_random_expression(max_depth - 1)
                return f"{op_name}({inner1}, {inner2})"
            else:
                # 带参数: ts_mean(data, param)
                inner = self._generate_random_expression(max_depth - 1)
                lo, hi = PARAMETRIC_OPS.get(op_name, (2, 60))
                param = random.randint(lo, hi)
                return f"{op_name}({inner}, {param})"

        elif arity == 3:
            # 三元算子: ts_corr(data1, data2, param)
            inner1 = self._generate_random_expression(max_depth - 1)
            inner2 = self._generate_random_expression(max_depth - 1)
            lo, hi = PARAMETRIC_OPS.get(op_name, (5, 60))
            param = random.randint(lo, hi)
            return f"{op_name}({inner1}, {inner2}, {param})"

        return random.choice(DATA_TERMINALS)

    def _pick_random_operator(self) -> Tuple[str, int]:
        """按权重随机选择算子"""
        op_names = [name for name, _ in REGISTERED_OPERATORS]
        weights = [OPERATOR_WEIGHTS.get(name, 1) for name in op_names]
        chosen = random.choices(op_names, weights=weights, k=1)[0]
        info = _get_op_info(chosen)
        if info:
            return info
        return ("ts_mean", 2)

    # ─── 初始化种群 ───

    def initialize_population(self, warm_start_exprs: List[str] = None) -> List[GPIndividual]:
        """
        初始化种群

        Args:
            warm_start_exprs: 已知有效因子表达式列表（Warm Start）
        """
        self.population = []
        self._expression_hashes = set()
        pop_size = self.config["population_size"]

        # 1. Warm Start: 直接将字符串加入种群
        ws_count = 0
        if warm_start_exprs:
            for expr in warm_start_exprs[:pop_size // 4]:
                expr = expr.strip()
                if not expr:
                    continue
                if len(expr) > self.config["max_expression_length"]:
                    continue
                h = _expression_hash(expr)
                if h not in self._expression_hashes:
                    individual = GPIndividual(expression=expr, generation=0)
                    self.population.append(individual)
                    self._expression_hashes.add(h)
                    ws_count += 1

        # 2. 随机生成剩余个体
        attempts = 0
        max_attempts = pop_size * 10
        while len(self.population) < pop_size and attempts < max_attempts:
            attempts += 1
            depth = random.randint(self.config["min_depth"], self.config["max_depth"])
            expr = self._generate_random_expression(depth)

            if len(expr) > self.config["max_expression_length"]:
                continue

            h = _expression_hash(expr)
            if h in self._expression_hashes:
                continue

            individual = GPIndividual(expression=expr, generation=0)
            self.population.append(individual)
            self._expression_hashes.add(h)

        logger.info(f"种群初始化完成: {len(self.population)} 个体 "
                     f"(warm_start={ws_count}, random={len(self.population) - ws_count})")
        return self.population

    # ─── 遗传操作：选择 ───

    def _selection(self) -> GPIndividual:
        """锦标赛选择"""
        k = min(self.config["tournament_size"], len(self.population))
        candidates = random.sample(self.population, k)
        return max(candidates, key=lambda x: x.fitness)

    # ─── 遗传操作：字符串交叉 ───

    def _crossover(self, parent1: GPIndividual, parent2: GPIndividual) -> Tuple[GPIndividual, GPIndividual]:
        """
        字符串层面的交叉操作

        三种模式：
        1. 算术组合: expr1 + op + expr2
        2. 算子替换交叉: 取 parent1 的算子 + parent2 的数据
        3. 子表达式交换: 从两者中各取子表达式组合
        """
        children = []

        for p1, p2 in [(parent1, parent2), (parent2, parent1)]:
            method = random.choice(["combine", "operator_swap", "subexpression_swap"])

            if method == "combine":
                # 模式1: 算术拼接
                op = random.choice(COMBINE_OPS)
                combined = f"({p1.expression} {op} {p2.expression})"
                if len(combined) <= self.config["max_expression_length"]:
                    child_expr = combined
                else:
                    # 太长了，只取 p1 加上一个简单终端
                    term = random.choice(DATA_TERMINALS)
                    child_expr = f"({p1.expression} + {term})"

            elif method == "operator_swap":
                # 模式2: 算子替换交叉
                child_expr = self._swap_operator_from(p1.expression, p2.expression)
                if not child_expr:
                    child_expr = p1.expression

            elif method == "subexpression_swap":
                # 模式3: 子表达式交换
                child_expr = self._subexpression_swap(p1.expression, p2.expression)
                if not child_expr:
                    child_expr = p1.expression

            else:
                child_expr = p1.expression

            child = GPIndividual(expression=child_expr, generation=self.generation)
            children.append(child)

        return children[0], children[1]

    def _swap_operator_from(self, target_expr: str, source_expr: str) -> Optional[str]:
        """从 source 中提取算子，替换 target 中一个同类算子"""
        target_ops = _extract_operator_tokens(target_expr)
        source_ops = _extract_operator_tokens(source_expr)

        if not target_ops or not source_ops:
            return None

        # 找同类算子替换
        for src_op in source_ops:
            src_arity = _get_op_info(src_op)
            if not src_arity:
                continue
            _, src_ar = src_arity

            for tgt_op in target_ops:
                tgt_info = _get_op_info(tgt_op)
                if not tgt_info:
                    continue
                _, tgt_ar = tgt_info

                if src_ar != tgt_ar or src_op == tgt_op:
                    continue

                # 参数类型兼容性检查
                if src_ar == 2:
                    if _is_parametric(src_op) != _is_parametric(tgt_op):
                        continue
                    if _is_dual_data(src_op) != _is_dual_data(tgt_op):
                        continue

                # 用正则精确替换第一个匹配
                new_expr = re.sub(
                    rf'\b{re.escape(tgt_op)}\b',
                    src_op,
                    target_expr,
                    count=1
                )
                if new_expr != target_expr:
                    return new_expr

        return None

    def _subexpression_swap(self, expr1: str, expr2: str) -> Optional[str]:
        """从 expr1 取算子 + expr2 的参数组合"""
        parsed1 = _parse_top_level_call(expr1)
        if not parsed1:
            return None

        op_name, inner1 = parsed1
        parsed2 = _parse_top_level_call(expr2)

        if parsed2:
            op_name2, inner2 = parsed2
            # 取 expr2 的第一个参数替换到 expr1
            args2 = _split_args(inner2)
            if args2:
                args1 = _split_args(inner1)
                if args1:
                    # 替换 expr1 的第一个参数
                    new_inner = args2[0] + ", " + ", ".join(args1[1:])
                    result = f"{op_name}({new_inner})"
                    if len(result) <= self.config["max_expression_length"]:
                        return result
        else:
            # expr2 是终端，替换 expr1 的第一个参数
            args1 = _split_args(inner1)
            if args1:
                new_inner = expr2 + ", " + ", ".join(args1[1:])
                result = f"{op_name}({new_inner})"
                if len(result) <= self.config["max_expression_length"]:
                    return result

        return None

    # ─── 遗传操作：算子感知字符串变异 ───

    def _mutate(self, individual: GPIndividual) -> GPIndividual:
        """
        算子感知的字符串变异

        5种变异模式：
        1. replace_operator: 替换算子（同 arity 算子间替换）
        2. adjust_param: 调整参数（在合理范围内微调）
        3. replace_terminal: 替换数据终端
        4. wrap_operator: 包裹新算子（外层加一元算子）
        5. combine_divide: 与另一个表达式组合
        """
        expr = individual.expression
        if not expr:
            return individual

        mutation_type = random.choices(
            ["replace_operator", "adjust_param", "replace_terminal",
             "wrap_operator", "combine"],
            weights=[3, 3, 2, 2, 2],
            k=1
        )[0]

        new_expr = expr

        if mutation_type == "replace_operator":
            new_expr = self._mutate_replace_operator(expr)
        elif mutation_type == "adjust_param":
            new_expr = self._mutate_adjust_param(expr)
        elif mutation_type == "replace_terminal":
            new_expr = self._mutate_replace_terminal(expr)
        elif mutation_type == "wrap_operator":
            new_expr = self._mutate_wrap_operator(expr)
        elif mutation_type == "combine":
            new_expr = self._mutate_combine(expr)

        # 长度检查
        if len(new_expr) > self.config["max_expression_length"] or new_expr == expr:
            new_expr = self._generate_random_expression(random.randint(1, 3))

        mutant = GPIndividual(expression=new_expr, generation=self.generation)
        return mutant

    def _mutate_replace_operator(self, expr: str) -> str:
        """替换算子：同 arity 同类型算子间替换"""
        ops = _extract_operator_tokens(expr)
        if not ops:
            return expr

        target_op = random.choice(ops)

        # 找同类型同类别的替换候选
        candidates = _get_same_arity_ops(target_op)

        # 进一步过滤参数兼容性
        if _is_parametric(target_op):
            candidates = [op for op in candidates if _is_parametric(op)]
        elif _is_dual_data(target_op):
            candidates = [op for op in candidates if _is_dual_data(op)]
        elif _get_op_info(target_op) and _get_op_info(target_op)[1] == 2:
            # arity=2 非参数非双数据的情况不应该存在，但保险起见
            candidates = [op for op in candidates if _is_parametric(op)]

        if not candidates:
            return expr

        new_op = random.choice(candidates)
        new_expr = re.sub(rf'\b{re.escape(target_op)}\b', new_op, expr, count=1)
        return new_expr

    def _mutate_adjust_param(self, expr: str) -> str:
        """调整参数：在合理范围内微调"""
        param_ops = _extract_parametric_ops(expr)
        if not param_ops:
            return expr

        op_name, p_start, p_end, old_val = random.choice(param_ops)
        lo, hi = PARAMETRIC_OPS.get(op_name, (2, 120))

        # 在原值附近微调
        delta = random.randint(max(-10, -(old_val - lo) // 2), min(10, (hi - old_val) // 2))
        new_val = max(lo, min(hi, old_val + delta))
        if new_val == old_val:
            new_val = random.randint(lo, hi)

        new_expr = expr[:p_start] + str(new_val) + expr[p_end:]
        return new_expr

    def _mutate_replace_terminal(self, expr: str) -> str:
        """替换数据终端"""
        terminals = _extract_data_terminals(expr)
        if not terminals:
            return expr

        t_name, t_start, t_end = random.choice(terminals)
        others = [t for t in DATA_TERMINALS if t != t_name]
        if not others:
            return expr

        new_term = random.choice(others)
        new_expr = expr[:t_start] + new_term + expr[t_end:]
        return new_expr

    def _mutate_wrap_operator(self, expr: str) -> str:
        """包裹新算子：在外层加一个一元算子"""
        if len(expr) > self.config["max_expression_length"] - 15:
            return expr

        wrapper = random.choice(OPERATOR_GROUPS["arity_1"])
        new_expr = f"{wrapper}({expr})"

        # 检查深度
        if _expression_depth(new_expr) > self.config["max_depth"] + 1:
            return expr

        return new_expr

    def _mutate_combine(self, expr: str) -> str:
        """组合变异：与另一个简单表达式组合"""
        other = self._generate_random_expression(random.randint(1, 2))

        method = random.choice(["simple", "ranked", "div_std"])

        if method == "simple":
            op = random.choice(["+", "-", "*", "/"])
            new_expr = f"({expr} {op} {other})"
        elif method == "ranked":
            new_expr = f"(rank({expr}) * {other})"
        elif method == "div_std":
            window = random.randint(5, 60)
            new_expr = f"({expr} / ts_std({expr}, {window}))"

        return new_expr

    # ─── 复制 ───

    def _copy(self, individual: GPIndividual) -> GPIndividual:
        """复制个体"""
        copy_ind = individual.clone()
        copy_ind.generation = self.generation
        return copy_ind

    def copy(self) -> "GeneticProgrammer":
        """复制引擎"""
        return copy.deepcopy(self)

    # ─── 进化循环 ───

    def evolve(self, data: pd.DataFrame, warm_start_exprs: List[str] = None,
               fitness_evaluator=None) -> List[GPIndividual]:
        """
        执行进化

        Args:
            data: OHLCV数据
            warm_start_exprs: 已知有效因子表达式（Warm Start），直接使用字符串
            fitness_evaluator: 适应度评估函数 (expression, data) -> dict

        Returns:
            最优因子列表
        """
        if fitness_evaluator:
            self.set_fitness_evaluator(fitness_evaluator)

        if not hasattr(self, "_fitness_evaluator"):
            raise ValueError("请先设置适应度评估函数")

        # 初始化种群
        self.initialize_population(warm_start_exprs)
        self.generation = 0
        self.history = []

        stagnation_count = 0
        prev_best_fitness = -float("inf")

        logger.info(f"🧬 开始进化: 种群={self.config['population_size']}, "
                     f"最大代数={self.config['max_generations']}")

        for gen in range(self.config["max_generations"]):
            self.generation = gen
            gen_start = time.time()

            logger.info(f"═══ 进化第 {gen+1}/{self.config['max_generations']} 代 ═══")

            # 1. 评估适应度
            self._evaluate_population(data)

            # 2. 记录统计
            fitnesses = [ind.fitness for ind in self.population if ind.fitness > 0]
            avg_fitness = np.mean(fitnesses) if fitnesses else 0
            best = max(self.population, key=lambda x: x.fitness) if self.population else None
            valid_count = len(fitnesses)
            gen_elapsed = time.time() - gen_start

            gen_stats = {
                "generation": gen + 1,
                "avg_fitness": round(avg_fitness, 4),
                "best_fitness": round(best.fitness, 4) if best else 0,
                "population_size": len(self.population),
                "valid_factors": valid_count,
                "unique_expressions": len(self._expression_hashes),
                "best_expression": (best.expression[:100] if best else ""),
                "best_ic": round(best.ic_mean, 4) if best else 0,
                "best_ir": round(best.ir, 4) if best else 0,
                "time": round(gen_elapsed, 2),
            }
            self.history.append(gen_stats)

            logger.info(f"  最佳适应度: {gen_stats['best_fitness']:.4f} | "
                         f"平均: {gen_stats['avg_fitness']:.4f} | "
                         f"有效因子: {valid_count}/{len(self.population)} | "
                         f"耗时: {gen_elapsed:.1f}s")
            if best:
                logger.info(f"  最佳因子: {best.expression[:80]}")

            # 7. 更新最佳个体（在检查停止条件之前）
            if best and (not self.best_individual or best.fitness > self.best_individual.fitness):
                self.best_individual = best

            # 3. 检查停止条件
            if best and best.fitness >= self.config["target_fitness"]:
                logger.info(f"🎉 达到目标适应度 {self.config['target_fitness']}")
                break

            if best and abs(best.fitness - prev_best_fitness) < 0.0001:
                stagnation_count += 1
                if stagnation_count >= self.config["stagnation_limit"]:
                    logger.info(f"⏹️ 连续 {stagnation_count} 代无改善，停止进化")
                    break
            else:
                stagnation_count = 0
                prev_best_fitness = best.fitness if best else prev_best_fitness

            # 4. 精英保留
            self.population.sort(key=lambda x: -x.fitness)
            elites = [ind.clone() for ind in self.population[:self.config["elite_size"]]]
            for e in elites:
                e.is_elite = True

            # 5. 生成下一代
            new_population = list(elites)

            # 重建哈希集合
            self._expression_hashes = set()
            for ind in new_population:
                self._expression_hashes.add(_expression_hash(ind.expression))

            while len(new_population) < self.config["population_size"]:
                r = random.random()

                if r < self.config["crossover_rate"]:
                    p1 = self._selection()
                    p2 = self._selection()
                    c1, c2 = self._crossover(p1, p2)
                    new_population.extend([c1, c2])
                elif r < self.config["crossover_rate"] + self.config["mutation_rate"]:
                    p = self._selection()
                    m = self._mutate(p)
                    new_population.append(m)
                else:
                    p = self._selection()
                    new_population.append(self._copy(p))

            # 6. 多样性过滤
            self.population = self._filter_diversity(new_population)
            self.elite_archive = elites

            # 种群过小时补充随机个体
            if len(self.population) < self.config["population_size"] // 2:
                shortage = self.config["population_size"] - len(self.population)
                for _ in range(min(shortage, 20)):
                    expr = self._generate_random_expression(
                        random.randint(self.config["min_depth"], self.config["max_depth"])
                    )
                    if len(expr) <= self.config["max_expression_length"]:
                        h = _expression_hash(expr)
                        if h not in self._expression_hashes:
                            self.population.append(
                                GPIndividual(expression=expr, generation=self.generation)
                            )
                            self._expression_hashes.add(h)

        # 最终评估
        self._evaluate_population(data)
        self.population.sort(key=lambda x: -x.fitness)

        if self.best_individual:
            logger.info(f"✅ 进化完成! 最佳因子: {self.best_individual.expression}")
            logger.info(f"   适应度: {self.best_individual.fitness:.4f} | "
                         f"IC: {self.best_individual.ic_mean:.4f} | "
                         f"IR: {self.best_individual.ir:.4f}")
        else:
            logger.warning("⚠️ 进化完成但未找到有效因子")

        return self.population[:self.config["elite_size"]]

    # ─── 评估 ───

    def _evaluate_population(self, data: pd.DataFrame):
        """评估种群中所有个体的适应度"""
        if self.config["parallel_workers"] > 1 and len(self.population) > 5:
            with ThreadPoolExecutor(max_workers=self.config["parallel_workers"]) as executor:
                futures = {}
                for ind in self.population:
                    future = executor.submit(self._evaluate_single, ind, data)
                    futures[future] = ind

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            ind = futures[future]
                            ind.fitness = result.get("fitness", 0)
                            ind.ic_mean = result.get("ic_mean", 0)
                            ind.ir = result.get("ir", 0)
                            ind.sharpe = result.get("sharpe", 0)
                    except Exception as e:
                        logger.debug(f"评估失败: {e}")
        else:
            for ind in self.population:
                result = self._evaluate_single(ind, data)
                if result:
                    ind.fitness = result.get("fitness", 0)
                    ind.ic_mean = result.get("ic_mean", 0)
                    ind.ir = result.get("ir", 0)
                    ind.sharpe = result.get("sharpe", 0)

    def _evaluate_single(self, individual: GPIndividual, data: pd.DataFrame) -> Optional[Dict]:
        """评估单个个体"""
        try:
            t0 = time.time()
            result = self._fitness_evaluator(individual.expression, data)
            individual.evaluation_time = time.time() - t0
            return result
        except Exception as e:
            logger.debug(f"因子评估失败 [{individual.expression[:50]}]: {e}")
            return None

    def _filter_diversity(self, population: List[GPIndividual]) -> List[GPIndividual]:
        """多样性过滤：基于表达式哈希去重"""
        filtered = []
        seen_hashes = set()

        for ind in population:
            h = _expression_hash(ind.expression)
            if h not in seen_hashes:
                filtered.append(ind)
                seen_hashes.add(h)

        # 按适应度排序后截断
        filtered.sort(key=lambda x: -x.fitness)
        result = filtered[:self.config["population_size"]]

        # 更新哈希集合
        self._expression_hashes = {_expression_hash(ind.expression) for ind in result}

        return result
