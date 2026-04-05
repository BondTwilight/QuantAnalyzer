"""快速端到端测试 — 验证进化流水线修复"""
import sys, os
sys.path.insert(0, '.')

print('=== 测试1: 数据缓存层 ===')
from core.data_cache import DataCache
cache = DataCache()
stats = cache.get_cache_stats()
print(f'缓存初始化成功: {stats}')

print('\n=== 测试2: 模拟数据生成 ===')
from core.alphaforge.auto_scheduler import EvolutionScheduler
scheduler = EvolutionScheduler()
sim_data = scheduler._generate_simulated_data()
print(f'模拟数据生成: {list(sim_data.keys())}')
for code, df in sim_data.items():
    dmin = str(df["date"].min())
    dmax = str(df["date"].max())
    print(f'   {code}: {len(df)} 行, 日期范围 {dmin} ~ {dmax}')

print('\n=== 测试3: 缓存写入+读取 ===')
for code, df in sim_data.items():
    cache.save_stock_data(code, df, source='simulated')

loaded = cache.batch_load(list(sim_data.keys()))
print(f'缓存写入+读取: {len(loaded)}/{len(sim_data)} 只股票命中')

stats2 = cache.get_cache_stats()
print(f'更新后缓存统计: {stats2["stock_count"]}只股票, {stats2["total_rows"]}条记录, {stats2["file_size_mb"]}MB')

print('\n=== 测试4: 完整 _load_data 流程（含超时保护）===')
import time
t0 = time.time()
data = scheduler._load_data()
t1 = time.time()
print(f'_load_data 完成: 耗时 {t1-t0:.1f}s, 获取 {len(data)} 只股票')

print('\n=== 测试5: 快速进化流程 (quick模式) ===')
try:
    task = scheduler.run_evolution(task_type='quick', progress_cb=lambda p,m: None)
    print(f'进化完成! 状态={task.status}, 因子测试={task.factors_tested}, 有效因子={task.factors_valid}')
    print(f'最佳适应度={task.best_fitness:.4f}, 组合评分={task.ensemble_score:.1f}')
    if task.error:
        print(f'错误信息: {task.error[:200]}')
except Exception as e:
    print(f'进化异常: {e}')
    import traceback
    traceback.print_exc()

print('\n═══ 全部测试完成 ═══')
