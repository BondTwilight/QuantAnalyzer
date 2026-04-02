"""
数据层 — BaoStock 数据获取 + SQLite 存储
BaoStock 免费A股数据，无需API Key，数据稳定
"""
import sqlite3
import pandas as pd
import numpy as np
import baostock as bs
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH, DATA_DIR, STOCK_POOL, BENCHMARK, DEFAULT_PERIOD

logger = logging.getLogger(__name__)

# BaoStock 代码格式: sh.600519, sz.000001
def _to_bs_code(ts_code: str) -> str:
    """000001.SZ -> sz.000001"""
    parts = ts_code.split(".")
    if len(parts) == 2:
        return f"{parts[1].lower()}.{parts[0]}"
    return ts_code.lower()

def _to_ts_code(bs_code: str) -> str:
    """sh.600519 -> 600519.SH"""
    parts = bs_code.split(".")
    if len(parts) == 2:
        return f"{parts[1]}.{parts[0].upper()}"
    return bs_code.upper()


class DataFetcher:
    """BaoStock 数据获取器"""

    def __init__(self):
        self._logged_in = False

    def _ensure_login(self):
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code != "0":
                raise ConnectionError(f"BaoStock login failed: {lg.error_msg}")
            self._logged_in = True
            logger.info("BaoStock logged in")

    def _logout(self):
        if self._logged_in:
            bs.logout()
            self._logged_in = False

    def get_stock_daily(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取股票日线数据"""
        try:
            self._ensure_login()
            bs_code = _to_bs_code(ts_code)

            df = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=start_date or (datetime.now() - timedelta(days=DEFAULT_PERIOD)).strftime("%Y-%m-%d"),
                end_date=end_date or datetime.now().strftime("%Y-%m-%d"),
                frequency="d",
                adjustflag="2"  # 前复权
            )

            rows = []
            while df.error_code == "0" and df.next():
                rows.append(df.get_row_data())

            if not rows:
                logger.warning(f"No data for {ts_code}")
                return pd.DataFrame()

            data = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            # 转换数据类型
            for col in ["open", "high", "low", "close", "volume"]:
                data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
            data["date"] = pd.to_datetime(data["date"])
            data["ts_code"] = ts_code
            data = data.set_index("date")
            data = data.dropna(subset=["close"])
            data = data[data["close"] > 0]  # 过滤无效数据

            logger.info(f"Fetched {len(data)} rows for {ts_code}")
            return data

        except Exception as e:
            logger.error(f"获取 {ts_code} 日线数据失败: {e}")
            return pd.DataFrame()

    def get_index_daily(self, index_code: str = "000300", start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指数日线数据 (沪深300等)"""
        try:
            self._ensure_login()
            # BaoStock 指数代码: sh.000300
            bs_code = f"sh.{index_code}"

            df = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=start_date or (datetime.now() - timedelta(days=DEFAULT_PERIOD)).strftime("%Y-%m-%d"),
                end_date=end_date or datetime.now().strftime("%Y-%m-%d"),
                frequency="d",
                adjustflag="3"  # 不复权
            )

            rows = []
            while df.error_code == "0" and df.next():
                rows.append(df.get_row_data())

            if not rows:
                return pd.DataFrame()

            data = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            for col in ["open", "high", "low", "close", "volume"]:
                data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
            data["date"] = pd.to_datetime(data["date"])
            data = data.set_index("date")
            data = data[data["close"] > 0]

            logger.info(f"Fetched {len(data)} rows for index {index_code}")
            return data

        except Exception as e:
            logger.error(f"获取指数 {index_code} 数据失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_stock_list() -> pd.DataFrame:
        """获取A股实时行情 (通过baostock)"""
        try:
            bs.login()
            rs = bs.query_stock_basic()
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            bs.logout()
            if rows:
                df = pd.DataFrame(rows)
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_sector_index(self, sector_name: str) -> pd.DataFrame:
        """获取行业板块指数 — 用代表性ETF替代"""
        sector_etf = {
            "银行": "sh.512800",  # 银行ETF
            "白酒": "sz.159928",  # 白酒ETF
            "医药": "sz.159938",  # 医药ETF
            "消费": "sz.159928",  # 白酒ETF代消费
            "科技": "sz.159915",  # 创业板ETF
            "新能源": "sz.159824",  # 新能源车ETF
        }
        bs_code = sector_etf.get(sector_name)
        if not bs_code:
            return pd.DataFrame()

        try:
            self._ensure_login()
            df = bs.query_history_k_data_plus(
                bs_code, "date,open,high,low,close,volume",
                start_date=(datetime.now() - timedelta(days=DEFAULT_PERIOD)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                frequency="d", adjustflag="2"
            )
            rows = []
            while df.error_code == "0" and df.next():
                rows.append(df.get_row_data())
            if not rows:
                return pd.DataFrame()
            data = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            for col in ["open", "high", "low", "close", "volume"]:
                data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
            data["date"] = pd.to_datetime(data["date"])
            data = data.set_index("date")
            return data[data["close"] > 0]
        except Exception as e:
            logger.error(f"获取行业 {sector_name} 数据失败: {e}")
            return pd.DataFrame()

    def close(self):
        self._logout()


class Database:
    """SQLite 数据库操作"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = None
        self._ensure_dir()
        self._init_tables()

    def _ensure_dir(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def _init_tables(self):
        conn = self._get_conn()
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
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO backtest_results (
                strategy_name, stock_code, start_date, end_date,
                initial_cash, final_value, total_return, annual_return,
                max_drawdown, sharpe_ratio, sortino_ratio, calmar_ratio,
                win_rate, profit_loss_ratio, total_trades, trade_frequency,
                beta, volatility
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.get("strategy_name"), result.get("stock_code"),
            result.get("start_date"), result.get("end_date"),
            result.get("initial_cash"), result.get("final_value"),
            result.get("total_return"), result.get("annual_return"),
            result.get("max_drawdown"), result.get("sharpe_ratio"),
            result.get("sortino_ratio"), result.get("calmar_ratio"),
            result.get("win_rate"), result.get("profit_loss_ratio"),
            result.get("total_trades"), result.get("trade_frequency"),
            result.get("beta"), result.get("volatility"),
        ))
        conn.commit()
        return cursor.lastrowid

    def save_daily_values(self, strategy_name: str, df: pd.DataFrame):
        conn = self._get_conn()
        for idx, row in df.iterrows():
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_values (strategy_name, date, portfolio_value, benchmark_value, drawdown, cash, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_name,
                    idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                    row.get("portfolio_value", 0),
                    row.get("benchmark_value", 0),
                    row.get("drawdown", 0),
                    row.get("cash", 0),
                    row.get("position", 0),
                ))
            except Exception as e:
                logger.warning(f"保存每日净值失败 {idx}: {e}")
        conn.commit()

    def save_trades(self, strategy_name: str, trades: list):
        conn = self._get_conn()
        for t in trades:
            conn.execute("""
                INSERT INTO trade_records (strategy_name, date, action, stock_code, price, quantity, commission, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strategy_name, t.get("date"), t.get("action"),
                t.get("stock_code"), t.get("price"), t.get("quantity"),
                t.get("commission"), t.get("reason"),
            ))
        conn.commit()

    def get_backtest_results(self, strategy_name=None) -> pd.DataFrame:
        conn = self._get_conn()
        if strategy_name:
            df = pd.read_sql(
                "SELECT * FROM backtest_results WHERE strategy_name = ? ORDER BY created_at DESC",
                conn, params=(strategy_name,)
            )
        else:
            df = pd.read_sql("SELECT * FROM backtest_results ORDER BY created_at DESC", conn)
        return df

    def get_daily_values(self, strategy_name: str) -> pd.DataFrame:
        conn = self._get_conn()
        df = pd.read_sql(
            "SELECT * FROM daily_values WHERE strategy_name = ? ORDER BY date",
            conn, params=(strategy_name,)
        )
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        return df

    def get_latest_results(self) -> pd.DataFrame:
        conn = self._get_conn()
        df = pd.read_sql("""
            SELECT * FROM backtest_results
            WHERE created_at IN (
                SELECT MAX(created_at) FROM backtest_results GROUP BY strategy_name
            )
            ORDER BY annual_return DESC
        """, conn)
        return df

    def save_ai_report(self, strategy_name: str, report_date: str, provider: str,
                       analysis_type: str, content: str):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO ai_reports (strategy_name, report_date, provider, analysis_type, content)
            VALUES (?, ?, ?, ?, ?)
        """, (strategy_name, report_date, provider, analysis_type, content))
        conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


# ── 全局数据库实例 ──
db = Database()
