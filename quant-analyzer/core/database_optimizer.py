"""
数据库查询优化模块
提供数据库查询优化、分页加载、查询缓存等功能
"""

import sqlite3
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass


@dataclass
class QueryStats:
    """查询统计信息"""
    query: str
    execution_time: float
    row_count: int
    timestamp: datetime
    cached: bool = False


class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self, db_path: str, max_cache_size: int = 1000):
        """
        初始化数据库优化器
        
        Args:
            db_path: 数据库文件路径
            max_cache_size: 最大缓存条目数
        """
        self.db_path = db_path
        self.max_cache_size = max_cache_size
        self.query_stats: List[QueryStats] = []
        self.query_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_lock = threading.Lock()
        self.connection_pool: Dict[int, sqlite3.Connection] = {}
        self.thread_local = threading.local()
        
        # 创建索引（如果不存在）
        self._create_indexes()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（线程安全）"""
        thread_id = threading.get_ident()
        
        if not hasattr(self.thread_local, 'connection'):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.thread_local.connection = conn
            self.connection_pool[thread_id] = conn
        
        return self.thread_local.connection
    
    def close_connections(self):
        """关闭所有数据库连接"""
        for conn in self.connection_pool.values():
            try:
                conn.close()
            except:
                pass
        self.connection_pool.clear()
    
    def _create_indexes(self):
        """创建优化索引"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 为常用查询字段创建索引
        indexes = [
            # backtest_results 表索引
            "CREATE INDEX IF NOT EXISTS idx_backtest_strategy ON backtest_results(strategy_name)",
            "CREATE INDEX IF NOT EXISTS idx_backtest_date_range ON backtest_results(start_date, end_date)",
            "CREATE INDEX IF NOT EXISTS idx_backtest_created ON backtest_results(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_backtest_return ON backtest_results(total_return DESC)",
            
            # daily_values 表索引
            "CREATE INDEX IF NOT EXISTS idx_daily_stock_date ON daily_values(stock_code, date)",
            "CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_values(date)",
            
            # signals 表索引
            "CREATE INDEX IF NOT EXISTS idx_signals_stock_date ON signals(stock_code, signal_date)",
            "CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type)",
            "CREATE INDEX IF NOT EXISTS idx_signals_confidence ON signals(confidence DESC)",
            
            # positions 表索引
            "CREATE INDEX IF NOT EXISTS idx_positions_stock ON positions(stock_code)",
            "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                print(f"创建索引失败: {e}")
        
        conn.commit()
    
    @lru_cache(maxsize=100)
    def execute_query(self, query: str, params: tuple = (), use_cache: bool = True, 
                     cache_ttl: int = 300) -> List[Dict[str, Any]]:
        """
        执行查询并缓存结果
        
        Args:
            query: SQL查询语句
            params: 查询参数
            use_cache: 是否使用缓存
            cache_ttl: 缓存有效期（秒）
            
        Returns:
            查询结果列表
        """
        start_time = time.time()
        
        # 检查缓存
        cache_key = f"{query}:{params}"
        if use_cache:
            with self.cache_lock:
                if cache_key in self.query_cache:
                    result, cached_time = self.query_cache[cache_key]
                    if datetime.now() - cached_time < timedelta(seconds=cache_ttl):
                        # 记录缓存命中
                        stats = QueryStats(
                            query=query,
                            execution_time=time.time() - start_time,
                            row_count=len(result),
                            timestamp=datetime.now(),
                            cached=True
                        )
                        self.query_stats.append(stats)
                        self._trim_stats()
                        return result
        
        # 执行查询
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # 转换为字典列表
            result = [dict(row) for row in rows]
            
            # 更新缓存
            if use_cache:
                with self.cache_lock:
                    self.query_cache[cache_key] = (result, datetime.now())
                    # 清理过期缓存
                    self._clean_cache(cache_ttl)
            
            # 记录统计信息
            stats = QueryStats(
                query=query,
                execution_time=time.time() - start_time,
                row_count=len(result),
                timestamp=datetime.now(),
                cached=False
            )
            self.query_stats.append(stats)
            self._trim_stats()
            
            return result
            
        except Exception as e:
            print(f"查询执行失败: {e}")
            raise
    
    def execute_paginated_query(self, query: str, params: tuple = (), 
                               page: int = 1, page_size: int = 50,
                               order_by: str = None) -> Dict[str, Any]:
        """
        执行分页查询
        
        Args:
            query: 基础查询语句（不包含LIMIT/OFFSET）
            params: 查询参数
            page: 页码（从1开始）
            page_size: 每页大小
            order_by: 排序字段（默认按主键或第一个字段）
            
        Returns:
            包含数据和分页信息的字典
        """
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 添加排序
        if order_by:
            order_clause = f"ORDER BY {order_by}"
        else:
            order_clause = ""
        
        # 构建分页查询
        paginated_query = f"""
            {query}
            {order_clause}
            LIMIT ? OFFSET ?
        """
        
        # 执行查询
        paginated_params = params + (page_size, offset)
        data = self.execute_query(paginated_query, paginated_params, use_cache=False)
        
        # 获取总数
        count_query = f"SELECT COUNT(*) as total FROM ({query})"
        count_result = self.execute_query(count_query, params, use_cache=False)
        total = count_result[0]['total'] if count_result else 0
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages
            }
        }
    
    def batch_insert(self, table: str, data: List[Dict[str, Any]], 
                    batch_size: int = 100) -> int:
        """
        批量插入数据
        
        Args:
            table: 表名
            data: 数据列表
            batch_size: 每批大小
            
        Returns:
            插入的行数
        """
        if not data:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取列名
        first_row = data[0]
        columns = list(first_row.keys())
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        inserted_count = 0
        
        # 分批插入
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            values = [tuple(row[col] for col in columns) for row in batch]
            
            try:
                cursor.executemany(
                    f"INSERT OR REPLACE INTO {table} ({columns_str}) VALUES ({placeholders})",
                    values
                )
                inserted_count += len(batch)
            except Exception as e:
                print(f"批量插入失败: {e}")
                # 尝试逐条插入
                for row in batch:
                    try:
                        cursor.execute(
                            f"INSERT OR REPLACE INTO {table} ({columns_str}) VALUES ({placeholders})",
                            tuple(row[col] for col in columns)
                        )
                        inserted_count += 1
                    except Exception as e2:
                        print(f"单条插入失败: {e2}")
        
        conn.commit()
        
        # 清除相关缓存
        self._invalidate_cache_for_table(table)
        
        return inserted_count
    
    def _clean_cache(self, cache_ttl: int):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = []
        
        for key, (_, cached_time) in self.query_cache.items():
            if now - cached_time > timedelta(seconds=cache_ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.query_cache[key]
        
        # 限制缓存大小
        if len(self.query_cache) > self.max_cache_size:
            # 移除最旧的缓存
            sorted_keys = sorted(
                self.query_cache.keys(),
                key=lambda k: self.query_cache[k][1]
            )
            for key in sorted_keys[:len(self.query_cache) - self.max_cache_size]:
                del self.query_cache[key]
    
    def _invalidate_cache_for_table(self, table: str):
        """使指定表的缓存失效"""
        keys_to_remove = []
        
        for key in self.query_cache.keys():
            if table.lower() in key.lower():
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.query_cache[key]
    
    def _trim_stats(self):
        """修剪统计信息，保留最近1000条"""
        if len(self.query_stats) > 1000:
            self.query_stats = self.query_stats[-1000:]
    
    def get_query_performance_report(self) -> Dict[str, Any]:
        """获取查询性能报告"""
        if not self.query_stats:
            return {"total_queries": 0, "avg_time": 0}
        
        total_queries = len(self.query_stats)
        cached_queries = sum(1 for s in self.query_stats if s.cached)
        avg_time = sum(s.execution_time for s in self.query_stats) / total_queries
        
        # 最慢的查询
        slow_queries = sorted(self.query_stats, key=lambda s: s.execution_time, reverse=True)[:10]
        
        # 按查询类型统计
        query_types = {}
        for stat in self.query_stats:
            query_lower = stat.query.lower().strip()
            if query_lower.startswith('select'):
                qtype = 'SELECT'
            elif query_lower.startswith('insert'):
                qtype = 'INSERT'
            elif query_lower.startswith('update'):
                qtype = 'UPDATE'
            elif query_lower.startswith('delete'):
                qtype = 'DELETE'
            else:
                qtype = 'OTHER'
            
            query_types[qtype] = query_types.get(qtype, 0) + 1
        
        return {
            "total_queries": total_queries,
            "cached_queries": cached_queries,
            "cache_hit_rate": cached_queries / total_queries if total_queries > 0 else 0,
            "avg_execution_time": avg_time,
            "slow_queries": [
                {
                    "query": s.query[:100] + "..." if len(s.query) > 100 else s.query,
                    "time": s.execution_time,
                    "cached": s.cached
                }
                for s in slow_queries
            ],
            "query_types": query_types,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 分析慢查询
        slow_queries = [s for s in self.query_stats if s.execution_time > 0.1]  # 超过100ms
        
        for stat in slow_queries[:5]:
            query_lower = stat.query.lower()
            
            if 'like' in query_lower and '%' in query_lower:
                recommendations.append(f"查询 '{stat.query[:50]}...' 使用了LIKE通配符查询，考虑添加全文搜索索引")
            
            if 'order by' in query_lower and 'limit' not in query_lower:
                recommendations.append(f"查询 '{stat.query[:50]}...' 有ORDER BY但没有LIMIT，考虑添加分页")
            
            if 'join' in query_lower and stat.row_count > 1000:
                recommendations.append(f"查询 '{stat.query[:50]}...' JOIN了大表，考虑优化连接条件或添加索引")
        
        # 缓存建议
        cache_hit_rate = sum(1 for s in self.query_stats if s.cached) / len(self.query_stats) if self.query_stats else 0
        if cache_hit_rate < 0.3:
            recommendations.append(f"缓存命中率较低 ({cache_hit_rate:.1%})，考虑增加缓存大小或调整缓存策略")
        
        return recommendations
    
    def optimize_table(self, table: str):
        """优化表（VACUUM和ANALYZE）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # VACUUM 整理碎片
            cursor.execute(f"VACUUM {table}")
            
            # ANALYZE 更新统计信息
            cursor.execute(f"ANALYZE {table}")
            
            conn.commit()
            print(f"表 {table} 优化完成")
        except Exception as e:
            print(f"表优化失败: {e}")
    
    def explain_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """解释查询执行计划"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"EXPLAIN QUERY PLAN {query}", params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"解释查询失败: {e}")
            return []


# 单例模式
_optimizer_instance = None

def get_database_optimizer(db_path: str = None) -> DatabaseOptimizer:
    """获取数据库优化器实例"""
    global _optimizer_instance
    
    if db_path is None:
        # 默认数据库路径
        import os
        db_path = os.path.join(os.path.dirname(__file__), "..", "data", "quant_data.db")
    
    if _optimizer_instance is None:
        _optimizer_instance = DatabaseOptimizer(db_path)
    
    return _optimizer_instance