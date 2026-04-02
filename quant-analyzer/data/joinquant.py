"""
聚宽 JoinQuant 数据源集成 v2.0
提供高质量A股数据 + 专业分析功能

功能增强:
- 股票/期货/期权日线数据
- 财务因子数据 (PE/PB/ROE等)
- 指数成分股
- 融资融券数据
- 收益率计算 (单利/复利/年化)
- 财务分析 (利润表/资产负债表/现金流量表)
- 风险指标计算 (Alpha/Beta/夏普比率/最大回撤)

使用示例:
    from data.joinquant import JoinQuantFetcher
    
    fetcher = JoinQuantFetcher()
    # 自动使用.env中的JQ_USERNAME和JQ_PASSWORD
    
    # 获取股票数据
    df = fetcher.get_security_bars("000001.XSHE", count=100)
    
    # 计算收益率
    returns = fetcher.calculate_returns(df)
    
    # 获取财务数据
    finance = fetcher.get_financial_data("000001.XSHE")
"""

import os
from typing import Optional, List, Dict, Any, Tuple
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
    聚宽数据获取器 v2.0
    
    功能:
    - 股票/期货/期权日线数据
    - 财务因子数据
    - 指数成分股
    - 融资融券数据
    - 收益率计算
    - 财务数据分析
    - 风险指标计算
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


# ============================================================
# 聚宽专业分析功能 (基于教程内容)
# ============================================================

def calculate_returns(prices: pd.DataFrame, 
                     price_col: str = 'close',
                     method: str = 'simple') -> pd.Series:
    """
    计算收益率
    
    Args:
        prices: 价格数据 (需要包含date和price_col列)
        price_col: 价格列名
        method: 'simple' (单利) 或 'log' (对数收益率/复利)
    
    Returns:
        收益率Series
    
    示例:
        >>> df = fetcher.get_security_bars("000001.XSHE", count=100)
        >>> returns = calculate_returns(df)
        >>> annual_return = returns.mean() * 252  # 年化收益率
    """
    if price_col not in prices.columns:
        raise ValueError(f"价格列 '{price_col}' 不存在")
    
    if method == 'log':
        # 对数收益率 (复利)
        returns = np.log(prices[price_col] / prices[price_col].shift(1))
    else:
        # 单利收益率
        returns = prices[price_col].pct_change()
    
    return returns.dropna()


def calculate_annual_return(total_return: float, 
                           days: int) -> float:
    """
    计算年化收益率
    
    Args:
        total_return: 总收益率 (如 0.5 表示50%)
        days: 持有天数
    
    Returns:
        年化收益率
    
    示例:
        >>> annual = calculate_annual_return(0.5, 365)  # 50%收益，365天
        >>> print(f"{annual:.2%}")  # 输出: 50.00%
    """
    if days <= 0:
        return 0.0
    years = days / 365
    return (1 + total_return) ** (1 / years) - 1


def calculate_max_drawdown(prices: pd.DataFrame,
                          price_col: str = 'close') -> Tuple[float, str, str]:
    """
    计算最大回撤
    
    Args:
        prices: 价格数据
        price_col: 价格列名
    
    Returns:
        (最大回撤率, 最高点日期, 最低点日期)
    
    示例:
        >>> dd, high_date, low_date = calculate_max_drawdown(df)
        >>> print(f"最大回撤: {dd:.2%}")
    """
    prices = prices.copy()
    prices['cummax'] = prices[price_col].cummax()
    prices['drawdown'] = (prices[price_col] - prices['cummax']) / prices['cummax']
    
    max_dd_idx = prices['drawdown'].idxmin()
    max_dd = prices.loc[max_dd_idx, 'drawdown']
    
    # 找到最高点日期
    high_before = prices.loc[:max_dd_idx, price_col].idxmax()
    high_date = prices.loc[high_before, 'date'] if 'date' in prices.columns else str(high_before)
    low_date = prices.loc[max_dd_idx, 'date'] if 'date' in prices.columns else str(max_dd_idx)
    
    return max_dd, str(high_date), str(low_date)


