"""
端到端进化流程测试脚本
验证从数据加载到策略输出的完整流水线
"""
import sys
import os
import logging

# 设置项目根目录
PROJECT_ROOT = r"c:\Users\Twilight\WorkBuddy\20260402202410\QuantAnalyzer\quant-analyzer"
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# 配置日志（输出到控制台）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """测试所有核心模块能否正常导入"""
    print("\n" + "="*60)
    print("📦 步骤1: 测试模块导入")
    print("="*60)
    
    modules = [
        ("pandas", "pd"),
        ("numpy", "np"),
        ("core.multi_data_source", "MultiDataSource"),
        ("core.alphaforge.factor_engine", "FactorEngine"),
        ("core.alphaforge.genetic_programming", "GeneticProgrammer"),
        ("core.alphaforge.factor_analyzer", "FactorAnalyzer"),
        ("core.alphaforge.strategy_ensemble", "StrategyEnsemble"),
        ("core.alphaforge.auto_scheduler", "EvolutionScheduler"),
    ]
    
    ok = []
    fail = []
    for module_name, attr in modules:
        try:
            mod = __import__(module_name, fromlist=[attr])
            if hasattr(mod, attr):
                obj = getattr(mod, attr)
                print(f"  ✅ {module_name}.{attr}")
                ok.append(module_name)
            else:
                print(f"  ❌ {module_name} — 缺少 {attr}")
                fail.append(module_name)
        except Exception as e:
            print(f"  ❌ {module_name}: {e}")
            fail.append(module_name)
    
    print(f"\n  导入结果: {len(ok)}/{len(modules)} 成功")
    return len(fail) == 0


def test_data_loading():
    """测试数据加载（含降级方案）"""
    print("\n" + "="*60)
    print("📊 步骤2: 测试数据加载")
    print("="*60)
    
    from core.alphaforge.auto_scheduler import EvolutionScheduler
    from core.alphaforge.config import EvolutionConfig
    
    config = EvolutionConfig()
    scheduler = EvolutionScheduler(config=config, store=None)
    
    # 直接调用 _load_data 测试
    data = scheduler._load_data()
    
    if data and len(data) > 0:
        print(f"  ✅ 数据加载成功！获取到 {len(data)} 只股票")
        for code, df in list(data.items())[:3]:
            print(f"     - {code}: {len(df)} 行, 列={list(df.columns)[:5]}...")
            print(f"       日期范围: {df['date'].min()} ~ {df['date'].max()}")
            print(f"       价格范围: {df['close'].min():.2f} ~ {df['close'].max():.2f}")
        return True
    else:
        print("  ❌ 数据加载失败")
        return False


def test_factor_computation():
    """测试因子计算"""
    print("\n" + "="*60)
    print("🧪 步骤3: 测试因子计算")
    print("="*60)
    
    from core.alphaforge.factor_engine import FactorEngine
    
    engine = FactorEngine()
    
    # 获取数据
    from core.alphaforge.auto_scheduler import EvolutionScheduler
    from core.alphaforge.config import EvolutionConfig
    config = EvolutionConfig()
    scheduler = EvolutionScheduler(config=config, store=None)
    data = scheduler._load_data()
    
    if not data:
        print("  ❌ 无数据，跳过因子计算")
        return False
    
    # 取第一只股票测试
    stock_code = list(data.keys())[0]
    df = data[stock_code]
    
    # 测试内置因子
    built_in_factors = ["MA_DEVIATION_20", "RSI_14", "MACD_HIST", "VOLUME_CHANGE_5"]
    
    success_count = 0
    for factor_name in built_in_factors:
        try:
            result = engine.compute(factor_name, df)
            if result is not None and len(result) > 0:
                valid_count = result.notna().sum()
                print(f"  ✅ {factor_name}: {valid_count}/{len(result)} 有效值")
                success_count += 1
            else:
                print(f"  ⚠️ {factor_name}: 空结果")
        except Exception as e:
            print(f"  ❌ {factor_name}: {e}")
    
    print(f"\n  因子计算: {success_count}/{len(built_in_factors)} 成功")
    return success_count >= 2


