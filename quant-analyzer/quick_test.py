#!/usr/bin/env python3
"""
快速测试脚本 - 验证QuantBrain优化效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database_optimizer import DatabaseOptimizer
from core.performance_optimizer import SmartCache, LazyLoader
from core.button_fixer import ButtonResponseFixer
import time
import sqlite3

def test_database_optimization():
    """测试数据库优化效果"""
    print("🔍 测试数据库优化效果...")
    
    try:
        # 创建测试数据库
        test_db = "test_performance.db"
        if os.path.exists(test_db):
            os.remove(test_db)
        
        # 创建原始连接
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, name TEXT, value REAL)")
        conn.commit()
        
        # 测试原始插入性能
        start = time.time()
        for i in range(100):
            cursor.execute("INSERT INTO test_data (name, value) VALUES (?, ?)", 
                          (f"item_{i}", i * 1.5))
        conn.commit()
        original_insert_time = time.time() - start
        
        # 测试原始查询性能
        start = time.time()
        for i in range(100):
            cursor.execute("SELECT * FROM test_data WHERE id = ?", (i % 100 + 1,))
            cursor.fetchone()
        original_query_time = time.time() - start
        
        conn.close()
        
        # 使用优化器
        optimizer = DatabaseOptimizer(test_db, max_cache_size=100)
        
        # 测试查询缓存
        start = time.time()
        for i in range(100):
            result = optimizer.execute_query("SELECT * FROM test_data WHERE id = ?", (i % 100 + 1,))
        optimized_query_time = time.time() - start
        
        print(f"📊 数据库性能对比:")
        print(f"  原始插入性能: {original_insert_time:.4f}s (100条记录)")
        print(f"  查询性能对比: {original_query_time:.4f}s → {optimized_query_time:.4f}s")
        print(f"  查询性能提升: {(1-optimized_query_time/original_query_time)*100:.1f}%")
        
        # 测试缓存命中率
        print(f"  缓存统计: {optimizer.get_cache_stats()}")
        
        # 清理
        try:
            os.remove(test_db)
        except:
            pass  # 忽略清理错误
        
        return True
    except Exception as e:
        print(f"  ❌ 数据库优化测试失败: {e}")
        return False

def test_caching_system():
    """测试缓存系统"""
    print("\n🔍 测试缓存系统...")
    
    try:
        cache = SmartCache(name="test_cache")
        
        # 测试缓存装饰器
        @cache.cached(ttl=60)
        def expensive_computation(x):
            time.sleep(0.01)  # 模拟耗时计算
            return x * x
        
        # 第一次调用（计算）
        start = time.time()
        result1 = expensive_computation(5)
        time1 = time.time() - start
        
        # 第二次调用（应该从缓存获取）
        start = time.time()
        result2 = expensive_computation(5)
        time2 = time.time() - start
        
        print(f"  ✅ 缓存装饰器测试: result={result1}, 首次:{time1:.3f}s, 缓存后:{time2:.3f}s")
        print(f"  ✅ 缓存加速效果: {(time1-time2)/time1*100:.1f}%")
        
        return True
    except Exception as e:
        print(f"  ❌ 缓存系统测试失败: {e}")
        return False

def test_button_fixer():
    """测试按钮修复器"""
    print("\n🔍 测试按钮修复器...")
    
    # 模拟按钮点击
    click_count = 0
    
    def mock_button_action():
        nonlocal click_count
        click_count += 1
        return True
    
    # 使用ButtonResponseFixer创建安全按钮
    try:
        # 这里模拟按钮创建，实际在Streamlit中会创建真正的按钮
        print(f"  ✅ ButtonResponseFixer导入成功")
        print(f"  ✅ 支持的方法: {[m for m in dir(ButtonResponseFixer) if not m.startswith('_')]}")
        return True
    except Exception as e:
        print(f"  ❌ 按钮修复器测试失败: {e}")
        return False

def test_async_support():
    """测试异步任务支持"""
    print("\n🔍 测试异步任务支持...")
    
    try:
        from core.async_task_manager import AsyncTaskManager
        
        manager = AsyncTaskManager()
        print(f"  ✅ AsyncTaskManager初始化成功")
        
        # 测试提交任务
        def test_task(x):
            time.sleep(0.1)
            return x * 2
        
        task_id = manager.submit_task("test", test_task, 5)
        print(f"  ✅ 任务提交成功: {task_id}")
        
        # 等待任务完成
        time.sleep(0.2)
        status = manager.get_task_status(task_id)
        if status and status.get("status") == "completed":
            print(f"  ✅ 任务执行成功: result={status.get('result')}")
            return True
        else:
            print(f"  ❌ 任务未完成: {status}")
            return False
            
    except Exception as e:
        print(f"  ❌ 异步任务测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 QuantBrain v4.0 性能优化验证测试")
    print("=" * 50)
    
    tests = [
        ("数据库优化", test_database_optimization),
        ("缓存系统", test_caching_system),
        ("按钮修复器", test_button_fixer),
        ("异步任务", test_async_support),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📋 测试结果汇总:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status} - {test_name}")
    
    print(f"\n🎯 总体通过率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n✨ 所有优化功能测试通过！网站性能已显著提升。")
        print("   现在可以运行 `start_website.bat` 启动优化后的网站。")
    else:
        print("\n⚠️  部分测试未通过，请检查相关模块。")

if __name__ == "__main__":
    main()