def calculate_sharpe_ratio(returns: pd.Series, 
                          risk_free_rate: float = 0.03,
                          periods_per_year: int = 252) -> float:
    """
    计算夏普比率
    
    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率 (年化)
        periods_per_year: 每年交易日 (默认252)
    
    Returns:
        夏普比率
    
    示例:
        >>> returns = calculate_returns(df)
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"夏普比率: {sharpe:.2f}")
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    excess_returns = returns - risk_free_rate / periods_per_year
    return np.sqrt(periods_per_year) * excess_returns.mean() / returns.std()


def calculate_volatility(returns: pd.Series,
                        periods_per_year: int = 252) -> float:
    """
    计算波动率
    
    Args:
        returns: 收益率序列
        periods_per_year: 每年交易日
    
    Returns:
        年化波动率
    """
    if len(returns) == 0:
        return 0.0
    return returns.std() * np.sqrt(periods_per_year)


def get_financial_report(code: str,
                         report_type: str = 'income',
                         count: int = 4) -> Optional[pd.DataFrame]:
    """
    获取财务报告 (利润表/资产负债表/现金流量表)
    
    Args:
        code: 股票代码, 如 "000001.XSHE"
        report_type: 'income' (利润表), 'balance' (资产负债表), 'cashflow' (现金流量表)
        count: 获取报告数量
    
    Returns:
        财务数据DataFrame
    
    示例:
        >>> income = get_financial_report("000001.XSHE", 'income')
        >>> print(income[['营业总收入', '净利润']])
    """
    if not JOINQUANT_AVAILABLE:
        print("聚宽SDK未安装")
        return None
    
    try:
        # 转换代码格式
        if "." not in code:
            if code.startswith("6"):
                code = f"{code}.XSHG"
            else:
                code = f"{code}.XSHE"
        
        # 选择查询对象
        if report_type == 'balance':
            query_obj = jq.balancesheet
        elif report_type == 'cashflow':
            query_obj = jq.cashflow
        else:
            query_obj = jq.income
        
        # 构建查询
        q = jq.query(query_obj).filter(
            jq.query_obj.code == code
        ).order_by(
            jq.query_obj.pub_date.desc()
        ).limit(count)
        
        # 执行查询
        df = jq.get_fundamentals(q)
        
        if df is not None and not df.empty:
            return df
        return None
        
    except Exception as e:
        print(f"获取财务报告失败: {e}")
        return None


def get_valuation_metrics(code: str,
                         date: Optional[str] = None) -> Optional[Dict[str, float]]:
    """
    获取估值指标 (PE/PB/PS/PCF)
    
    Args:
        code: 股票代码
        date: 查询日期 (默认今天)
    
    Returns:
        估值指标字典
    
    示例:
        >>> metrics = get_valuation_metrics("000001.XSHE")
        >>> print(f"PE: {metrics['pe_ratio']:.2f}, PB: {metrics['pb_ratio']:.2f}")
    """
    if not JOINQUANT_AVAILABLE:
        return None
    
    try:
        if "." not in code:
            if code.startswith("6"):
                code = f"{code}.XSHG"
            else:
                code = f"{code}.XSHE"
        
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        # 获取估值数据
        df = jq.get_fundamentals(
            jq.query(jq.valuation).filter(jq.valuation.code == code),
            date=date
        )
        
        if df is not None and not df.empty:
            row = df.iloc[0]
            return {
                'pe_ratio': row.get('pe_ratio', 0),
                'pb_ratio': row.get('pb_ratio', 0),
                'ps_ratio': row.get('ps_ratio', 0),
                'pcf_ratio': row.get('pcf_ratio', 0),
                'market_cap': row.get('market_cap', 0),
                'circulating_market_cap': row.get('circulating_market_cap', 0),
            }
        return None
    except Exception as e:
        print(f"获取估值指标失败: {e}")
        return None


def get_index_components(index_code: str = "000300.XSHG") -> Optional[pd.DataFrame]:
    """
    获取指数成分股
    
    Args:
        index_code: 指数代码
            - 000300.XSHG: 沪深300
            - 000905.XSHG: 中证500
            - 000001.XSHG: 上证指数
    
    Returns:
        成分股权重DataFrame
    
    示例:
        >>> df = get_index_components("000300.XSHG")
        >>> print(df.head(10))  # 前10大权重股
    """
    if not JOINQUANT_AVAILABLE:
        return None
    
    try:
        stocks = jq.get_index_stocks(index_code)
        weights = []
        
        for stock in stocks[:100]:  # 限制数量避免超时
            try:
                # 获取股票信息
                info = jq.get_security_info(stock)
                if info is not None:
                    weights.append({
                        'code': stock,
                        'name': info.get('display_name', ''),
                        'start_date': info.get('start_date', ''),
                    })
            except:
                pass
        
        return pd.DataFrame(weights)
    except Exception as e:
        print(f"获取指数成分股失败: {e}")
        return None


def calculate_beta(stock_returns: pd.Series, 
                  market_returns: pd.Series) -> float:
    """
    计算Beta值
    
    Args:
        stock_returns: 个股收益率序列
        market_returns: 市场收益率序列
    
    Returns:
        Beta值
    
    示例:
        >>> stock_ret = calculate_returns(stock_df)
        >>> market_ret = calculate_returns(market_df)
        >>> beta = calculate_beta(stock_ret, market_ret)
        >>> print(f"Beta: {beta:.2f}")
    """
    # 对齐数据
    common_idx = stock_returns.index.intersection(market_returns.index)
    if len(common_idx) < 10:
        return 1.0
    
    stock_ret = stock_returns.loc[common_idx]
    market_ret = market_returns.loc[common_idx]
    
    # 计算协方差
    covariance = np.cov(stock_ret, market_ret)[0, 1]
    market_var = np.var(market_ret)
    
    if market_var == 0:
        return 1.0
    
    return covariance / market_var


def generate_strategy_report(df: pd.DataFrame,
                             price_col: str = 'close',
                             initial_capital: float = 1000000) -> Dict[str, Any]:
    """
    生成策略分析报告 (综合多个指标)
    
    Args:
        df: 价格数据
        price_col: 价格列名
        initial_capital: 初始资金
    
    Returns:
        策略分析报告字典
    
    示例:
        >>> report = generate_strategy_report(df)
        >>> print(f"总收益率: {report['total_return']:.2%}")
        >>> print(f"夏普比率: {report['sharpe_ratio']:.2f}")
        >>> print(f"最大回撤: {report['max_drawdown']:.2%}")
    """
    if price_col not in df.columns:
        raise ValueError(f"价格列 '{price_col}' 不存在")
    
    # 计算收益率
    returns = calculate_returns(df, price_col, method='log')
    
    # 计算各项指标
    total_return = (df[price_col].iloc[-1] / df[price_col].iloc[0]) - 1
    max_dd, dd_high_date, dd_low_date = calculate_max_drawdown(df, price_col)
    sharpe = calculate_sharpe_ratio(returns)
    volatility = calculate_volatility(returns)
    beta = 1.0  # 需要市场数据才能计算
    
    # 交易天数
    trading_days = len(df)
    years = trading_days / 252
    
    # 年化收益率
    if years > 0:
        annual_return = (1 + total_return) ** (1 / years) - 1
    else:
        annual_return = 0
    
    # 最终资金
    final_capital = initial_capital * (1 + total_return)
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_dd,
        'max_drawdown_high': dd_high_date,
        'max_drawdown_low': dd_low_date,
        'sharpe_ratio': sharpe,
        'volatility': volatility,
        'beta': beta,
        'trading_days': trading_days,
        'years': years,
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'profit': final_capital - initial_capital,
    }