def test_factor_analysis():
    """测试因子分析（IC评估）"""
    print("\n" + "="*60)
    print("📈 步骤4: 测试因子分析 (IC/IR)")
    print("="*60)
    
    from core.alphaforge.factor_analyzer import FactorAnalyzer
    from core.alphaforge.auto_scheduler import EvolutionScheduler
    from core.alphaforge.config import EvolutionConfig
    
    config = EvolutionConfig()
    scheduler = EvolutionScheduler(config=config, store=None)
    data = scheduler._load_data()
    
    if not data or len(data) < 2:
        print("  ❌ 数据不足，跳过分析")
        return False
    
    analyzer = FactorAnalyzer()
    
    # 取前3只股票的截面数据做IC测试
    sample_data = dict(list(data.items())[:3])
    
    # 构建截面因子值
    factor_values = {}
    returns = {}
    
    for code, df in sample_data.items():
        from core.alphaforge.factor_engine import FactorEngine
        engine = FactorEngine()
        
        try:
            factor_result = engine.compute("RSI_14", df)
            if factor_result is not None and len(factor_result) > 10:
                # 取最后一个有效值作为截面数据
                valid_idx = factor_result.dropna().index
                if len(valid_idx) > 0:
                    last_valid = valid_idx[-1]
                    factor_values[code] = factor_result.iloc[last_valid]
                    
                    # 未来一期收益
                    if last_valid + 1 < len(df):
                        future_ret = (df['close'].iloc[last_valid+1] / df['close'].iloc[last_valid]) - 1
                        returns[code] = future_ret
        except Exception as e:
            continue
    
    if len(factor_values) >= 2 and len(returns) >= 2:
        ic = analyzer.evaluate(factor_values, returns, method="ic")
        print(f"  ✅ IC分析完成: IC={ic.get('ic', 'N/A'):.4f}" if isinstance(ic, dict) else f"  ✅ IC分析完成: {ic}")
        return True
    else:
        print(f"  ⚠️ 截面数据不足 (factors={len(factor_values)}, returns={len(returns)})")
        return False


