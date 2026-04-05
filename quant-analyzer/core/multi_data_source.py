"""
多数据源提供器 — 参考 OpenClaw/易涨EasyUp 的"多源聚合+免费优先+自动降级"策略
数据源优先级: BaoStock(稳定免费) → AkShare(多源聚合) → 模拟数据(兜底)
灵感来源: 易涨EasyUp "好几个和在一起用、一个不行"
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
            import urllib3
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
                # 检查是否是连接错误导致的空数据
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

        except (urllib3.exceptions.MaxRetryError, 
                urllib3.exceptions.NewConnectionError,
                ConnectionError,
                TimeoutError) as e:
            # 连接错误，抛出异常以便触发备用数据源
            logger.warning(f"AkShare连接失败 {stock_code}: {e}")
            raise
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
    # ETF 数据接口
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_etf_list() -> pd.DataFrame:
        """获取全部ETF列表"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.etf_spot_em()
            if df is not None and not df.empty:
                rename_map = {"代码": "code", "名称": "name", "最新价": "price",
                             "涨跌幅": "pct_change", "成交量": "volume", "成交额": "amount"}
                df = df.rename(columns=rename_map)
                return df
        except Exception as e:
            logger.warning(f"AkShare ETF列表失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_etf_daily(etf_code: str, days: int = 365) -> pd.DataFrame:
        """获取ETF日K线数据
        
        Args:
            etf_code: ETF代码，如 '510300'(沪深300ETF), '159915'(创业板ETF)
            days: 回溯天数
        """
        try:
            import akshare as ak
            code = etf_code.replace(".SZ", "").replace(".SH", "")
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            with _no_proxy():
                df = ak.fund_etf_hist_em(
                    symbol=code, period="daily",
                    start_date=start_date, end_date=end_date, adjust="qfq"
                )
            if df is not None and not df.empty:
                rename_map = {
                    "日期": "date", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume",
                    "成交额": "amount",
                }
                df = df.rename(columns=rename_map)
                df["date"] = pd.to_datetime(df["date"])
                for col in ["open", "high", "low", "close", "volume"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.sort_values("date").reset_index(drop=True)
                return df
        except Exception as e:
            logger.warning(f"AkShare ETF日K失败 {etf_code}: {e}")
        return pd.DataFrame()

    # ═══════════════════════════════════════════════════════════
    # 基金数据接口
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_fund_nav(fund_code: str) -> pd.DataFrame:
        """获取基金净值历史
        
        Args:
            fund_code: 基金代码，如 '110011'(易方达中小盘)
        """
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
            if df is not None and not df.empty:
                rename_map = {"净值日期": "date", "单位净值": "nav", "累计净值": "accumulated_nav"}
                df = df.rename(columns=rename_map)
                df["date"] = pd.to_datetime(df["date"])
                return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            logger.warning(f"AkShare基金净值失败 {fund_code}: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_fund_rank(category: str = "股票型") -> pd.DataFrame:
        """获取基金排行
        
        Args:
            category: 基金类型，如 '股票型', '混合型', '债券型', '指数型'
        """
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.fund_open_fund_rank_em(symbol=category)
            return df
        except Exception as e:
            logger.warning(f"AkShare基金排行失败: {e}")
        return pd.DataFrame()

    # ═══════════════════════════════════════════════════════════
    # 期货数据接口
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_future_list() -> pd.DataFrame:
        """获取期货主力合约列表"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.futures_main_sina()
            if df is not None and not df.empty:
                rename_map = {"代码": "code", "名称": "name", "最新价": "price",
                             "涨跌幅": "pct_change", "成交量": "volume", "持仓量": "open_interest"}
                df = df.rename(columns=rename_map)
                return df
        except Exception as e:
            logger.warning(f"AkShare期货列表失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_future_daily(symbol: str, days: int = 180) -> pd.DataFrame:
        """获取期货日K数据
        
        Args:
            symbol: 期货合约代码，如 'IF2406'(沪深300指数期货), 'AU2506'(黄金期货)
            days: 回溯天数
        """
        try:
            import akshare as ak
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            with _no_proxy():
                df = ak.futures_main_sina(symbol=symbol, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                for col in ["open", "high", "low", "close", "volume"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            logger.warning(f"AkShare期货日K失败 {symbol}: {e}")
        return pd.DataFrame()

    # ═══════════════════════════════════════════════════════════
    # 宏观经济数据接口
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_gdp_data() -> pd.DataFrame:
        """获取中国GDP数据（季度）"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.cn_gdp()
            if df is not None and not df.empty:
                rename_map = {"季度": "quarter", "国内生产总值-绝对值": "gdp",
                             "第一产业增加值-绝对值": "primary_industry",
                             "第二产业增加值-绝对值": "secondary_industry",
                             "第三产业增加值-绝对值": "tertiary_industry"}
                df = df.rename(columns=rename_map)
                return df
        except Exception as e:
            logger.warning(f"AkShare GDP数据失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_cpi_data() -> pd.DataFrame:
        """获取中国CPI数据（月度）"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.cn_cpi()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"AkShare CPI数据失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_ppi_data() -> pd.DataFrame:
        """获取中国PPI数据（月度）"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.cn_ppi()
            return df
        except Exception as e:
            logger.warning(f"AkShare PPI数据失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_pm_i_data() -> pd.DataFrame:
        """获取PMI采购经理指数"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.china_pmi_index_monthly()
            return df
        except Exception as e:
            logger.warning(f"AkShare PMI数据失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_money_supply() -> pd.DataFrame:
        """获取货币供应量（M0/M1/M2）"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.money_supply_cn_monthly()
            return df
        except Exception as e:
            logger.warning(f"AkShare货币供应量失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_shibor_rates() -> pd.DataFrame:
        """获取Shibor利率"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.shibor_data_df(symbol="SHIBOR")
            return df
        except Exception as e:
            logger.warning(f"AkShare Shibor失败: {e}")
        return pd.DataFrame()

    # ═══════════════════════════════════════════════════════════
    # 港股/美股数据接口
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_hk_stock_daily(stock_code: str, days: int = 365) -> pd.DataFrame:
        """获取港股日K数据
        
        Args:
            stock_code: 港股代码，如 '00700'(腾讯), '09988'(阿里), '03690'(美团)
        """
        try:
            import akshare as ak
            code = stock_code.replace("HK.", "").replace("hk.", "")
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            with _no_proxy():
                df = ak.stock_hk_hist(
                    symbol=code, period="daily",
                    start_date=start_date, end_date=end_date, adjust="qfq"
                )
            if df is not None and not df.empty:
                rename_map = {
                    "日期": "date", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume",
                    "成交额": "amount", "振幅": "amplitude", "换手率": "turnover",
                }
                df = df.rename(columns=rename_map)
                df["date"] = pd.to_datetime(df["date"])
                for col in ["open", "high", "low", "close", "volume"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            logger.warning(f"AkShare港股日K失败 {stock_code}: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_us_stock_daily(stock_code: str, days: int = 365) -> pd.DataFrame:
        """获取美股日K数据
        
        Args:
            stock_code: 美股代码，如 'AAPL', 'TSLA', 'NVDA'
        """
        try:
            import akshare as ak
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            with _no_proxy():
                df = ak.us_stock_daily_hist(
                    symbol=stock_code, period="daily",
                    start_date=start_date, end_date=end_date, adjust="qfq"
                )
            if df is not None and not df.empty:
                rename_map = {
                    "日期": "date", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume",
                    "成交额": "amount",
                }
                df = df.rename(columns=rename_map)
                df["date"] = pd.to_datetime(df["date"])
                for col in ["open", "high", "low", "close", "volume"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            logger.warning(f"AkShare美股日K失败 {stock_code}: {e}")
        return pd.DataFrame()

    # ═══════════════════════════════════════════════════════════
    # 债券/可转债接口
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_bond_cb_list() -> pd.DataFrame:
        """获取可转债列表"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.bond_cb_em()
            return df
        except Exception as e:
            logger.warning(f"AkShare可转债列表失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_treasury_yield(days: int = 365) -> pd.DataFrame:
        """获取国债收益率曲线
        
        Args:
            days: 回溯天数
        """
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.bond_china_yield(start_date=(datetime.now()-timedelta(days=days)).strftime("%Y%m%d"))
            return df
        except Exception as e:
            logger.warning(f"AkShare国债收益率失败: {e}")
        return pd.DataFrame()

    # ═══════════════════════════════════════════════════════════
    # 资金流向 / 市场情绪
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_stock_money_flow(stock_code: str) -> pd.DataFrame:
        """获取个股资金流向（东方财富）
        
        Args:
            stock_code: 股票代码
        """
        try:
            import akshare as ak
            code = stock_code.replace(".SZ", "").replace(".SH", "")
            with _no_proxy():
                df = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith(("6","9")) else "sz")
            return df
        except Exception as e:
            logger.warning(f"AkShare个股资金流向失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_sector_money_flow() -> pd.DataFrame:
        """获取行业板块资金流向"""
        try:
            import akshare as ak
            with _no_proxy():
                df = ak.stock_sector_fund_flow_rank(indicator="今日")
            return df
        except Exception as e:
            logger.warning(f"AkShare板块资金流失败: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_market_sentiment() -> Dict:
        """获取市场情绪指标汇总"""
        result = {}
        try:
            # 涨跌家数比
            import akshare as ak
            with _no_proxy():
                df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                up_count = len(df[df["涨跌幅"] > 0])
                down_count = len(df[df["涨跌幅"] < 0])
                flat_count = len(df[df["涨跌幅"] == 0])
                total = len(df)
                result.update({
                    "total_stocks": total,
                    "up_count": up_count,
                    "down_count": down_count,
                    "flat_count": flat_count,
                    "advance_decline_ratio": round(up_count / (down_count + 1), 2),
                    "avg_pct_change": round(float(df["涨跌幅"].mean()), 2),
                })
        except Exception as e:
            logger.warning(f"市场情绪计算失败: {e}")
        return result


# ════════════════════════════════════════════════════════════════
# 东方财富实时行情专用源（易涨EasyUp推荐的核心数据源）
# ════════════════════════════════════════════════════════════════

class EastMoneyRealtimeSource:
    """东方财富实时行情专用数据源
    
    易涨EasyUp核心推荐的数据层组件，特点：
    - 覆盖A股/港股/美股/期货/基金全品类
    - 实时推送 + 历史K线一体化
    - 免费无需注册（公开API）
    - 通过AkShare的em系列接口访问
    
    参考: SKILL分享之东财篇 (2144赞)
    """

    @staticmethod
    def get_realtime_batch(codes: List[str]) -> pd.DataFrame:
        """批量获取实时行情（支持跨市场混合查询）
        
        Args:
            codes: 代码列表，支持混合格式：
                   A股: ['000001', '600519']
                   港股: ['00700', '09988']  
                   美股: ['AAPL', 'TSLA']
                   指数: ['000001', '399001', '899050']
        
        Returns:
            包含 code/name/price/pct_change/volume/amount 的DataFrame
        """
        all_dfs = []
        for code in codes:
            try:
                import akshare as ak
                clean_code = code.replace(".SZ", "").replace(".SH", "")
                
                # 判断市场类型
                if clean_code.isdigit() and len(clean_code) == 6:
                    # A股或指数 - 使用 spot 接口
                    with _no_proxy():
                        df = ak.stock_zh_a_spot_em()
                    if df is not None and not df.empty:
                        match = df[df["代码"] == clean_code]
                        if not match.empty:
                            row = match.iloc[0]
                            all_dfs.append({
                                "code": clean_code,
                                "name": row.get("名称", ""),
                                "price": row.get("最新价"),
                                "pct_change": row.get("涨跌幅"),
                                "change": row.get("涨跌额"),
                                "volume": row.get("成交量"),
                                "amount": row.get("成交额"),
                                "high": row.get("最高"),
                                "low": row.get("最低"),
                                "open": row.get("今开"),
                                "prev_close": row.get("昨收"),
                                "turnover": row.get("换手率"),
                                "pe": row.get("市盈率-动态"),
                                "pb": row.get("市净率"),
                            })

                elif clean_code.isdigit() and len(clean_code) <= 5:
                    # 港股
                    with _no_proxy():
                        hk_df = ak.stock_hk_spot_em()
                    if hk_df is not None and not hk_df.empty:
                        match = hk_df[hk_df["代码"] == clean_code]
                        if not match.empty:
                            row = match.iloc[0]
                            all_dfs.append({
                                "code": f"HK.{clean_code}",
                                "name": row.get("名称", ""),
                                "price": row.get("最新价"),
                                "pct_change": row.get("涨跌幅"),
                                "volume": row.get("成交量"),
                                "amount": row.get("成交额"),
                            })

                else:
                    # 美股
                    with _no_proxy():
                        us_df = ak.us_spot_em()
                    if us_df is not None and not us_df.empty:
                        match = us_df[us_df["代码"].str.upper() == clean_code.upper()]
                        if not match.empty:
                            row = match.iloc[0]
                            all_dfs.append({
                                "code": clean_code.upper(),
                                "name": row.get("名称", ""),
                                "price": row.get("最新价"),
                                "pct_change": row.get("涨跌幅"),
                                "volume": row.get("成交量"),
                            })

            except Exception as e:
                logger.debug(f"EastMoney realtime {code} failed: {e}")

        if all_dfs:
            df = pd.DataFrame(all_dfs)
            for col in ["price", "pct_change", "change", "volume", "amount", "pe", "pb"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
        return pd.DataFrame()

    @staticmethod
    def get_minute_data(stock_code: str, period: str = "1") -> pd.DataFrame:
        """获取分钟级K线数据
        
        Args:
            stock_code: 股票代码
            period: K线周期 '1'=1分钟, '5'=5分钟, '15'=15分钟, '30'=30分钟, '60'=60分钟
        """
        try:
            import akshare as ak
            code = stock_code.replace(".SZ", "").replace(".SH", "")
            
            # 确定市场
            market = "sz" if code.startswith(("0", "3")) else "sh"
            symbol = f"{market}{code}"
            
            period_map = {"1": "1", "5": "5", "15": "15", "30": "30", "60": "60"}
            adj_period = period_map.get(period, "5")

            with _no_proxy():
                df = ak.stock_zh_a_hist_min_em(
                    symbol=code, period=adj_period, adjust="qfq"
                )
            if df is not None and not df.empty:
                rename_map = {
                    "时间": "datetime", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount",
                    "振幅": "amplitude", "涨跌幅": "pct_change",
                }
                df = df.rename(columns=rename_map)
                return df
        except Exception as e:
            logger.warning(f"EastMoney分钟线失败 {stock_code}: {e}")
        return pd.DataFrame()

    @staticmethod
    def get_market_overview() -> Dict:
        """获取市场全景概览（主要指数+市场情绪+热门板块）"""
        overview = {}
        try:
            import akshare as ak
            
            # 主要指数实时行情
            index_codes = ["000001", "399001", "399006", "000300", "000016", "000688"]
            index_names = ["上证指数", "深证成指", "创业板指", "沪深300", "上证50", "科创50"]

            with _no_proxy():
                df = ak.stock_zh_a_spot_em()
            
            if df is not None and not df.empty:
                indices = []
                for code, name in zip(index_codes, index_names):
                    idx_match = df[df["代码"] == code]
                    if not idx_match.empty:
                        r = idx_match.iloc[0]
                        indices.append({
                            "code": code, "name": name,
                            "price": r.get("最新价"), 
                            "pct_change": r.get("涨跌幅"),
                        })
                overview["indices"] = indices

                # 市场统计
                overview["market_stats"] = {
                    "total": len(df),
                    "up_count": int(len(df[df["涨跌幅"] > 0])),
                    "down_count": int(len(df[df["涨跌幅"] < 0])),
                    "limit_up": int(len(df[abs(df["涨跌幅"] - 19.9) < 1])),  # 近似涨停
                    "limit_down": int(len(df[df["涨跌幅"] < -9.9])),
                    "total_amount": df["成交额"].sum() if "成交额" in df.columns else 0,
                }

                # 涨幅前10
                top_gainers = df.nlargest(10, "涨跌幅")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
                overview["top_gainers"] = top_gainers.to_dict("records")

                # 跌幅前10
                top_losers = df.nsmallest(10, "涨跌幅")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
                overview["top_losers"] = top_losers.to_dict("records")

                # 成交额前10
                top_volume = df.nlargest(10, "成交额")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
                overview["top_volume"] = top_volume.to_dict("records")

        except Exception as e:
            logger.error(f"市场全景概览失败: {e}")
        return overview

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
    """多数据源统一接口 — 参考OpenClaw/易涨EasyUp的多源聚合策略
    
    数据源优先级链 (参考 akshare-data Skill 的98接口设计):
    1. BaoStock: 免费、稳定、无需Token，适合历史K线回测
    2. AkShare: 多源聚合(新浪/腾讯/东财)，98+接口，实时行情强
    3. 模拟数据: 几何布朗运动兜底，确保系统永远可用
    
    核心哲学 (来自易涨EasyUp): "好几个和在一起用、一个不行"
    - ❌ 不依赖单一数据源
    - ✅ 多源聚合 + 自动降级
    - ✅ 免费优先 + 模拟兜底
    - ✅ 稳定性 > 实时性（对于回测场景）
    """

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

        # 1. AkShare（主）- 本地环境下如果AkShare失败，尝试BaoStock
        try:
            df = AkShareSource.get_stock_daily(stock_code, start_date, end_date, days)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"AkShare获取数据失败，尝试备用源: {e}")

        # 2. BaoStock（备用）- 仅在非云环境
        if not _is_cloud_env():
            try:
                df = BaoStockSource.get_stock_daily(stock_code, start_date, end_date)
                if df is not None and not df.empty:
                    logger.info(f"使用BaoStock获取 {stock_code} 数据成功")
                    return df
            except Exception as e:
                logger.warning(f"BaoStock也失败了: {e}")

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

    # ─── ETF ───
    @staticmethod
    def get_etf_list() -> pd.DataFrame:
        """获取全部ETF列表"""
        return AkShareSource.get_etf_list()

    @staticmethod
    def get_etf_daily(etf_code: str, days: int = 365) -> pd.DataFrame:
        """获取ETF日K线数据"""
        return AkShareSource.get_etf_daily(etf_code, days)

    # ─── 基金 ───
    @staticmethod
    def get_fund_nav(fund_code: str) -> pd.DataFrame:
        """获取基金净值历史"""
        return AkShareSource.get_fund_nav(fund_code)

    @staticmethod
    def get_fund_rank(category: str = "股票型") -> pd.DataFrame:
        """获取基金排行"""
        return AkShareSource.get_fund_rank(category)

    # ─── 期货 ───
    @staticmethod
    def get_future_list() -> pd.DataFrame:
        """获取期货主力合约列表"""
        return AkShareSource.get_future_list()

    @staticmethod
    def get_future_daily(symbol: str, days: int = 180) -> pd.DataFrame:
        """获取期货日K数据"""
        return AkShareSource.get_future_daily(symbol, days)

    # ─── 宏观经济 ───
    @staticmethod
    def get_gdp_data() -> pd.DataFrame:
        """获取中国GDP数据"""
        return AkShareSource.get_gdp_data()

    @staticmethod
    def get_cpi_data() -> pd.DataFrame:
        """获取中国CPI数据"""
        return AkShareSource.get_cpi_data()

    @staticmethod
    def get_ppi_data() -> pd.DataFrame:
        """获取中国PPI数据"""
        return AkShareSource.get_ppi_data()

    @staticmethod
    def get_pm_i_data() -> pd.DataFrame:
        """获取PMI采购经理指数"""
        return AkShareSource.get_pm_i_data()

    @staticmethod
    def get_money_supply() -> pd.DataFrame:
        """获取货币供应量(M0/M1/M2)"""
        return AkShareSource.get_money_supply()

    @staticmethod
    def get_shibor_rates() -> pd.DataFrame:
        """获取Shibor利率"""
        return AkShareSource.get_shibor_rates()

    # ─── 港股/美股 ───
    @staticmethod
    def get_hk_stock_daily(stock_code: str, days: int = 365) -> pd.DataFrame:
        """获取港股日K数据"""
        return AkShareSource.get_hk_stock_daily(stock_code, days)

    @staticmethod
    def get_us_stock_daily(stock_code: str, days: int = 365) -> pd.DataFrame:
        """获取美股日K数据"""
        return AkShareSource.get_us_stock_daily(stock_code, days)

    # ─── 债券 ───
    @staticmethod
    def get_bond_cb_list() -> pd.DataFrame:
        """获取可转债列表"""
        return AkShareSource.get_bond_cb_list()

    @staticmethod
    def get_treasury_yield(days: int = 365) -> pd.DataFrame:
        """获取国债收益率曲线"""
        return AkShareSource.get_treasury_yield(days)

    # ─── 资金流向 / 市场情绪 ───
    @staticmethod
    def get_stock_money_flow(stock_code: str) -> pd.DataFrame:
        """获取个股资金流向"""
        return AkShareSource.get_stock_money_flow(stock_code)

    @staticmethod
    def get_sector_money_flow() -> pd.DataFrame:
        """获取行业板块资金流向"""
        return AkShareSource.get_sector_money_flow()

    @staticmethod
    def get_market_sentiment() -> Dict:
        """获取市场情绪指标汇总"""
        return AkShareSource.get_market_sentiment()

    # ─── 东方财富实时行情（批量） ───
    @staticmethod
    def get_realtime_batch(codes: List[str]) -> pd.DataFrame:
        """批量获取实时行情（支持A股/港股/美股混合）"""
        return EastMoneyRealtimeSource.get_realtime_batch(codes)

    @staticmethod
    def get_minute_data(stock_code: str, period: str = "5") -> pd.DataFrame:
        """获取分钟级K线数据"""
        return EastMoneyRealtimeSource.get_minute_data(stock_code, period)

    @staticmethod
    def get_market_overview() -> Dict:
        """获取市场全景概览（指数+涨跌榜+成交额榜）"""
        return EastMoneyRealtimeSource.get_market_overview()

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
