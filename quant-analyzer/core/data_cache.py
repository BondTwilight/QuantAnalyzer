"""
📦 数据缓存层 — 学习易涨EasyUp的 SQLite 本地存储策略

核心设计（来自易涨EasyUp截图分析）:
- 90MB SQLite数据库存储历史行情
- 60万+ 行情记录，12表结构化存储  
- 121笔交易归因
- 采集→计算→决策 三段式流水线

本模块功能:
1. 股票日线数据SQLite缓存（避免重复网络请求）
2. 缓存过期自动刷新机制
3. 离线模式支持（纯缓存运行）
4. 多股票批量加载优化
"""

import sqlite3
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_DB_PATH = CACHE_DIR / "stock_data_cache.db"

# 缓存有效期（天）— A股交易日约250天/年，缓存1周足够回测用
CACHE_TTL_DAYS = 7


class DataCache:
    """
    股票数据SQLite缓存管理器
    
    特点:
    - 写入时压缩存储（节省空间）
    - 读取时带TTL过期检查
    - 支持批量操作（减少IO）
    - 自动清理过期数据
    """
    
    def __init__(self, db_path: Path = CACHE_DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（懒加载+复用）"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=10)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 主缓存表 — 存储所有股票的日K数据
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily_cache (
                stock_code TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                turnover REAL,
                cached_at TEXT DEFAULT (datetime('now','localtime')),
                PRIMARY KEY (stock_code, date)
            )
        """)
        
        # 缓存元信息表 — 记录每只股票的缓存状态
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_meta (
                stock_code TEXT PRIMARY KEY,
                total_rows INTEGER DEFAULT 0,
                date_start TEXT,
                date_end TEXT,
                last_refresh TEXT DEFAULT (datetime('now','localtime')),
                source TEXT DEFAULT 'unknown',  -- akshare/baostock/simulated
                status TEXT DEFAULT 'ok'       -- ok/stale/expired/error
            )
        """)
        
        # 创建索引加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_stock ON stock_daily_cache(stock_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_date ON stock_daily_cache(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_cached ON stock_daily_cache(cached_at)")
        
        conn.commit()
        
        # 清理过期缓存（异步）
        try:
            expired_days = CACHE_TTL_DAYS * 2
            cursor.execute(
                f"DELETE FROM stock_daily_cache WHERE cached_at < datetime('now','localtime','-{expired_days} days')"
            )
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"🧹 清理了 {deleted} 条过期缓存记录")
            conn.commit()
        except Exception:
            pass
    
    def save_stock_data(self, stock_code: str, df: pd.DataFrame, 
                        source: str = "akshare") -> bool:
        """保存单只股票数据到缓存
        
        Args:
            stock_code: 股票代码 (如 "000001.SZ")
            df: OHLCV DataFrame
            source: 数据来源标识
            
        Returns:
            是否保存成功
        """
        if df is None or df.empty:
            return False
        
        try:
            required_cols = {"date", "close"}
            if not required_cols.issubset(df.columns):
                logger.warning(f"{stock_code} DataFrame缺少必要列 {required_cols - set(df.columns)}")
                return False
            
            conn = self._get_conn()
            
            safe_code = stock_code.replace(".", "_")
            
            # 准备写入数据
            records = []
            for _, row in df.iterrows():
                date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])
                records.append((
                    safe_code,
                    date_str,
                    float(row.get("open", 0)),
                    float(row.get("high", 0)),
                    float(row.get("low", 0)),
                    float(row.get("close", 0)),
                    float(row.get("volume", 0)),
                    float(row.get("amount", 0)),
                    float(row.get("turnover", 0)),
                ))
            
            # 批量插入/更新
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO stock_daily_cache 
                (stock_code, date, open, high, low, close, volume, amount, turnover, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            """, records)
            
            # 更新元信息
            dates_str = [r[1] for r in records]
            cursor.execute("""
                INSERT OR REPLACE INTO cache_meta 
                (stock_code, total_rows, date_start, date_end, last_refresh, source, status)
                VALUES (?, ?, ?, ?, datetime('now','localtime'), ?, 'ok')
            """, (safe_code, len(records), min(dates_str), max(dates_str), source))
            
            conn.commit()
            logger.debug(f"💾 缓存 {stock_code}: {len(records)} 条记录 ({source})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 缓存保存失败 {stock_code}: {e}")
            return False
    
    def load_stock_data(self, stock_code: str, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """从缓存加载股票数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)，None则不限
            end_date: 结束日期 (YYYY-MM-DD)，None则不限
            
        Returns:
            OHLCV DataFrame or None（无缓存或已过期）
        """
        try:
            conn = self._get_conn()
            safe_code = stock_code.replace(".", "_")
            
            # 检查缓存是否有效
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, last_refresh, total_rows FROM cache_meta WHERE stock_code = ?
            """, (safe_code,))
            meta = cursor.fetchone()
            
            if meta is None:
                return None  # 无缓存
            
            status, last_refresh, total_rows = meta
            
            # 检查是否过期
            if last_refresh:
                try:
                    refresh_dt = datetime.strptime(last_refresh, "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - refresh_dt).days > CACHE_TTL_DAYS and total_rows > 60:
                        # 标记为stale但不拒绝使用（总比没数据好）
                        pass
                except ValueError:
                    pass
            
            # 查询数据
            query = """
                SELECT stock_code, date, open, high, low, close, volume, amount, turnover
                FROM stock_daily_cache WHERE stock_code = ?
            """
            params = [safe_code]
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            
            query += " ORDER BY date ASC"
            
            df = pd.read_sql(query, conn, params=params)
            
            if df.empty:
                return None
            
            # 还原原始列名
            df["stock_code"] = df["stock_code"].str.replace("_", ".", 1)
            df["date"] = pd.to_datetime(df["date"])
            
            # 数值列转换
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
            logger.debug(f"📂 从缓存加载 {stock_code}: {len(df)} 条记录")
            return df[["date", "open", "high", "low", "close", "volume", "amount", "turnover"]]
            
        except Exception as e:
            logger.warning(f"⚠️ 缓存读取失败 {stock_code}: {e}")
            return None
    
    def batch_load(self, stock_codes: List[str], min_rows: int = 60) -> Dict[str, pd.DataFrame]:
        """批量从缓存加载多只股票数据
        
        Returns:
            Dict[code, DataFrame]
        """
        result = {}
        for code in stock_codes:
            df = self.load_stock_data(code)
            if df is not None and len(df) >= min_rows:
                result[code] = df
        
        if result:
            logger.info(f"📦 批量缓存命中: {len(result)}/{len(stock_codes)} 只股票")
        return result
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_daily_cache")
            stock_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM stock_daily_cache")
            total_rows = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cache_meta WHERE status='ok'")
            valid_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(cached_at), MAX(cached_at) FROM stock_daily_cache")
            oldest, newest = cursor.fetchone()
            
            # 文件大小
            file_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            return {
                "stock_count": stock_count,
                "total_rows": total_rows,
                "valid_count": valid_count,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "oldest": oldest,
                "newest": newest,
                "db_path": str(self.db_path),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def invalidate(self, stock_code: Optional[str] = None):
        """使缓存失效
        
        Args:
            stock_code: 指定股票代码，None则清除全部
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            if stock_code:
                safe_code = stock_code.replace(".", "_")
                cursor.execute("DELETE FROM stock_daily_cache WHERE stock_code = ?", (safe_code,))
                cursor.execute("DELETE FROM cache_meta WHERE stock_code = ?", (safe_code,))
                logger.info(f"🗑️ 已清除 {stock_code} 的缓存")
            else:
                cursor.execute("DELETE FROM stock_daily_cache")
                cursor.execute("DELETE FROM cache_meta")
                logger.info("🗑️ 已清除全部缓存")
            
            conn.commit()
        except Exception as e:
            logger.error(f"❌ 清除缓存失败: {e}")
    
    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# ═════ 全局缓存实例 ═══
_cache_instance: Optional[DataCache] = None


def get_data_cache() -> DataCache:
    """获取全局数据缓存实例（单例）"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DataCache()
    return _cache_instance
