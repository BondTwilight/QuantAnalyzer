"""
数据层 — 统一数据获取 + SQLite 存储
优先使用 MultiDataSource（AkShare为主，BaoStock备用）
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH, DATA_DIR, STOCK_POOL, BENCHMARK, DEFAULT_PERIOD

logger = logging.getLogger(__name__)


class DataFetcher:
    """数据获取器 — 委托给 MultiDataSource"""

    def __init__(self):
        self._use_multidata = False
        try:
            from core.multi_data_source import MultiDataSource
            self._mds = MultiDataSource
            self._use_multidata = True
            logger.info("DataFetcher: 使用 MultiDataSource (AkShare主)")
        except ImportError:
            logger.warning("DataFetcher: MultiDataSource不可用，使用BaoStock")

    def _bs_login(self):
        """BaoStock登录（仅作为备用）"""
        if not self._use_multidata:
            try:
                import baostock as bs
                if not hasattr(self, '_bs_logged_in') or not self._bs_logged_in:
                    lg = bs.login()
                    if lg.error_code != "0":
                        raise ConnectionError(f"BaoStock login failed: {lg.error_msg}")
                    self._bs_logged_in = True
                    logger.info("BaoStock logged in")
            except Exception as e:
                raise ConnectionError(f"BaoStock不可用: {e}")

    def get_stock_daily(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取股票日线数据"""
        code = ts_code.split(".")[0] if "." in ts_code else ts_code

        # 优先 MultiDataSource
        if self._use_multidata:
            df = self._mds.get_stock_daily(code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df["ts_code"] = ts_code
                logger.info(f"Fetched {len(df)} rows for {ts_code} via MultiDataSource")
                return df

        # 备用：BaoStock
        try:
            self._bs_login()
            import baostock as bs
            bs_code = code
            if code.startswith("6"):
                bs_code = f"sh.{code}"
            else:
                bs_code = f"sz.{code}"

            _start = start_date or (datetime.now() - timedelta(days=DEFAULT_PERIOD)).strftime("%Y-%m-%d")
            _end = end_date or datetime.now().strftime("%Y-%m-%d")

            rs = bs.query_history_k_data_plus(
                bs_code, "date,open,high,low,close,volume",
                start_date=_start, end_date=_end,
                frequency="d", adjustflag="2"
            )
            rows = []
            if rs is None:
                return pd.DataFrame()
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return pd.DataFrame()

            data = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            for col in ["open", "high", "low", "close", "volume"]:
                data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
            data["date"] = pd.to_datetime(data["date"])
            data["ts_code"] = ts_code
            data = data.dropna(subset=["close"])
            data = data[data["close"] > 0]
            logger.info(f"Fetched {len(data)} rows for {ts_code} via BaoStock")
            return data
        except Exception as e:
            logger.error(f"获取 {ts_code} 日线数据失败: {e}")
            return pd.DataFrame()

    def get_index_daily(self, index_code: str = "000300", start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指数日线数据"""
        code = index_code.replace("sh.", "").replace("sz.", "")

        if self._use_multidata:
            df = self._mds.get_index_daily(code, days=DEFAULT_PERIOD)
            if df is not None and not df.empty:
                logger.info(f"Fetched {len(df)} rows for index {index_code}")
                return df

        # 备用BaoStock
        try:
            self._bs_login()
            import baostock as bs
            bs_code = f"sh.{code}"
            _start = start_date or (datetime.now() - timedelta(days=DEFAULT_PERIOD)).strftime("%Y-%m-%d")
            _end = end_date or datetime.now().strftime("%Y-%m-%d")

            rs = bs.query_history_k_data_plus(
                bs_code, "date,open,high,low,close,volume",
                start_date=_start, end_date=_end,
                frequency="d", adjustflag="3"
            )
            rows = []
            if rs is None:
                return pd.DataFrame()
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return pd.DataFrame()
            data = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            for col in ["open", "high", "low", "close", "volume"]:
                data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
            data["date"] = pd.to_datetime(data["date"])
            data = data[data["close"] > 0]
            return data
        except Exception as e:
            logger.error(f"获取指数 {index_code} 数据失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_stock_list() -> pd.DataFrame:
        """获取A股列表"""
        try:
            from core.multi_data_source import MultiDataSource
            df = MultiDataSource.get_stock_list()
            if df is not None and not df.empty:
                return df
        except:
            pass

        try:
            import baostock as bs
            bs.login()
            rs = bs.query_stock_basic()
            rows = []
            if rs is None:
                bs.logout()
                return pd.DataFrame()
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            bs.logout()
            if rows:
                return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
        return pd.DataFrame()

    def get_sector_index(self, sector_name: str) -> pd.DataFrame:
        """获取行业板块指数 — 用AkShare"""
        try:
            from core.multi_data_source import AkShareSource
            df = AkShareSource.get_stock_daily(
                {"银行": "601398", "白酒": "000858", "医药": "000538",
                 "消费": "000858", "科技": "300750", "新能源": "300750"}.get(sector_name, "000001"),
                days=DEFAULT_PERIOD
            )
            return df
        except:
            return pd.DataFrame()

    def close(self):
        if hasattr(self, '_bs_logged_in') and self._bs_logged_in:
            try:
                import baostock as bs
                bs.logout()
            except:
                pass


class Database:
    """SQLite 数据库操作（优化版）"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._ensure_dir()
        
        # 导入数据库优化器
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.database_optimizer import get_database_optimizer
        self.optimizer = get_database_optimizer(str(self.db_path))
        
        self._init_tables()

    def _ensure_dir(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_tables(self):
        conn = self.optimizer.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                stock_code TEXT,
                start_date TEXT,
                end_date TEXT,
                initial_cash REAL,
                final_value REAL,
                total_return REAL,
                annual_return REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                sortino_ratio REAL,
                calmar_ratio REAL,
                win_rate REAL,
                profit_loss_ratio REAL,
                total_trades INTEGER,
                trade_frequency REAL,
                beta REAL,
                volatility REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                date TEXT NOT NULL,
                portfolio_value REAL,
                benchmark_value REAL,
                drawdown REAL,
                cash REAL,
                position REAL,
                UNIQUE(strategy_name, date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                date TEXT NOT NULL,
                action TEXT,
                stock_code TEXT,
                price REAL,
                quantity INTEGER,
                commission REAL,
                reason TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                report_date TEXT NOT NULL,
                provider TEXT,
                analysis_type TEXT,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL UNIQUE,
                params TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    def save_backtest_result(self, result: dict):
        """保存回测结果（批量插入优化）"""
        data = [{
            "strategy_name": result.get("strategy_name"),
            "stock_code": result.get("stock_code"),
            "start_date": result.get("start_date"),
            "end_date": result.get("end_date"),
            "initial_cash": result.get("initial_cash"),
            "final_value": result.get("final_value"),
            "total_return": result.get("total_return"),
            "annual_return": result.get("annual_return"),
            "max_drawdown": result.get("max_drawdown"),
            "sharpe_ratio": result.get("sharpe_ratio"),
            "sortino_ratio": result.get("sortino_ratio"),
            "calmar_ratio": result.get("calmar_ratio"),
            "win_rate": result.get("win_rate"),
            "profit_loss_ratio": result.get("profit_loss_ratio"),
            "total_trades": result.get("total_trades"),
            "trade_frequency": result.get("trade_frequency"),
            "beta": result.get("beta"),
            "volatility": result.get("volatility")
        }]
        
        inserted = self.optimizer.batch_insert("backtest_results", data)
        return inserted

    def save_daily_values(self, strategy_name: str, df: pd.DataFrame):
        """保存每日净值（批量插入优化）"""
        if df.empty:
            return
        
        data = []
        for idx, row in df.iterrows():
            data.append({
                "strategy_name": strategy_name,
                "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                "portfolio_value": row.get("portfolio_value", 0),
                "benchmark_value": row.get("benchmark_value", 0),
                "drawdown": row.get("drawdown", 0),
                "cash": row.get("cash", 0),
                "position": row.get("position", 0)
            })
        
        self.optimizer.batch_insert("daily_values", data, batch_size=50)

    def save_trades(self, strategy_name: str, trades: list):
        """保存交易记录（批量插入优化）"""
        if not trades:
            return
        
        data = []
        for t in trades:
            data.append({
                "strategy_name": strategy_name,
                "date": t.get("date"),
                "action": t.get("action"),
                "stock_code": t.get("stock_code"),
                "price": t.get("price"),
                "quantity": t.get("quantity"),
                "commission": t.get("commission"),
                "reason": t.get("reason")
            })
        
        self.optimizer.batch_insert("trade_records", data, batch_size=50)

    def get_backtest_results(self, strategy_name=None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取回测结果（分页优化）"""
        if strategy_name:
            query = "SELECT * FROM backtest_results WHERE strategy_name = ?"
            params = (strategy_name,)
        else:
            query = "SELECT * FROM backtest_results"
            params = ()
        
        result = self.optimizer.execute_paginated_query(
            query, params, page=page, page_size=page_size, 
            order_by="created_at DESC"
        )
        
        return result

    def get_daily_values(self, strategy_name: str, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """获取每日净值（分页优化）"""
        query = "SELECT * FROM daily_values WHERE strategy_name = ?"
        params = (strategy_name,)
        
        result = self.optimizer.execute_paginated_query(
            query, params, page=page, page_size=page_size,
            order_by="date DESC"
        )
        
        # 转换为DataFrame格式（兼容旧代码）
        if result["data"]:
            df = pd.DataFrame(result["data"])
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            result["data"] = df
        
        return result

    def get_latest_results(self, limit: int = 10) -> pd.DataFrame:
        """获取最新回测结果（缓存优化）"""
        query = """
            SELECT * FROM backtest_results
            WHERE created_at IN (
                SELECT MAX(created_at) FROM backtest_results GROUP BY strategy_name
            )
            ORDER BY annual_return DESC
            LIMIT ?
        """
        
        results = self.optimizer.execute_query(query, (limit,), use_cache=True, cache_ttl=60)
        
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()

    def save_ai_report(self, strategy_name: str, report_date: str, provider: str,
                       analysis_type: str, content: str):
        """保存AI报告（批量插入优化）"""
        data = [{
            "strategy_name": strategy_name,
            "report_date": report_date,
            "provider": provider,
            "analysis_type": analysis_type,
            "content": content
        }]
        
        self.optimizer.batch_insert("ai_reports", data)

    def get_query_performance_report(self) -> Dict[str, Any]:
        """获取查询性能报告"""
        return self.optimizer.get_query_performance_report()

    def optimize_database(self):
        """优化数据库"""
        tables = ["backtest_results", "daily_values", "trade_records", "ai_reports", "strategy_params"]
        for table in tables:
            try:
                self.optimizer.optimize_table(table)
            except:
                pass

    def close(self):
        """关闭数据库连接"""
        self.optimizer.close_connections()


# ── 全局数据库实例 ──
db = Database()