def test_genetic_programming():
    """测试遗传编程"""
    print("\n" + "="*60)
    print("🧬 步骤5: 测试遗传编程进化")
    print("="*60)
    
    from core.alphaforge.genetic_programming import GeneticProgrammer
    from core.alphaforge.auto_scheduler import EvolutionScheduler
    from core.alphaforge.config import EvolutionConfig
    
    config = EvolutionConfig()
    config.generation_size = 6   # 小规模快速测试
    config.elite_size = 2
    config.mutation_rate = 0.4
    config.crossover_rate = 0.4
    
    scheduler = EvolutionScheduler(config=config, store=None)
    data = scheduler._load_data()
    
    gp = GeneticProgrammer(config=config)
    
    # 准备训练数据
    train_data = {}
    for code, df in data.items():
        if len(df) >= 60:
            train_data[code] = df
    
    # 种子表达式
    seed_expressions = [
        "ts_mean(close, 5) / ts_mean(close, 20) - 1",
        "corr(close, volume, 10)",
        "std_dev(returns, 20)",
        "(high - low) / close",
        "-delta(close, 5) / ts_std_dev(close, 20)",
        "volume / ts_mean(volume, 20) - 1",
    ]
    
    # 运行3代快速测试
    print("  🔄 开始 GP 进化 (3代, pop=6)...")
    try:
        best_individuals = gp.evolve(
            expressions=seed_expressions,
            data=train_data,
            generations=3,
        )
        
        if best_individuals:
            print(f"  ✅ GP 进化完成! 获得 {len(best_individuals)} 个优秀个体")
            for i, ind in enumerate(best_individuals[:3]):
                expr = getattr(ind, 'expression', str(ind))
                fitness = getattr(ind, 'fitness', 'N/A')
                print(f"     #{i+1}: fitness={fitness}, expr={str(expr)[:60]}...")
            return True
        else:
            print("  ⚠️ GP 进化完成但没有产生有效结果")
            return False
            
    except Exception as e:
        print(f"  ❌ GP 进化出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_ensemble():
    """测试策略组合"""
    print("\n" + "="*60)
    print("🎯 步骤6: 测试策略组合")
    print("="*60)
    
    from core.alphaforge.strategy_ensemble import StrategyEnsemble
    from core.alphaforge.auto_scheduler import EvolutionScheduler
    from core.alphaforge.config import EvolutionConfig
    
    config = EvolutionConfig()
    scheduler = EvolutionScheduler(config=config, store=None)
    data = scheduler._load_data()
    
    ensemble = StrategyEnsemble(config=config)
    
    # 构造假因子结果（因为前面步骤可能失败）
    factor_results = []
    stock_codes = list(data.keys())[:5]
    
    for code in stock_codes:
        df = data[code]
        factor_results.append({
            'code': code,
            'RSI': df['close'].pct_change().rolling(14).apply(lambda x: x.dropna().std() if len(x.dropna())>0 else 50, raw=False).iloc[-1] if len(df)>14 else 50.0,
            'MOM': (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) if len(df)>20 else 0.0,
            'VOL_RATIO': (df['volume'].iloc[-5:].mean() / df['volume'].iloc[-20:].mean() - 1) if len(df)>20 else 0.0,
        })
    
    try:
        result = ensemble.build_ensemble(factor_results, data)
        
        if result:
            score = getattr(result, 'score', getattr(result, 'get', lambda k: None)('score', 'N/A'))
            trades = getattr(result, 'total_trades', getattr(result, 'get', lambda k: None)('total_trades', 'N/A'))
            
            # 尝试转为字典输出
            if hasattr(result, 'to_dict'):
                info = result.to_dict()
            elif isinstance(result, dict):
                info = result
            else:
                info = str(result)
            
            print(f"  ✅ 策略组合构建成功!")
            print(f"     结果摘要: {str(info)[:200]}...")
            return True
        else:
            print("  ⚠️ 策略组合返回空")
            return False
            
    except Exception as e:
        print(f"  ❌ 策略组合出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_full_evolution():
    """运行完整的进化流程"""
    print("\n" + "="*60)
    print("🚀 步骤7: 完整进化流程测试")
    print("="*60)
    
    from core.alphaforge.auto_scheduler import EvolutionScheduler
    from core.alphaforge.config import EvolutionConfig
    
    config = EvolutionConfig()
    # 快速测试参数
    config.generation_size = 6
    config.elite_size = 2
    config.generations = 2
    config.lookback_days = 365
    
    scheduler = EvolutionScheduler(config=config, store=None)
    
    print("  🔄 执行完整进化流程...")
    try:
        result = scheduler.run_evolution()
        
        if result:
            print(f"  ✅ 完整进化流程执行成功!")
            
            # 输出结果摘要
            if hasattr(result, 'to_dict'):
                summary = result.to_dict()
            elif isinstance(result, dict):
                summary = result
            else:
                summary = {'result': str(result)}
            
            for key, val in summary.items():
                if isinstance(val, (int, float, str, bool)):
                    print(f"     {key}: {val}")
                elif isinstance(val, dict):
                    for k2, v2 in list(val.items())[:5]:
                        print(f"     {key}.{k2}: {v2}")
            
            return True
        else:
            print("  ❌ 进化流程返回空结果")
            return False
            
    except Exception as e:
        print(f"  ❌ 完整进化流程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════
# 主测试入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "█"*60)
    print("█  QuantBrain AlphaForge 端到端进化流程测试")
    print("█" + " "*58 + "█")
    print(f"█  项目路径: {PROJECT_ROOT}")
    print(f"█  时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("█"*60)
    
    results = {}
    
    # 按顺序执行每个步骤
    results['imports'] = test_imports()
    results['data'] = test_data_loading()
    
    if results['data']:
        results['factor_compute'] = test_factor_computation()
        results['factor_analysis'] = test_factor_analysis()
        results['gp'] = test_genetic_programming()
        results['ensemble'] = test_strategy_ensemble()
    else:
        results['factor_compute'] = False
        results['factor_analysis'] = False
        results['gp'] = False
        results['ensemble'] = False
    
    results['full_evolution'] = run_full_evolution()
    
    # 输出总结
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)
    
    total = len(results)
    passed = sum(results.values())
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}")
    
    print(f"\n  总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n  🎉 所有测试通过! 进化流程完全可用!")
    else:
        failed_steps = [k for k,v in results.items() if not v]
        print(f"\n  ⚠️ 失败步骤: {', '.join(failed_steps)}")
    
    sys.exit(0 if passed == total else 1)
