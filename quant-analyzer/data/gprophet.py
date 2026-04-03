"""
G-Prophet API 集成模块
AI驱动的股票预测与市场分析平台

API文档: https://www.gprophet.com/api/external/v1
功能:
- 股票价格预测 (LSTM/Transformer/蒙特卡洛)
- 多算法对比预测
- 技术指标分析
- AI股票分析报告 (5维度)
- 市场情绪/恐惧贪婪指数
- 实时报价/历史K线

市场支持: US(美股), CN(A股), HK(港股), CRYPTO(加密货币)
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# API 基础URL
BASE_URL = "https://www.gprophet.com/api/external/v1"

# 支持的市场
MARKETS = {
    "CN": "A股",
    "US": "美股",
    "HK": "港股",
    "CRYPTO": "加密货币",
}

# 支持的算法
ALGORITHMS = [
    "auto",           # 自动选择
    "gprophet2026v1", # G-Prophet 2026 v1 (蒙特卡洛)
    "lstm",           # LSTM神经网络
    "transformer",    # Transformer
    "random_forest",  # 随机森林
    "ensemble",       # 集成模型
]

# 点数消耗表
POINTS_COST = {
    "predict_cn": 10,
    "predict_hk": 15,
    "predict_us": 20,
    "predict_crypto": 20,
    "market_data": 5,
    "technical": 5,
    "sentiment": 5,
    "analysis_stock": 58,
    "analysis_comprehensive": 150,
}

# 技术指标列表
TECHNICAL_INDICATORS = ["rsi", "macd", "bollinger", "kdj", "sma", "ema"]


@dataclass
class PredictionResult:
    """预测结果"""
    symbol: str
    name: str
    market: str
    current_price: float
    predicted_price: float
    change_percent: float
    direction: str       # up/down/neutral
    confidence: float    # 0-1
    days: int
    algorithm: str
    data_quality: Dict = None


@dataclass
class CompareResult:
    """多算法对比结果"""
    symbol: str
    name: str
    market: str
    current_price: float
    days: int
    results: List[Dict]
    best_algorithm: str
    consensus_direction: str
    average_predicted_price: float


@dataclass
class TechnicalResult:
    """技术分析结果"""
    symbol: str
    market: str
    current_price: float
    indicators: Dict
    signals: List[Dict]
    overall_signal: str
    signal_strength: float


@dataclass
class AnalysisReport:
    """AI分析报告"""
    symbol: str
    market: str
    overall_rating: str
    confidence: float
    agents: Dict           # 各维度分析结果
    recommendation: str
    risk_level: str


class GProphetClient:
    """G-Prophet API 客户端"""

    def __init__(self, api_key: str = None):
        """
        初始化客户端
        
        Args:
            api_key: G-Prophet API Key (gp_sk_...)
                    也可通过环境变量 GPROPHET_API_KEY 设置
        """
        self.api_key = api_key or os.getenv("GPROPHET_API_KEY", "")
        self.session = None
        
        if not self.api_key:
            raise ValueError("请设置 GPROPHET_API_KEY 环境变量或传入 api_key 参数")

    def _get_session(self):
        """懒加载 HTTP session"""
        if self.session is None:
            try:
                import requests
                self.session = requests.Session()
                self.session.headers.update({
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                })
            except ImportError:
                raise ImportError("请安装 requests: pip install requests")
        return self.session

    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET 请求"""
        session = self._get_session()
        url = f"{BASE_URL}{endpoint}"
        try:
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _post(self, endpoint: str, data: Dict = None) -> Dict:
        """POST 请求"""
        session = self._get_session()
        url = f"{BASE_URL}{endpoint}"
        try:
            resp = session.post(url, json=data, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ========== 股票价格预测 ==========

    def predict(
        self,
        symbol: str,
        market: str = "CN",
        days: int = 7,
        algorithm: str = "auto"
    ) -> Optional[PredictionResult]:
        """
        AI预测股票价格
        
        Args:
            symbol: 股票代码 (如 600519, AAPL, BTCUSDT)
            market: 市场 (CN/US/HK/CRYPTO)
            days: 预测天数 (1-30)
            algorithm: 算法 (auto/gprophet2026v1/lstm/transformer/random_forest/ensemble)
        
        Returns:
            PredictionResult or None
        """
        data = {
            "symbol": symbol,
            "market": market,
            "days": min(max(days, 1), 30),
            "algorithm": algorithm,
        }
        
        result = self._post("/predictions/predict", data)
        
        if result.get("success") and result.get("data"):
            d = result["data"]
            return PredictionResult(
                symbol=d.get("symbol", symbol),
                name=d.get("name", ""),
                market=d.get("market", market),
                current_price=d.get("current_price", 0),
                predicted_price=d.get("predicted_price", 0),
                change_percent=d.get("change_percent", 0),
                direction=d.get("direction", "neutral"),
                confidence=d.get("confidence", 0),
                days=d.get("prediction_days", days),
                algorithm=d.get("algorithm_used", algorithm),
                data_quality=d.get("data_quality", {}),
            )
        return None

    def predict_compare(
        self,
        symbol: str,
        market: str = "CN",
        days: int = 5,
        algorithms: List[str] = None
    ) -> Optional[CompareResult]:
        """
        多算法对比预测
        
        Args:
            symbol: 股票代码
            market: 市场
            days: 预测天数
            algorithms: 算法列表
        
        Returns:
            CompareResult or None
        """
        if algorithms is None:
            algorithms = ["gprophet2026v1", "lstm", "transformer", "ensemble"]
        
        data = {
            "symbol": symbol,
            "market": market,
            "days": min(max(days, 1), 30),
            "algorithms": algorithms[:6],
        }
        
        result = self._post("/predictions/compare", data)
        
        if result.get("success") and result.get("data"):
            d = result["data"]
            return CompareResult(
                symbol=d.get("symbol", symbol),
                name=d.get("name", ""),
                market=d.get("market", market),
                current_price=d.get("current_price", 0),
                days=d.get("prediction_days", days),
                results=d.get("results", []),
                best_algorithm=d.get("best_algorithm", ""),
                consensus_direction=d.get("consensus_direction", ""),
                average_predicted_price=d.get("average_predicted_price", 0),
            )
        return None

    # ========== 市场数据 ==========

    def get_quote(self, symbol: str, market: str = "CN") -> Optional[Dict]:
        """获取实时报价"""
        return self._get("/market-data/quote", {
            "symbol": symbol, "market": market
        })

    def get_history(
        self,
        symbol: str,
        market: str = "CN",
        period: str = "3m"
    ) -> Optional[Dict]:
        """
        获取历史K线数据
        
        Args:
            period: 时间范围 (1w/1m/3m/6m/1y/2y)
        """
        return self._get("/market-data/history", {
            "symbol": symbol, "market": market, "period": period
        })

    def search(self, keyword: str, market: str = "CN", limit: int = 10) -> Optional[Dict]:
        """搜索股票"""
        return self._get("/market-data/search", {
            "keyword": keyword, "market": market, "limit": min(limit, 50)
        })

    def batch_quote(self, symbols: List[str], market: str = "CN") -> Optional[Dict]:
        """批量获取报价 (最多20个)"""
        data = {
            "symbols": symbols[:20],
            "market": market,
        }
        return self._post("/market-data/batch-quote", data)

    # ========== 技术分析 ==========

    def technical_analyze(
        self,
        symbol: str,
        market: str = "CN",
        indicators: List[str] = None
    ) -> Optional[TechnicalResult]:
        """
        技术指标分析
        
        Args:
            indicators: 指标列表 (rsi/macd/bollinger/kdj/sma/ema)
        """
        if indicators is None:
            indicators = ["rsi", "macd", "bollinger", "kdj"]
        
        data = {
            "symbol": symbol,
            "market": market,
            "indicators": indicators,
        }
        
        result = self._post("/technical/analyze", data)
        
        if result.get("success") and result.get("data"):
            d = result["data"]
            return TechnicalResult(
                symbol=d.get("symbol", symbol),
                market=d.get("market", market),
                current_price=d.get("current_price", 0),
                indicators=d.get("indicators", {}),
                signals=d.get("signals", []),
                overall_signal=d.get("overall_signal", ""),
                signal_strength=d.get("signal_strength", 0),
            )
        return None

    # ========== 市场情绪 ==========

    def get_fear_greed(self, days: int = 1) -> Optional[Dict]:
        """获取恐惧与贪婪指数 (加密货币)"""
        return self._get("/sentiment/fear-greed", {"days": days})

    def get_market_overview(self, market: str = "CN") -> Optional[Dict]:
        """获取市场概览"""
        return self._get("/sentiment/market-overview", {"market": market})

    # ========== AI分析 (异步) ==========

    def analyze_stock(
        self,
        symbol: str,
        market: str = "CN",
        locale: str = "zh-CN",
        poll_interval: int = 5,
        timeout: int = 120
    ) -> Optional[AnalysisReport]:
        """
        AI股票分析报告 (58点数)
        
        自动提交任务并轮询结果
        
        Args:
            locale: 报告语言 (zh-CN/en-US)
            poll_interval: 轮询间隔秒数
            timeout: 超时秒数
        """
        data = {
            "symbol": symbol,
            "market": market,
            "locale": locale,
        }
        
        result = self._post("/analysis/stock", data)
        
        if not result.get("success"):
            return None
        
        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            return None
        
        return self._poll_task(task_id, poll_interval, timeout)

    def analyze_comprehensive(
        self,
        symbol: str,
        market: str = "CN",
        locale: str = "zh-CN",
        poll_interval: int = 5,
        timeout: int = 180
    ) -> Optional[AnalysisReport]:
        """
        多维度深度分析 (150点数)
        
        5维度: 技术面/基本面/资金流向/市场情绪/宏观环境
        
        Args:
            locale: 报告语言 (zh-CN/en-US)
            poll_interval: 轮询间隔秒数
            timeout: 超时秒数
        """
        data = {
            "symbol": symbol,
            "market": market,
            "locale": locale,
        }
        
        result = self._post("/analysis/comprehensive", data)
        
        if not result.get("success"):
            return None
        
        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            return None
        
        return self._poll_task(task_id, poll_interval, timeout)

    def _poll_task(
        self,
        task_id: str,
        poll_interval: int = 5,
        timeout: int = 120
    ) -> Optional[AnalysisReport]:
        """轮询异步任务结果"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self._get(f"/analysis/task/{task_id}")
            
            if not result.get("success"):
                time.sleep(poll_interval)
                continue
            
            data = result.get("data", {})
            status = data.get("status", "")
            
            if status == "completed":
                analysis = data.get("result", {}).get("analysis", {})
                return AnalysisReport(
                    symbol=data.get("result", {}).get("symbol", ""),
                    market="",
                    overall_rating=analysis.get("overall_rating", ""),
                    confidence=analysis.get("confidence", 0),
                    agents=analysis.get("agents", {}),
                    recommendation=analysis.get("final_recommendation", ""),
                    risk_level=analysis.get("risk_level", ""),
                )
            elif status == "failed":
                return None
            
            time.sleep(poll_interval)
        
        return None  # 超时

    # ========== 账户 ==========

    def get_balance(self) -> Optional[Dict]:
        """查询API余额"""
        return self._get("/account/balance")

    def get_usage(self, days: int = 7) -> Optional[Dict]:
        """获取调用历史"""
        return self._get("/account/usage", {"days": days})

    def get_info(self) -> Optional[Dict]:
        """获取API元数据"""
        return self._get("/info")


# ========== 便捷函数 ==========

def create_client() -> Optional[GProphetClient]:
    """创建G-Prophet客户端 (如果API Key可用)"""
    api_key = os.getenv("GPROPHET_API_KEY", "")
    if api_key:
        return GProphetClient(api_key)
    return None


def quick_predict(symbol: str, market: str = "CN", days: int = 7) -> Optional[PredictionResult]:
    """快速预测"""
    client = create_client()
    if client:
        return client.predict(symbol, market, days)
    return None


def quick_technical(symbol: str, market: str = "CN") -> Optional[TechnicalResult]:
    """快速技术分析"""
    client = create_client()
    if client:
        return client.technical_analyze(symbol, market)
    return None
