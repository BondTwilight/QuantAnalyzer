"""
性能优化模块 — 解决网站反应慢的问题
核心优化策略：
1. 智能缓存：多级缓存（内存 + 磁盘 + 云）
2. 懒加载：按需加载数据
3. 异步操作：非阻塞IO
4. 批量处理：减少API调用
5. 连接复用：避免重复连接
"""

import json
import time
import hashlib
import pickle
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps, lru_cache
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════
# 智能缓存系统
# ═══════════════════════════════════════════════

class SmartCache:
    """智能缓存系统 — 支持内存、磁盘、云三级缓存"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.memory_cache = {}
        self.cache_file = CACHE_DIR / f"{name}_cache.json"
        self.lock = threading.RLock()
        
    def _get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_str = f"{func_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, func_name: str, *args, **kwargs) -> Optional[Any]:
        """获取缓存数据"""
        cache_key = self._get_cache_key(func_name, *args, **kwargs)
        
        # 1. 检查内存缓存
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if datetime.now() < entry["expires"]:
                logger.debug(f"内存缓存命中: {func_name}")
                return entry["data"]
            else:
                del self.memory_cache[cache_key]
        
        # 2. 检查磁盘缓存
        if self.cache_file.exists():
            try:
                with self.lock:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                
                if cache_key in cache_data:
                    entry = cache_data[cache_key]
                    expires = datetime.fromisoformat(entry["expires"])
                    if datetime.now() < expires:
                        logger.debug(f"磁盘缓存命中: {func_name}")
                        # 存入内存缓存
                        self.memory_cache[cache_key] = {
                            "data": entry["data"],
                            "expires": expires
                        }
                        return entry["data"]
            except Exception as e:
                logger.warning(f"读取磁盘缓存失败: {e}")
        
        return None
    
    def set(self, func_name: str, data: Any, ttl_seconds: int = 3600, *args, **kwargs):
        """设置缓存数据"""
        cache_key = self._get_cache_key(func_name, *args, **kwargs)
        expires = datetime.now() + timedelta(seconds=ttl_seconds)
        
        # 1. 存入内存缓存
        self.memory_cache[cache_key] = {
            "data": data,
            "expires": expires
        }
        
        # 2. 存入磁盘缓存
        try:
            cache_data = {}
            if self.cache_file.exists():
                with self.lock:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
            
            cache_data[cache_key] = {
                "data": data,
                "expires": expires.isoformat(),
                "func_name": func_name,
                "cached_at": datetime.now().isoformat(),
                "ttl": ttl_seconds
            }
            
            # 清理过期缓存
            cache_data = {k: v for k, v in cache_data.items() 
                         if datetime.fromisoformat(v["expires"]) > datetime.now()}
            
            with self.lock:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"缓存设置: {func_name}, TTL={ttl_seconds}s")
        except Exception as e:
            logger.warning(f"写入磁盘缓存失败: {e}")
    
    def clear(self, func_name: str = None):
        """清理缓存"""
        if func_name:
            # 清理特定函数的缓存
            keys_to_remove = []
            for key in list(self.memory_cache.keys()):
                if func_name in key:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.memory_cache[key]
            
            if self.cache_file.exists():
                try:
                    with self.lock:
                        with open(self.cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                    
                    cache_data = {k: v for k, v in cache_data.items() 
                                 if func_name not in v.get("func_name", "")}
                    
                    with open(self.cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.warning(f"清理磁盘缓存失败: {e}")
        else:
            # 清理所有缓存
            self.memory_cache.clear()
            if self.cache_file.exists():
                self.cache_file.unlink()


# ═══════════════════════════════════════════════
# 缓存装饰器
# ═══════════════════════════════════════════════

def cached(ttl_seconds: int = 3600, cache_name: str = "default"):
    """缓存装饰器"""
    cache = SmartCache(cache_name)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache._get_cache_key(func.__name__, *args, **kwargs)
            
            # 尝试获取缓存
            cached_data = cache.get(func.__name__, *args, **kwargs)
            if cached_data is not None:
                return cached_data
            
            # 执行函数
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            # 缓存结果
            if result is not None:
                cache.set(func.__name__, result, ttl_seconds, *args, **kwargs)
                logger.debug(f"缓存装饰器: {func.__name__} 执行时间: {elapsed:.2f}s")
            
            return result
        return wrapper
    return decorator


# ═══════════════════════════════════════════════
# 懒加载代理
# ═══════════════════════════════════════════════

class LazyLoader:
    """懒加载代理 — 延迟初始化直到真正需要时"""
    
    def __init__(self, factory_func: Callable, *args, **kwargs):
        self._factory_func = factory_func
        self._args = args
        self._kwargs = kwargs
        self._instance = None
        self._lock = threading.RLock()
    
    def __getattr__(self, name):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    logger.debug(f"懒加载初始化: {self._factory_func.__name__}")
                    self._instance = self._factory_func(*self._args, **self._kwargs)
        return getattr(self._instance, name)
    
    def __call__(self, *args, **kwargs):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    logger.debug(f"懒加载初始化: {self._factory_func.__name__}")
                    self._instance = self._factory_func(*self._args, **self._kwargs)
        return self._instance(*args, **kwargs)


# ═══════════════════════════════════════════════
# 批量处理器
# ═══════════════════════════════════════════════

class BatchProcessor:
    """批量处理器 — 减少API调用次数"""
    
    def __init__(self, batch_size: int = 10, delay_seconds: float = 0.1):
        self.batch_size = batch_size
        self.delay_seconds = delay_seconds
        self.batch_cache = {}
        self.last_flush_time = {}
        self.lock = threading.RLock()
    
    def add_to_batch(self, batch_key: str, item_key: str, get_func: Callable):
        """添加到批量处理队列"""
        with self.lock:
            if batch_key not in self.batch_cache:
                self.batch_cache[batch_key] = {
                    "items": {},
                    "results": {},
                    "pending": set()
                }
            
            batch = self.batch_cache[batch_key]
            batch["pending"].add(item_key)
            
            # 如果达到批量大小，立即执行
            if len(batch["pending"]) >= self.batch_size:
                return self._flush_batch(batch_key, get_func)
            
            # 检查是否需要刷新（距离上次刷新时间过长）
            current_time = time.time()
            if batch_key not in self.last_flush_time:
                self.last_flush_time[batch_key] = current_time
            
            if current_time - self.last_flush_time[batch_key] > 5.0:  # 5秒自动刷新
                return self._flush_batch(batch_key, get_func)
            
            return None
    
    def _flush_batch(self, batch_key: str, get_func: Callable):
        """执行批量处理"""
        with self.lock:
            if batch_key not in self.batch_cache:
                return {}
            
            batch = self.batch_cache[batch_key]
            if not batch["pending"]:
                return batch["results"]
            
            # 获取待处理项
            pending_items = list(batch["pending"])
            batch["pending"].clear()
            self.last_flush_time[batch_key] = time.time()
            
            try:
                # 批量获取数据
                logger.debug(f"批量处理: {batch_key}, 数量: {len(pending_items)}")
                batch_results = get_func(pending_items)
                
                # 存储结果
                if isinstance(batch_results, dict):
                    batch["results"].update(batch_results)
                elif isinstance(batch_results, list) and len(batch_results) == len(pending_items):
                    for item_key, result in zip(pending_items, batch_results):
                        batch["results"][item_key] = result
                
                return batch["results"]
            except Exception as e:
                logger.error(f"批量处理失败: {e}")
                return {}
    
    def get_result(self, batch_key: str, item_key: str):
        """获取批量处理结果"""
        with self.lock:
            if batch_key in self.batch_cache:
                return self.batch_cache[batch_key]["results"].get(item_key)
        return None


# ═══════════════════════════════════════════════
# 连接池管理器
# ═══════════════════════════════════════════════

class ConnectionPool:
    """连接池管理器 — 复用数据库/API连接"""
    
    _pools = {}
    _lock = threading.RLock()
    
    @classmethod
    def get_connection(cls, pool_name: str, create_func: Callable, max_size: int = 5):
        """获取连接"""
        with cls._lock:
            if pool_name not in cls._pools:
                cls._pools[pool_name] = {
                    "connections": [],
                    "in_use": set(),
                    "create_func": create_func,
                    "max_size": max_size
                }
            
            pool = cls._pools[pool_name]
            
            # 查找可用连接
            for conn in pool["connections"]:
                if conn not in pool["in_use"]:
                    pool["in_use"].add(conn)
                    logger.debug(f"连接池复用: {pool_name}")
                    return conn
            
            # 创建新连接
            if len(pool["connections"]) < max_size:
                conn = create_func()
                pool["connections"].append(conn)
                pool["in_use"].add(conn)
                logger.debug(f"连接池新建: {pool_name}")
                return conn
            
            # 等待连接释放（简单实现）
            logger.warning(f"连接池 {pool_name} 已满，等待释放")
            time.sleep(0.1)
            return cls.get_connection(pool_name, create_func, max_size)
    
    @classmethod
    def release_connection(cls, pool_name: str, connection):
        """释放连接"""
        with cls._lock:
            if pool_name in cls._pools:
                if connection in cls._pools[pool_name]["in_use"]:
                    cls._pools[pool_name]["in_use"].remove(connection)
                    logger.debug(f"连接池释放: {pool_name}")
    
    @classmethod
    def close_all(cls):
        """关闭所有连接"""
        with cls._lock:
            for pool_name, pool in cls._pools.items():
                for conn in pool["connections"]:
                    try:
                        if hasattr(conn, 'close'):
                            conn.close()
                        elif hasattr(conn, 'logout'):
                            conn.logout()
                    except:
                        pass
                logger.info(f"关闭连接池: {pool_name}")
            cls._pools.clear()


# ═══════════════════════════════════════════════
# 性能监控器
# ═══════════════════════════════════════════════

class PerformanceMonitor:
    """性能监控器 — 跟踪函数执行时间"""
    
    _metrics = {}
    _lock = threading.RLock()
    
    @classmethod
    def track(cls, func_name: str):
        """跟踪函数执行时间"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = time.time() - start_time
                    with cls._lock:
                        if func_name not in cls._metrics:
                            cls._metrics[func_name] = {
                                "count": 0,
                                "total_time": 0,
                                "max_time": 0,
                                "min_time": float('inf')
                            }
                        
                        metrics = cls._metrics[func_name]
                        metrics["count"] += 1
                        metrics["total_time"] += elapsed
                        metrics["max_time"] = max(metrics["max_time"], elapsed)
                        metrics["min_time"] = min(metrics["min_time"], elapsed)
                        
                        if metrics["count"] % 10 == 0:
                            avg_time = metrics["total_time"] / metrics["count"]
                            logger.info(
                                f"性能监控 [{func_name}]: "
                                f"调用{metrics['count']}次, "
                                f"平均{avg_time:.3f}s, "
                                f"最慢{metrics['max_time']:.3f}s"
                            )
            return wrapper
        return decorator
    
    @classmethod
    def get_report(cls) -> Dict:
        """获取性能报告"""
        with cls._lock:
            report = {}
            for func_name, metrics in cls._metrics.items():
                if metrics["count"] > 0:
                    report[func_name] = {
                        "调用次数": metrics["count"],
                        "总耗时": f"{metrics['total_time']:.2f}s",
                        "平均耗时": f"{metrics['total_time'] / metrics['count']:.3f}s",
                        "最慢耗时": f"{metrics['max_time']:.3f}s",
                        "最快耗时": f"{metrics['min_time']:.3f}s"
                    }
            return report
    
    @classmethod
    def clear(cls):
        """清空监控数据"""
        with cls._lock:
            cls._metrics.clear()


