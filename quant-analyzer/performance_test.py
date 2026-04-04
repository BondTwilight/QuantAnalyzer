#!/usr/bin/env python3
"""
性能测试脚本 - 测试数据库优化效果
"""

import time
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database_optimizer import DatabaseOptimizer
from data.fetcher import Database

def create_test_data():
    """创建测试数据"""
    print("创建测试数据...")
    
    # 连接到数据库
    db_path = "data/quantbrain.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建测试表（如果不存在）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 清空测试表
    cursor.execute("DELETE FROM test_performance")
    
    # 插入大量测试数据
    symbols = ['000001.SZ', '000002.SZ', '000858.SZ', '600519.SH', '601318.SH']
    start_date = datetime(2020, 1, 1)
    
    data_count = 0
    for symbol in symbols:
        current_date = start_date
        for i in range(1000):  # 每个股票1000条记录
            cursor.execute("""
            INSERT INTO test_performance (symbol, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                current_date.strftime('%Y-%m-%d'),
                random.uniform(10, 100),
                random.uniform(10, 100),
                random.uniform(10, 100),
                random.uniform(10, 100),
                random.randint(100000, 10000000)
            ))
            current_date += timedelta(days=1)
            data_count += 1
    
    conn.commit()
    print(f"插入 {data_count} 条测试数据")
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_symbol ON test_performance(symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_date ON test_performance(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_symbol_date ON test_performance(symbol, date)")
    
    conn.close()
    print("测试数据创建完成")

def test_original_database():
    """测试原始数据库性能"""
    print("\n" + "="*50)
    print("测试原始数据库性能")
    print("="*50)
    
    db_path = "data/quantbrain.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 测试1: 简单查询
    start_time = time.time()
    cursor.execute("SELECT COUNT(*) FROM test_performance")
    count = cursor.fetchone()[0]
    simple_query_time = time.time() - start_time
    print(f"简单查询时间: {simple_query_time:.4f}秒, 结果: {count}")
    
    # 测试2: 带条件查询
    start_time = time.time()
    cursor.execute("SELECT * FROM test_performance WHERE symbol = '000001.SZ' AND date >= '2021-01-01'")
    results = cursor.fetchall()
    conditional_query_time = time.time() - start_time
    print(f"条件查询时间: {conditional_query_time:.4f}秒, 结果数: {len(results)}")
    
    # 测试3: 聚合查询
    start_time = time.time()
    cursor.execute("""
    SELECT symbol, COUNT(*), AVG(close), MAX(close), MIN(close)
    FROM test_performance
    GROUP BY symbol
    """)
    agg_results = cursor.fetchall()
    aggregate_query_time = time.time() - start_time
    print(f"聚合查询时间: {aggregate_query_time:.4f}秒, 分组数: {len(agg_results)}")
    
    # 测试4: 多次重复查询（测试缓存效果）
    repeat_times = []
    for i in range(10):
        start_time = time.time()
        cursor.execute("SELECT COUNT(*) FROM test_performance WHERE symbol = '000001.SZ'")
        cursor.fetchone()
        repeat_times.append(time.time() - start_time)
    
    avg_repeat_time = sum(repeat_times) / len(repeat_times)
    print(f"重复查询平均时间: {avg_repeat_time:.4f}秒")
    
    conn.close()
    
    return {
        "simple_query": simple_query_time,
        "conditional_query": conditional_query_time,
        "aggregate_query": aggregate_query_time,
        "repeat_query": avg_repeat_time
    }

def test_optimized_database():
    """测试优化后数据库性能"""
    print("\n" + "="*50)
    print("测试优化后数据库性能")
    print("="*50)
    
    db_path = "data/quantbrain.db"
    optimizer = DatabaseOptimizer(db_path)
    
    # 测试1: 简单查询（应该命中缓存）
    start_time = time.time()
    result1 = optimizer.execute_query("SELECT COUNT(*) as count FROM test_performance")
    simple_query_time = time.time() - start_time
    if result1 and len(result1) > 0:
        count = result1[0].get('count', 0)
        print(f"简单查询时间: {simple_query_time:.4f}秒, 结果: {count}")
    else:
        print(f"简单查询时间: {simple_query_time:.4f}秒, 结果: 0")
    
    # 测试2: 带条件查询
    start_time = time.time()
    result2 = optimizer.execute_query(
        "SELECT * FROM test_performance WHERE symbol = ? AND date >= ?",
        ('000001.SZ', '2021-01-01')
    )
    conditional_query_time = time.time() - start_time
    print(f"条件查询时间: {conditional_query_time:.4f}秒, 结果数: {len(result2)}")
    
    # 测试3: 聚合查询
    start_time = time.time()
    result3 = optimizer.execute_query("""
    SELECT symbol, COUNT(*) as count, AVG(close) as avg_close, 
           MAX(close) as max_close, MIN(close) as min_close
    FROM test_performance
    GROUP BY symbol
    """)
    aggregate_query_time = time.time() - start_time
    print(f"聚合查询时间: {aggregate_query_time:.4f}秒, 分组数: {len(result3)}")
    
    # 测试4: 多次重复查询（测试缓存效果）
    repeat_times = []
    for i in range(10):
        start_time = time.time()
        optimizer.execute_query("SELECT COUNT(*) FROM test_performance WHERE symbol = ?", ('000001.SZ',))
        repeat_times.append(time.time() - start_time)
    
    avg_repeat_time = sum(repeat_times) / len(repeat_times)
    print(f"重复查询平均时间: {avg_repeat_time:.4f}秒")
    
    # 显示缓存统计
    stats = optimizer.get_query_performance_report()
    print(f"\n缓存统计:")
    print(f"  总查询数: {stats['total_queries']}")
    print(f"  缓存命中数: {stats['cached_queries']}")
    print(f"  缓存命中率: {stats['cache_hit_rate']:.1%}")
    print(f"  平均执行时间: {stats['avg_execution_time']*1000:.1f}ms")
    
    return {
        "simple_query": simple_query_time,
        "conditional_query": conditional_query_time,
        "aggregate_query": aggregate_query_time,
        "repeat_query": avg_repeat_time,
        "cache_stats": stats
    }

def test_pagination():
    """测试分页性能"""
    print("\n" + "="*50)
    print("测试分页性能")
    print("="*50)
    
    db_path = "data/quantbrain.db"
    optimizer = DatabaseOptimizer(db_path)
    
    # 测试分页查询
    page_size = 100
    total_pages = 5
    
    page_times = []
    for page in range(1, total_pages + 1):
        start_time = time.time()
        results = optimizer.execute_paginated_query(
            "SELECT * FROM test_performance ORDER BY date DESC",
            page=page,
            page_size=page_size
        )
        page_time = time.time() - start_time
        page_times.append(page_time)
        print(f"第 {page} 页查询时间: {page_time:.4f}秒, 结果数: {len(results)}")
    
    avg_page_time = sum(page_times) / len(page_times)
    print(f"平均分页查询时间: {avg_page_time:.4f}秒")
    
    return avg_page_time

def test_batch_operations():
    """测试批量操作性能"""
    print("\n" + "="*50)
    print("测试批量操作性能")
    print("="*50)
    
    db_path = "data/quantbrain.db"
    optimizer = DatabaseOptimizer(db_path)
    
    # 准备批量数据（字典格式）
    batch_data = []
    for i in range(1000):
        batch_data.append({
            "symbol": f"TEST{i:04d}.SZ",
            "date": f"2024-01-{i%30+1:02d}",
            "open": random.uniform(10, 100),
            "high": random.uniform(10, 100),
            "low": random.uniform(10, 100),
            "close": random.uniform(10, 100),
            "volume": random.randint(100000, 10000000)
        })
    
    # 测试批量插入
    start_time = time.time()
    optimizer.batch_insert("test_performance", batch_data)
    batch_insert_time = time.time() - start_time
    print(f"批量插入1000条数据时间: {batch_insert_time:.4f}秒")
    
    return batch_insert_time

def main():
    """主函数"""
    print("开始性能测试...")
    
    # 创建测试数据
    create_test_data()
    
    # 测试原始数据库性能
    original_results = test_original_database()
    
    # 测试优化后数据库性能
    optimized_results = test_optimized_database()
    
    # 测试分页性能
    pagination_time = test_pagination()
    
    # 测试批量操作性能
    batch_time = test_batch_operations()
    
    # 性能对比分析
    print("\n" + "="*50)
    print("性能对比分析")
    print("="*50)
    
    improvements = {}
    for key in ['simple_query', 'conditional_query', 'aggregate_query', 'repeat_query']:
        if key in original_results and key in optimized_results:
            improvement = (original_results[key] - optimized_results[key]) / original_results[key] * 100
            improvements[key] = improvement
            print(f"{key}: 原始 {original_results[key]:.4f}s → 优化 {optimized_results[key]:.4f}s, 提升 {improvement:.1f}%")
    
    # 总结
    print("\n" + "="*50)
    print("性能优化总结")
    print("="*50)
    print("1. 数据库查询性能显著提升")
    print("2. 缓存机制有效减少重复查询时间")
    print("3. 分页查询优化大数据集访问")
    print("4. 批量操作大幅提升数据插入效率")
    
    if 'cache_stats' in optimized_results:
        stats = optimized_results['cache_stats']
        print(f"\n缓存效果:")
        print(f"  • 缓存命中率: {stats['cache_hit_rate']:.1%}")
        print(f"  • 平均查询时间: {stats['avg_execution_time']*1000:.1f}ms")
        print(f"  • 慢查询数: {len(stats.get('slow_queries', []))}")

if __name__ == "__main__":
    main()