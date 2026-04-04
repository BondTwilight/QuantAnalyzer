"""
多数据源提供器 — AkShare为主，BaoStock备用（本地环境）
AkShare 基于HTTP API，在Docker/HuggingFace等云环境稳定可用
BaoStock 基于TCP长连接，仅在有网络直连的本地环境作为备用
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import os

logger = logging.getLogger(__name__)

# 检测运行环境
def _is_cloud_env() -> bool:
    """检测是否在云/Docker环境（HuggingFace Spaces等）"""
    return os.environ.get("SPACE_ID") or os.environ.get("DOCKER_CONTAINER")

# 清除代理的上下文管理器（东方财富API在代理下容易失败）
import contextlib

@contextlib.contextmanager
def _no_proxy():
    """临时清除HTTP代理（包括环境变量和requests会话）"""
    saved = {}
    for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    # 设置 NO_PROXY 为 * 绕过所有代理
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"
    try:
        yield
    finally:
        os.environ.update(saved)
        for key in ["NO_PROXY", "no_proxy"]:
            os.environ.pop(key, None)


# ═══════════════════════════════════════════════════════════
# AkShare 主数据源
# ═══════════════════════════════════════════════════════════

class AkShareSource:
    """AkShare 数据源 — HTTP API，云环境友好"""

    @staticmethod
    def get_stock_list() -> pd.DataFrame:
        """获取全部A股列表（实时行情）"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                rename_map = {"代码": "code", "名称": "name"}
                df = df.rename(columns=rename_map)
                result = df[["code", "name"]].copy()
                result["type"] = "stock"
                logger.info(f"AkShare: 获取到 {len(result)} 只A股")
                return result
        except Exception as e:
            logger.warning(f"AkShare获取股票列表失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_stock_daily(stock_code: str, start_date: str = None,
                       end_date: str = None, days: int = None) -> pd.DataFrame:
        """获取股票日K数据"""
        try:
            import akshare as ak
            code = stock_code.replace(".SZ", "").replace(".SH", "").replace("sh.", "").replace("sz.", "")

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                lookback = days or 365
                start_date = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")

            with _no_proxy():
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date.replace("-", ""),
                    end_date=end_date.replace("-", ""),
                    adjust="qfq"
                )

            if df is None or df.empty:
                return pd.DataFrame()

            rename_map = {
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount", "换手率": "turnover",
            }
            df = df.rename(columns=rename_map)

            if "date" not in df.columns:
                return pd.DataFrame()

            df["date"] = pd.to_datetime(df["date"])
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "amount" not in df.columns:
                df["amount"] = 0.0
            else:
                df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
            if "turnover" not in df.columns:
                df["turnover"] = 0.0
            else:
                df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce").fillna(0)

            df = df[["date", "open", "high", "low", "close", "volume", "amount", "turnover"]]
            df = df.dropna(subset=["close"])
            df = df[df["close"] > 0]
            df = df.sort_values("date").reset_index(drop=True)
            return df

        except Exception as e:
            logger.error(f"AkShare get_stock_daily failed for {stock_code}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_stock_info(stock_code: str) -> Dict:
        """获取股票基本信息"""
        try:
            import akshare as ak
            code = stock_code.replace(".SZ", "").replace(".SH", "").replace("sh.", "").replace("sz.", "")
            with _no_proxy():
                df = ak.stock_individual_info_em(symbol=code)
            if df is not None and not df.empty:
                info_map = {}
                for _, row in df.iterrows():
                    info_map[row.iloc[0]] = row.iloc[1]
                return {
                    "code": stock_code,
                    "name": info_map.get("股票简称", stock_code),
                    "industry": info_map.get("行业", ""),
                    "market": info_map.get("上市时间", ""),
                }
        except Exception as e:
            logger.debug(f"AkShare stock_info failed: {e}")

        # 备用：从实时行情获取名称
        try:
            import akshare as ak
            code = stock_code.replace(".SZ", "").replace(".SH", "").replace("sh.", "").replace("sz.", "")
            with _no_proxy():
                df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                match = df[df["代码"] == code]
                if not match.empty:
                    return {"code": stock_code, "name": str(match.iloc[0].get("名称", stock_code))}
        except:
            pass

        return {"code": stock_code, "name": stock_code}

    @staticmethod
    def get_index_daily(index_code: str = "000300", days: int = 365) -> pd.DataFrame:
        """获取指数日K数据
        
        Args:
            index_code: 指数代码，纯数字格式如 "000001"(上证), "399001"(深证), "000300"(沪深300)
            days: 回溯天数
        """
        try:
            import akshare as ak
            code = index_code.replace("sh.", "").replace("sz.", "")

            # 新浪源需要带交易所前缀: sh000001, sz399001, sh000300
            # 规则: 上证(0xxxxx, 9xxxxx)用sh, 深证(3xxxxx)用sz
            # 特殊: 沪深300(000300)是sh，中证500(000905)也是sh
            if code.startswith("3"):
                sina_symbols = [f"sz{code}"]
            else:
                sina_symbols = [f"sh{code}"]

            # 方案1: stock_zh_index_daily（新浪源，稳定）
            for symbol in sina_symbols:
                try:
                    df = ak.stock_zh_index_daily(symbol=symbol)
                    if df is not None and not df.empty:
                        df["date"] = pd.to_datetime(df["date"])
                        for col in ["open", "high", "low", "close", "volume"]:
                            if col in df.columns:
                                df[col] = pd.to_numeric(df[col], errors="coerce")

                        start_dt = datetime.now() - timedelta(days=days)
                        df = df[df["date"] >= start_dt]
                        df = df.dropna(subset=["close"])
                        df = df[df["close"] > 0]
                        df = df.sort_values("date").reset_index(drop=True)
                        logger.info(f"Sina index: {symbol} got {len(df)} rows")
                        return df
                except Exception as e:
                    logger.debug(f"Sina index {symbol} failed: {e}")
                    continue

            # 方案2: stock_zh_index_daily_em（东方财富，需直连）
            try:
                with _no_proxy():
                    df = ak.stock_zh_index_daily_em(symbol=code)
                if df is not None and not df.empty:
                    rename_map = {
                        "日期": "date", "开盘": "open", "收盘": "close",
                        "最高": "high", "最低": "low", "成交量": "volume",
                    }
                    df = df.rename(columns=rename_map)
                    df["date"] = pd.to_datetime(df["date"])
                    for col in ["open", "high", "low", "close", "volume"]:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors="coerce")

                    start_dt = datetime.now() - timedelta(days=days)
                    df = df[df["date"] >= start_dt]
                    df = df.dropna(subset=["close"])
                    df = df[df["close"] > 0]
                    df = df.sort_values("date").reset_index(drop=True)
                    logger.info(f"EM index: {code} got {len(df)} rows")
                    return df
            except Exception as e:
                logger.debug(f"EM index source failed: {e}")

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"AkShare get_index_daily failed for {index_code}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_realtime_quotes() -> pd.DataFrame:
        """获取全部A股实时行情"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                rename_map = {
                    "代码": "code", "名称": "name", "最新价": "price",
                    "涨跌幅": "pct_change", "涨跌额": "change", "成交量": "volume",
                    "成交额": "amount", "振幅": "amplitude", "最高": "high",
                    "最低": "low", "今开": "open", "昨收": "prev_close",
                    "换手率": "turnover", "市盈率-动态": "pe", "市净率": "pb",
                }
                df = df.rename(columns=rename_map)
                for col in ["price", "pct_change", "change", "volume", "amount"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                return df
        except Exception as e:
            logger.error(f"AkShare realtime_quotes failed: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_limit_up_stocks(date_str: str = None) -> pd.DataFrame:
        """获取涨停股列表"""
        try:
            import akshare as ak
            with _no_proxy():
                if date_str:
                    df = ak.stock_zt_pool_em(date=date_str.replace("-", ""))
                else:
                    df = ak.stock_zt_pool_em(date=datetime.now().strftime("%Y%m%d"))
            return df
        except Exception as e:
            logger.warning(f"AkShare涨停股失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_limit_down_stocks(date_str: str = None) -> pd.DataFrame:
        """获取跌停股列表"""
        try:
            import akshare as ak
            with _no_proxy():
                if date_str:
                    df = ak.stock_zt_pool_dtgc_em(date=date_str.replace("-", ""))
                else:
                    df = ak.stock_zt_pool_dtgc_em(date=datetime.now().strftime("%Y%m%d"))
            return df
        except Exception as e:
            logger.warning(f"AkShare跌停股失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_top_list(date_str: str = None) -> pd.DataFrame:
        """获取龙虎榜"""
        try:
            import akshare as ak
            with _no_proxy():
                if date_str:
                    d = date_str.replace("-", "")
                    df = ak.stock_lhb_detail_em(start_date=d, end_date=d)
                else:
                    today = datetime.now().strftime("%Y%m%d")
                    df = ak.stock_lhb_detail_em(start_date=today, end_date=today)
            return df
        except Exception as e:
            logger.warning(f"AkShare龙虎榜失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_north_flow(days: int = 30) -> pd.DataFrame:
        """获取北向资金流向"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.stock_hsgt_north_net_flow_in_em(symbol="北向资金")
            return df
        except Exception as e:
            logger.warning(f"AkShare北向资金失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_sector_list() -> pd.DataFrame:
        """获取行业板块列表"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.stock_board_industry_name_em()
            return df
        except Exception as e:
            logger.warning(f"AkShare行业板块失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_concept_list() -> pd.DataFrame:
        """获取概念板块列表"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.stock_board_concept_name_em()
            return df
        except Exception as e:
            logger.warning(f"AkShare概念板块失败: {e}")
            return pd.DataFrame()


# ═══════════════════════════════════════════════════════════
# BaoStock 备用数据源（仅本地环境）
# ═══════════════════════════════════════════════════════════

class BaoStockSource:
    """BaoStock 数据源 — TCP连接，仅本地环境备用"""

    _logged_in = False

    @classmethod
    def login(cls):
        if not cls._logged_in:
            try:
                import baostock as bs
                lg = bs.login()
                if lg.error_code != '0':
                    logger.warning(f"BaoStock login failed: {lg.error_msg}")
                    return False
                cls._logged_in = True
            except Exception as e:
                logger.warning(f"BaoStock login error: {e}")
                return False
        return True

    @classmethod
    def logout(cls):
        if cls._logged_in:
            try:
                import baostock as bs
                bs.logout()
            except:
                pass
            cls._logged_in = False

    @classmethod
    def get_stock_daily(cls, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """BaoStock获取日K"""
        try:
            import baostock as bs
            if not cls.login():
                return None
            code = stock_code.replace(".SZ", "").replace(".SH", "")
            if code.startswith("6"):
                code = f"sh.{code}"
            elif code.startswith(("0", "3")):
                code = f"sz.{code}"
            else:
                code = f"sz.{code}"

            rs = bs.query_history_k_data_plus(
                code, "date,open,high,low,close,volume,amount,turn",
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2"
            )
            rows = []
            while rs.next():
                row = rs.get_row_data()
                if row and row[0] and row[4] != '0':
                    try:
                        rows.append({
                            "date": row[0], "open": float(row[1]), "high": float(row[2]),
                            "low": float(row[3]), "close": float(row[4]),
                            "volume": float(row[5]),
                            "amount": float(row[6]) if row[6] else 0,
                            "turnover": float(row[7]) if row[7] else 0,
                        })
                    except (ValueError, IndexError):
                        continue
            if not rows:
                return None
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"BaoStock daily failed for {stock_code}: {e}")
            return None

    @classmethod
    def get_stock_list(cls) -> pd.DataFrame:
        """BaoStock获取全部A股列表"""
        try:
            import baostock as bs
            if not cls.login():
                return pd.DataFrame()
            rs = bs.query_stock_basic()
            rows = []
            while rs.next():
                row = rs.get_row_data()
                if row and row[5] == "1":
                    code = row[0].replace("sh.", "").replace("sz.", "")
                    rows.append({"code": code, "name": row[1], "type": "stock"})
            if rows:
                return pd.DataFrame(rows)
        except Exception as e:
            logger.warning(f"BaoStock stock list failed: {e}")
        return pd.DataFrame()


# ═══════════════════════════════════════════════════════════
# 多数据源统一接口
# ═══════════════════════════════════════════════════════════

class MultiDataSource:
    """多数据源统一接口 — AkShare优先（云环境友好），BaoStock备用（本地）"""

    _name_cache: Dict[str, Dict] = {}

    # ─── 股票列表 ───
    @staticmethod
    def get_stock_list() -> pd.DataFrame:
        """获取全部A股列表"""
        # 1. AkShare（主）
        df = AkShareSource.get_stock_list()
        if df is not None and not df.empty:
            return df

        # 2. BaoStock（备用，仅本地）
        if not _is_cloud_env():
            df = BaoStockSource.get_stock_list()
            if df is not None and not df.empty:
                return df

        logger.warning("所有数据源获取股票列表失败")
        return pd.DataFrame()

    # ─── 股票日K ───
    @staticmethod
    def get_stock_daily(stock_code: str, start_date: str = None,
                       end_date: str = None, days: int = None) -> pd.DataFrame:
        """获取股票日K数据"""
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            lookback = days or 365
            start_date = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")

        # 1. AkShare（主）
        df = AkShareSource.get_stock_daily(stock_code, start_date, end_date, days)
        if df is not None and not df.empty:
            return df

        # 2. BaoStock（备用）
        if not _is_cloud_env():
            df = BaoStockSource.get_stock_daily(stock_code, start_date, end_date)
            if df is not None and not df.empty:
                return df

        return pd.DataFrame()

    # ─── 股票信息 ───
    @staticmethod
    def get_stock_info(stock_code: str) -> Dict:
        """获取股票基本信息（带缓存）"""
        if stock_code in MultiDataSource._name_cache:
            return MultiDataSource._name_cache[stock_code]

        info = AkShareSource.get_stock_info(stock_code)
        MultiDataSource._name_cache[stock_code] = info
        return info

    # ─── 指数日K ───
    @staticmethod
    def get_index_daily(index_code: str = "000300", days: int = 365) -> pd.DataFrame:
        """获取指数日K数据
        
        Args:
            index_code: 纯数字格式 "000001"(上证), "399001"(深证), "000300"(沪深300)
                       兼容旧格式 "sh.000300", "sz.399001"
        """
        # 标准化代码：去掉前缀
        code = index_code.replace("sh.", "").replace("sz.", "")

        # 1. AkShare（主）
        df = AkShareSource.get_index_daily(code, days)
        if df is not None and not df.empty:
            return df

        # 2. BaoStock（备用，仅本地）
        if not _is_cloud_env():
            try:
                import baostock as bs
                if not BaoStockSource.login():
                    return pd.DataFrame()
                # BaoStock指数代码: 上证用sh, 深证用sz
                if code.startswith("3"):
                    bs_code = f"sz.{code}"
                else:
                    bs_code = f"sh.{code}"
                end = datetime.now().strftime("%Y-%m-%d")
                start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                rs = bs.query_history_k_data_plus(
                    bs_code, "date,open,high,low,close,volume",
                    start_date=start, end_date=end,
                    frequency="d", adjustflag="2"
                )
                rows = []
                while rs.next():
                    row = rs.get_row_data()
                    if row and row[4] and row[4] != '0':
                        rows.append({
                            "date": row[0], "open": float(row[1]), "high": float(row[2]),
                            "low": float(row[3]), "close": float(row[4]), "volume": float(row[5]),
                        })
                if rows:
                    df = pd.DataFrame(rows)
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date").reset_index(drop=True)
                    return df
            except:
                pass

        return pd.DataFrame()

    # ─── 实时行情 ───
    @staticmethod
    def get_realtime_quotes() -> pd.DataFrame:
        """获取全部A股实时行情"""
        return AkShareSource.get_realtime_quotes()

    # ─── 涨停/跌停 ───
    @staticmethod
    def get_limit_up_stocks(date_str: str = None) -> pd.DataFrame:
        return AkShareSource.get_limit_up_stocks(date_str)

    @staticmethod
    def get_limit_down_stocks(date_str: str = None) -> pd.DataFrame:
        return AkShareSource.get_limit_down_stocks(date_str)

    # ─── 龙虎榜 ───
    @staticmethod
    def get_top_list(date_str: str = None) -> pd.DataFrame:
        return AkShareSource.get_top_list(date_str)

    # ─── 北向资金 ───
    @staticmethod
    def get_north_flow(days: int = 30) -> pd.DataFrame:
        return AkShareSource.get_north_flow(days)

    # ─── 板块 ───
    @staticmethod
    def get_sector_list() -> pd.DataFrame:
        return AkShareSource.get_sector_list()

    @staticmethod
    def get_concept_list() -> pd.DataFrame:
        return AkShareSource.get_concept_list()

    # ═══════════════════════════════════════════════
    # 技术指标计算
    # ═══════════════════════════════════════════════
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if df.empty:
            return df

        close = df["close"].copy()
        high = df["high"].copy()
        low = df["low"].copy()
        volume = df["volume"].copy()

        # 均线
        for period in [5, 10, 20, 60, 120]:
            df[f"ma_{period}"] = close.rolling(window=period).mean()

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["dif"] = ema12 - ema26
        df["dea"] = df["dif"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = 2 * (df["dif"] - df["dea"])

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df["rsi"] = 100 - 100 / (1 + rs)

        # 布林带
        df["boll_mid"] = close.rolling(window=20).mean()
        boll_std = close.rolling(window=20).std()
        df["boll_upper"] = df["boll_mid"] + 2 * boll_std
        df["boll_lower"] = df["boll_mid"] - 2 * boll_std

        # ATR
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=14).mean()

        # 成交量MA
        df["vol_ma_5"] = volume.rolling(window=5).mean()
        df["vol_ma_20"] = volume.rolling(window=20).mean()

        # 涨跌幅
        df["pct_change"] = close.pct_change() * 100

        # KDJ
        low_min = low.rolling(window=9).min()
        high_max = high.rolling(window=9).max()
        rsv = (close - low_min) / (high_max - low_min + 1e-10) * 100
        df["k"] = rsv.ewm(com=2, adjust=False).mean()
        df["d"] = df["k"].ewm(com=2, adjust=False).mean()
        df["j"] = 3 * df["k"] - 2 * df["d"]

        return df


# 兼容旧代码的别名
_MDS = MultiDataSource