# ═══════════════════════════════════════════════
# 优化后的数据提供器
# ═══════════════════════════════════════════════

class OptimizedDataProvider:
    """优化后的数据提供器 — 集成所有性能优化"""
    
    _cache = SmartCache("data_provider")
    _batch_processor = BatchProcessor(batch_size=20)
    
    @classmethod
    @cached(ttl_seconds=86400)  # 24小时缓存
    def get_stock_list(cls) -> pd.DataFrame:
        """获取股票列表 — 带缓存"""
        from core.multi_data_source import MultiDataSource
        return MultiDataSource.get_stock_list()
    
    @classmethod
    @cached(ttl_seconds=3600)  # 1小时缓存
    def get_stock_daily(cls, stock_code: str, days: int = 100) -> pd.DataFrame:
        """获取股票日K数据 — 带缓存"""
        from core.multi_data_source import MultiDataSource
        return MultiDataSource.get_stock_daily(stock_code, days=days)
    
    @classmethod
    def get_multiple_stocks_daily(cls, stock_codes: List[str], days: int = 100) -> Dict[str, pd.DataFrame]:
        """批量获取多只股票数据 — 减少API调用"""
        results = {}
        pending = {}
        
        # 先检查缓存
        for code in stock_codes:
            cache_key = f"get_stock_daily:{code}:{days}"
            cached = cls._cache.get("get_stock_daily", code, days=days)
            if cached is not None:
                results[code] = cached
            else:
                pending[code] = code
        
        # 批量获取剩余数据
        if pending:
            from core.multi_data_source import MultiDataSource
            
            codes_list = list(pending.values())
            logger.info(f"批量获取 {len(codes_list)} 只股票数据")
            
            for i in range(0, len(codes_list), 10):  # 每10只一批
                batch = codes_list[i:i+10]
                for code in batch:
                    try:
                        df = MultiDataSource.get_stock_daily(code, days=days)
                        if df is not None and not df.empty:
                            results[code] = df
                            # 缓存结果
                            cls._cache.set("get_stock_daily", df, 3600, code, days=days)
                    except Exception as e:
                        logger.warning(f"获取股票 {code} 数据失败: {e}")
                time.sleep(0.5)  # 避免请求过快
        
        return results


# ═══════════════════════════════════════════════
# 优化初始化
# ═══════════════════════════════════════════════

def optimize_quant_brain():
    """优化QuantBrain初始化"""
    from core.quant_brain import QuantBrain
    
    class OptimizedQuantBrain(QuantBrain):
        """优化版的QuantBrain — 懒加载组件"""
        
        def __init__(self):
            # 使用懒加载代理延迟初始化
            from core.quant_brain import SignalGenerator, StrategyLearner, PortfolioTracker, DataProvider
            
            self._signal_gen = LazyLoader(SignalGenerator)
            self._learner = LazyLoader(StrategyLearner)
            self._portfolio = LazyLoader(PortfolioTracker)
            self._data = LazyLoader(DataProvider)
            
            # 标记为已初始化
            self._initialized = True
        
        @property
        def signal_gen(self):
            return self._signal_gen
        
        @property
        def learner(self):
            return self._learner
        
        @property
        def portfolio(self):
            return self._portfolio
        
        @property
        def data(self):
            return self._data
    
    return OptimizedQuantBrain


# 全局性能优化实例
cache_system = SmartCache("global")
performance_monitor = PerformanceMonitor()
connection_pool = ConnectionPool()
optimized_data_provider = OptimizedDataProvider()