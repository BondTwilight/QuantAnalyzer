"""测试重写后的 genetic_programming.py"""
import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np

from core.alphaforge.genetic_programming import (
    GeneticProgrammer, GPIndividual,
    REGISTERED_OPERATORS, PARAMETRIC_OPS, DUAL_DATA_OPS, DATA_TERMINALS,
    _parse_top_level_call, _split_args, _extract_parametric_ops, 
    _extract_data_terminals, _expression_depth, _expression_hash,
)

print('=== 1. 基础导入 ===')
print(f'  注册算子: {len(REGISTERED_OPERATORS)}')
print(f'  带参数算子: {len(PARAMETRIC_OPS)}')
print(f'  双数据算子: {DUAL_DATA_OPS}')

print('\n=== 2. 表达式解析 ===')
for t in ['ts_mean(close, 10)', 'rank(ts_mean(close, 5))', 'close',
           'ts_mean(close, 5) / ts_std(close, 5)', 'ts_corr(close, volume, 20)']:
    print(f'  {t:45s} -> {_parse_top_level_call(t)}')

print('\n=== 3. 参数提取 ===')
for t in ['ts_mean(close, 10)', 'rank(ts_mean(close, 5))', 'ts_corr(close, volume, 20)', 'rsi(ema(close, 5), 14)']:
    print(f'  {t:45s} -> {_extract_parametric_ops(t)}')

print('\n=== 4. 终端提取 ===')
for t in ['ts_mean(close, 10)', 'ts_corr(close, volume, 20)', 'max(high, low)']:
    print(f'  {t:35s} -> {_extract_data_terminals(t)}')

print('\n=== 5. 参数分割 ===')
for t in ['close, 10', 'ts_mean(close, 5), ts_std(close, 10)', 'close, volume, 20']:
    print(f'  {t:50s} -> {_split_args(t)}')

print('\n=== 6. GPIndividual ===')
ind = GPIndividual(expression='ts_mean(close, 10)', fitness=0.5, ic_mean=0.03)
print(f'  to_dict: {ind.to_dict()}')
print(f'  clone OK: {ind.clone().expression == ind.expression}')

print('\n=== 7. 随机表达式生成 (10个) ===')
gp = GeneticProgrammer()
for _ in range(10):
    expr = gp._generate_random_expression(np.random.randint(2, 5))
    d = _expression_depth(expr)
    print(f'  depth={d} len={len(expr):3d} {expr[:70]}')

print('\n=== 8. 种群初始化 ===')
warm = ['ts_mean(close, 10)', 'rsi(close, 14)', 'rank(ema(volume, 20))']
pop = gp.initialize_population(warm)
print(f'  种群大小: {len(pop)}')
print(f'  唯一哈希: {len(gp._expression_hashes)}')
for p in pop[:3]:
    print(f'    {p.expression}')

print('\n=== 9. 变异测试 ===')
base = 'ts_mean(close, 10)'
for _ in range(10):
    m = gp._mutate(GPIndividual(expression=base))
    print(f'  {base:30s} -> {m.expression}')

print('\n=== 10. 交叉测试 ===')
p1 = GPIndividual(expression='ts_mean(close, 10)')
p2 = GPIndividual(expression='rsi(volume, 14)')
for _ in range(6):
    c1, c2 = gp._crossover(p1, p2)
    print(f'  c1={c1.expression[:50]:50s} c2={c2.expression[:50]}')

print('\n=== 11. 完整进化 (小规模) ===')
np.random.seed(42)
n = 300
data = pd.DataFrame({
    'open': np.cumsum(np.random.randn(n)) + 100,
    'high': np.cumsum(np.random.randn(n)) + 101,
    'low': np.cumsum(np.random.randn(n)) + 99,
    'close': np.cumsum(np.random.randn(n)) + 100,
    'volume': np.random.randint(1e6, 5e6, n).astype(float),
})

def fake_evaluator(expression, data):
    try:
        from core.alphaforge.factor_engine import FactorEngine
        engine = FactorEngine()
        values = engine.compute(expression, data)
        if values is None or values.empty or values.isna().all():
            return {'fitness': 0, 'ic_mean': 0, 'ir': 0, 'sharpe': 0}
        ret = data['close'].pct_change().shift(-1)
        valid = values.notna() & ret.notna()
        if valid.sum() < 20:
            return {'fitness': 0, 'ic_mean': 0, 'ir': 0, 'sharpe': 0}
        ic = values[valid].corr(ret[valid])
        fitness = min(abs(ic) * 100, 1.0) if not np.isnan(ic) else 0
        return {'fitness': fitness, 'ic_mean': ic if not np.isnan(ic) else 0, 'ir': 0, 'sharpe': 0}
    except:
        return {'fitness': 0, 'ic_mean': 0, 'ir': 0, 'sharpe': 0}

gp2 = GeneticProgrammer({
    'population_size': 30, 'max_generations': 5, 'elite_size': 5, 'parallel_workers': 2,
})
results = gp2.evolve(data, warm_start_exprs=['ts_mean(close, 10)', 'rsi(close, 14)'],
                      fitness_evaluator=fake_evaluator)

print(f'  结果数: {len(results)}')
print(f'  历史代数: {len(gp2.history)}')
for i, r in enumerate(results[:5]):
    print(f'  #{i+1} fit={r.fitness:.4f} ic={r.ic_mean:.4f} {r.expression[:60]}')
best = gp2.best_individual
print(f'  Best: {best.expression if best else "None"}')
print(f'  Best fitness: {best.fitness:.4f}' if best else '')

# 多样性检查：确保不是所有因子都一样
exprs = [r.expression for r in results]
unique = len(set(exprs))
print(f'\n=== 12. 多样性检查 ===')
print(f'  Top {len(results)} 中唯一表达式: {unique}/{len(results)}')
if unique >= 3:
    print('  PASS: 种群多样性良好')
else:
    print('  WARN: 多样性偏低')

print('\n=== ALL TESTS DONE ===')
