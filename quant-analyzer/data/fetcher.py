"""
数据层 — AKShare 数据获取 + SQLite 存储
"""
import sqlite3
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH, DATA_DIR, STOCK_POOL, BENCHMARK, DEFAULT_PERIOD

logger = logging.getLogger(__name__)


class DataFetcher:
    """AKShare 数据获取器"""

    @staticmethod
    def get_stock_daily(ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票日线数据
        ts_code: 000001.SZ 格式
        """
        try:
            # akshare 接口使用 6位代码 格式
            symbol = ts_code.split(".")[0]
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date or (datetime.now() - timedelta(days=DEFAULT_PERIOD)).strftime("%Y%m%d"),
                end_date=end_date or datetime.now().strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )
            if df is not None and not df.empty:
                df.columns = ["date", "open", "close", "high", "low", "volume", "turnover", "amplitude", "pct_change", "change", "turnover_rate"]
                df["date"] = pd.to_datetime(df["date"])
                df["ts_code"] = ts_code
                df = df.set_index("date")
            return df
        except Exception as e:
            logger.error(f"获取 {ts_code} 日线数据失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_stock_list() -> pd.DataFrame:
        """获取A股股票列表"""
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                return df[["代码", "名称", "最新价", "涨跌幅", "总市值", "流通市值"]]
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_index_daily(index_code: str = "000300", start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指数日线数据 (沪深300等)"""
        try:
            df = ak.index_zh_a_hist(
                symbol=index_code,
                period="daily",
                start_date=start_date or (datetime.now() - timedelta(days=DEFAULT_PERIOD)).strftime("%Y%m%d"),
                end_date=end_date or datetime.now().strftime("%Y%m%d"),
            )
            if df is not None and not df.empty:
                df.columns = ["date", "open", "close", "high", "low", "volume", "turnover"]
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            return df
        except Exception as e:
            logger.error(f"获取指数 {index_code} 数据失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_sector_index(sector_name: str) -> pd.DataFrame:
        """获取行业板块指数"""
        try:
            df = ak.stock_board_industry_hist_em(
                symbol=sector_name,
                period="daily",
                start_date=(datetime.now() - timedelta(days=DEFAULT_PERIOD)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq"
            )
            if df is not None and not df.empty:
                df.columns = ["date", "open", "close", "high", "low", "volume", "turnover", "amplitude", "pct_change", "change", "turnover_rate"]
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            return df
        except Exception as e:
            logger.error(f"获取行业 {sector_name} 数据失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_financial_indicator(ts_code: str) -> pd.DataFrame:
        """获取财务指标 (ROE, PE, PB等)"""
        try:
            symbol = ts_code.split(".")[0]
            df = ak.stock_financial_abstract_ths(symbol=symbol)
            if df is not None and not df.empty:
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取 {ts_code} 财务指标失败: {e}")
            return pd.DataFrame()


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

        # 回测结果表
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

        # 每日净值表
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

        # 交易记录表
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

        # AI分析报告表
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

        # 策略参数表
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
        logger.info("数据库初始化完成")

    def save_backtest_result(self, result: dict):
        """保存回测结果"""
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
        """保存每日净值数据"""
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
        """保存交易记录"""
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
        """获取回测结果"""
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
        """获取策略每日净值"""
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
        """获取每个策略的最新回测结果"""
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
        """保存AI分析报告"""
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
