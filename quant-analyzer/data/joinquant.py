"""
聚宽 JoinQuant 数据源集成
提供高质量A股数据，补充BaoStock

注意: 聚宽API需要注册获取token, 免费账户有使用限制
注册地址: https://www.joinquant.com/

使用示例:
    from data.joinquant import JoinQuantFetcher
    
    fetcher = JoinQuantFetcher()
    # 需要设置聚宽token
    fetcher.set_token("your_joinquant_token")
    
    # 获取股票数据
    df = fetcher.get_security_bars("000001.XSHE", count=100)
"""

import os
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 尝试导入聚宽SDK (需要: pip install jqdatasdk)
JOINQUANT_AVAILABLE = False
try:
    import jqdatasdk as jq
    JOINQUANT_AVAILABLE = True
except ImportError:
    jq = None


class JoinQuantFetcher:
    """
    聚宽数据获取器
    
    功能:
    - 股票/期货/期权日线数据
    - 财务因子数据
    - 指数成分股
    - 融资融券数据
    """
    
    def __init__(self, token: Optional[str] = None):
        self.connected = False
        self._auth(token)
    
    def _auth(self, token: Optional[str] = None):
        """认证聚宽API"""
        if not JOINQUANT_AVAILABLE:
            print("聚宽SDK未安装, 请运行: pip install jqdatasdk")
            return False
        
        try:
            # 优先使用传入的token,其次使用环境变量
            jq_token = token or os.getenv("JOINQUANT_TOKEN") or os.getenv("JQ_DATA_TOKEN")
            jq_password = os.getenv("JOINQUANT_PASSWORD") or os.getenv("JQ_DATA_PASSWORD")
            
            if jq_token:
                # 标准认证
                if jq_password:
                    jq.auth(jq_token, jq_password)
                else:
                    # 旧版认证格式
                    jq.auth(jq_token, jq_password or "")
            else:
                # 尝试使用环境变量认证
                jq.auth(os.getenv("JQ_ACCOUNT", ""), os.getenv("JQ_PASSWORD", ""))
            
            self.connected = True
            print("聚宽数据源连接成功")
            return True
        except Exception as e:
            print(f"聚宽认证失败: {e}")
            self.connected = False
            return False
    
    def set_token(self, token: str, password: str = ""):
        """设置认证token"""
        os.environ["JOINQUANT_TOKEN"] = token
        if password:
            os.environ["JOINQUANT_PASSWORD"] = password
        return self._auth(token)
    
    def get_security_bars(self, code: str, count: int = 100, 
                         end_date: Optional[str] = None,
                         fields: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        获取证券 bars 数据
        
        Args:
            code: 证券代码, 如 "000001.XSHE" (平安银行), "600519.XSHG" (茅台)
            count: 获取数量
            end_date: 结束日期
            fields: 返回字段列表
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, money
        """
        if not self.connected:
            return None
        
        try:
            # 转换代码格式
            if "." not in code:
                if code.startswith("6"):
                    code = f"{code}.XSHG"
                else:
                    code = f"{code}.XSHE"
            
            # 默认字段
            if fields is None:
                fields = ["open", "high", "low", "close", "volume", "money"]
            
            # 获取数据
            df = jq.get_bars(
                securities=[code],
                count=count,
                end_date=end_date or datetime.now().strftime("%Y-%m-%d"),
                unit="1d",
                fields=fields,
                include_now=True
            )
            
            if df is not None and not df.empty:
                df = df.reset_index()
                df["date"] = pd.to_datetime(df["date"])
                return df
            
            return None
        except Exception as e:
            print(f"获取 {code} 数据失败: {e}")
            return None
    
    def get_index_stocks(self, index_code: str = "000300.XSHG") -> List[str]:
        """
        获取指数成分股
        
        Args:
            index_code: 指数代码, 如 "000300.XSHG" (沪深300)
        """
        if not self.connected:
            return []
        
        try:
            stocks = jq.get_index_stocks(index_code)
            return stocks
        except Exception as e:
            print(f"获取指数成分股失败: {e}")
            return []
    
    def get_limit_list(self, date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        获取涨停股列表
        
        Args:
            date: 日期, 默认今天
        """
        if not self.connected:
            return None
        
        try:
            today = date or datetime.now().strftime("%Y-%m-%d")
            
            # 获取所有股票
            all_stocks = jq.get_all_securities()
            
            # 过滤ST和退市
            all_stocks = all_stocks[~all_stocks["display_name"].str.contains("ST|退")]
            
            # 获取当日数据
            df = jq.get_price(all_stocks.index.tolist()[:500], 
                            start_date=today, 
                            end_date=today,
                            frequency="daily")
            
            if df is not None and not df.empty:
                if "close" in df.columns and "open" in df.columns:
                    df["pct_change"] = (df["close"] - df["open"]) / df["open"] * 100
                    limit_up = df[df["pct_change"] > 9.5]
                    return limit_up
            
            return None
        except Exception as e:
            print(f"获取涨停股列表失败: {e}")
            return None
    
    def disconnect(self):
        """断开连接"""
        if JOINQUANT_AVAILABLE and self.connected:
            try:
                jq.logout()
                self.connected = False
                print("聚宽连接已断开")
            except:
                pass


def get_baostock_data(code: str, count: int = 100) -> Optional[pd.DataFrame]:
    """
    BaoStock备用获取 (无需注册)
    
    Args:
        code: BaoStock格式代码, 如 "sh.000001"
        count: 数据条数
    
    Returns:
        DataFrame 或 None
    """
    try:
        import baostock as bs
        
        # 转换代码格式
        if "." in code:
            exchange, num = code.split(".")
            bs_code = f"{exchange.lower()}.{num}"
        else:
            bs_code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
        
        bs.login()
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume,amount",
            start_date=(datetime.now() - timedelta(days=count * 2)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            frequency="d",
            adjustflag="3"
        )
        
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        bs.logout()
        
        if rows:
            df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume","amount"])
            for c in ["open","high","low","close","volume","amount"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            return df.tail(count)
        
        return None
    except Exception as e:
        print(f"BaoStock获取失败: {e}")
        return None


class UnifiedDataFetcher:
    """
    统一数据获取器 - 自动选择最佳数据源
    
    优先级:
    1. 聚宽 (需要注册, 数据最全)
    2. BaoStock (免费, 无需注册)
    """
    
    def __init__(self):
        self.jq_fetcher = JoinQuantFetcher()
        self.baostock_available = False
        
        # 检查BaoStock
        try:
            import baostock as bs
            bs.login()
            bs.logout()
            self.baostock_available = True
        except:
            pass
    
    def get_stock_data(self, code: str, count: int = 100, 
                       prefer_source: str = "auto") -> Optional[pd.DataFrame]:
        """获取股票数据"""
        # 1. 优先使用聚宽
        if prefer_source in ["joinquant", "auto"]:
            if self.jq_fetcher.connected:
                df = self.jq_fetcher.get_security_bars(code, count=count)
                if df is not None:
                    return df
        
        # 2. 备用BaoStock
        if prefer_source in ["baostock", "auto"]:
            if self.baostock_available:
                return get_baostock_data(code, count)
        
        return None
    
    def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "sources": [],
            "data": {}
        }
        
        # 聚宽
        if self.jq_fetcher.connected:
            result["sources"].append("joinquant")
            try:
                snapshot = self.jq_fetcher.get_market_snapshot()
                if snapshot is not None:
                    result["data"]["joinquant"] = snapshot.to_dict()
            except:
                pass
        
        # BaoStock
        if self.baostock_available:
            result["sources"].append("baostock")
            indices = [
                ("sh.000001", "上证指数"),
                ("sz.399001", "深证成指"),
                ("sz.399006", "创业板指"),
                ("sh.000300", "沪深300"),
            ]
            
            import baostock as bs
            bs.login()
            
            baostock_data = {}
            for code, name in indices:
                try:
                    rs = bs.query_history_k_data_plus(
                        code, "date,close,volume",
                        start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                        end_date=datetime.now().strftime("%Y-%m-%d"),
                        frequency="d"
                    )
                    rows = []
                    while rs.error_code == "0" and rs.next():
                        rows.append(rs.get_row_data())
                    if rows:
                        baostock_data[name] = rows[-1]
                except:
                    pass
            
            bs.logout()
            result["data"]["baostock"] = baostock_data
        
        return result
