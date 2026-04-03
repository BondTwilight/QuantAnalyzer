"""
🧠 QuantBrain — AI量化策略自学习引擎
核心闭环: 搜索策略 → 学习解析 → 回测验证 → 生成信号 → 跟踪收益 → 自动优化
"""
import json
import hashlib
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
# 数据层
# ═══════════════════════════════════════════════

DATA_DIR = Path(__file__).parent.parent / "data"
SIGNALS_FILE = DATA_DIR / "signals.json"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
STRATEGY_KB_FILE = DATA_DIR / "strategy_knowledge.json"
LEARNING_LOG_FILE = DATA_DIR / "learning_log.json"
DATA_DIR.mkdir(exist_ok=True)

# 云存储支持
try:
    from core.github_storage import load_state, save_state, init_cloud_sync
    CLOUD_STORAGE_AVAILABLE = True
except ImportError:
    CLOUD_STORAGE_AVAILABLE = False


def _load_json_file(filepath: Path) -> dict:
    """统一加载JSON文件：优先GitHub云存储，回退本地"""
    if CLOUD_STORAGE_AVAILABLE:
        data = load_state(filepath.name, str(DATA_DIR))
        if data:
            return data
    if filepath.exists():
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_json_file(filepath: Path, data: dict):
    """统一保存JSON文件：本地 + GitHub云存储"""
    filepath.parent.mkdir(exist_ok=True)
    try:
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"保存本地文件失败: {e}")
    if CLOUD_STORAGE_AVAILABLE:
        save_state(filepath.name, data, str(DATA_DIR))


@dataclass
class TradeSignal:
    """交易信号"""
    id: str = ""
    stock_code: str = ""
    stock_name: str = ""
    direction: str = "BUY"  # BUY / SELL
    strategy_name: str = ""
    confidence: float = 0.0  # 0-100
    reason: str = ""
    price: float = 0.0  # 信号触发价
    target_price: float = 0.0  # 目标价
    stop_loss: float = 0.0  # 止损价
    created_at: str = ""
    status: str = "PENDING"  # PENDING / EXECUTED / CLOSED
    executed_price: float = 0.0  # 实际买入价
    closed_price: float = 0.0  # 实际卖出价
    profit_pct: float = 0.0  # 收益率%
    closed_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = datetime.now().strftime("%Y%m%d%H%M%S") + hashlib.md5(
                f"{self.stock_code}{self.direction}{self.created_at}".encode()
            ).hexdigest()[:6]
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")


@dataclass
class Position:
    """持仓"""
    stock_code: str = ""
    stock_name: str = ""
    shares: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    buy_date: str = ""
    strategy_name: str = ""
    signal_id: str = ""
    stop_loss: float = 0.0
    target_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.shares * self.avg_cost

    @property
    def profit_pct(self) -> float:
        if self.avg_cost <= 0:
            return 0.0
        return round((self.current_price - self.avg_cost) / self.avg_cost * 100, 2)

    @property
    def profit_amount(self) -> float:
        return self.market_value - self.cost_basis


@dataclass
class StrategyKnowledge:
    """策略知识条目"""
    name: str = ""
    category: str = ""
    source: str = ""
    code: str = ""
    description: str = ""
    factors: List[str] = field(default_factory=list)
    backtest_result: Dict = field(default_factory=dict)
    quality_score: float = 0.0  # 0-100
    real_trade_count: int = 0
    real_win_rate: float = 0.0
    real_avg_profit: float = 0.0
    learned_at: str = ""
    last_optimized: str = ""
    optimization_history: List[Dict] = field(default_factory=list)


@dataclass
class LearningRecord:
    """学习记录"""
    date: str = ""
    action: str = ""  # learn / optimize / trade / evaluate
    strategy: str = ""
    result: str = ""
    metrics: Dict = field(default_factory=dict)
    ai_insight: str = ""


# ═══════════════════════════════════════════════
# 数据提供器 — 多源统一接口
# ═══════════════════════════════════════════════

class DataProvider:
    """股票数据统一接口"""

    _bs_logged_in = False

    @classmethod
    def _bs_login(cls):
        """BaoStock 连接复用，避免每次都 login/logout"""
        if not cls._bs_logged_in:
            import baostock as bs
            lg = bs.login()
            if lg.error_code != '0':
                logger.warning(f"BaoStock login failed: {lg.error_msg}")
            cls._bs_logged_in = True
        return cls._bs_logged_in

    @classmethod
    def _bs_logout(cls):
        """仅在应用退出时 logout"""
        if cls._bs_logged_in:
            try:
                import baostock as bs
                bs.logout()
            except:
                pass
            cls._bs_logged_in = False

    @staticmethod
    def get_stock_daily(stock_code: str, start_date: str = None, end_date: str = None, days: int = None) -> pd.DataFrame:
        """获取股票日K数据 (BaoStock备用)"""
        try:
            import baostock as bs
            if not DataProvider._bs_login():
                return pd.DataFrame()

            # 标准化代码格式
            code = stock_code.replace(".SZ", "").replace(".SH", "")
            if code.startswith("6"):
                code = f"sh.{code}"
            elif code.startswith(("0", "3")):
                code = f"sz.{code}"
            else:
                code = f"sz.{code}"

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                lookback = days or 365
                start_date = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")

            rs = bs.query_history_k_data_plus(
                code,
                "date,open,high,low,close,volume,amount,turn",
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2"  # 前复权
            )

            data_rows = []
            while rs.next():
                row = rs.get_row_data()
                if row and row[0] and row[4] != '0':  # 排除停牌
                    try:
                        data_rows.append({
                            "date": row[0],
                            "open": float(row[1]),
                            "high": float(row[2]),
                            "low": float(row[3]),
                            "close": float(row[4]),
                            "volume": float(row[5]),
                            "amount": float(row[6]) if row[6] else 0,
                            "turnover": float(row[7]) if row[7] else 0,
                        })
                    except (ValueError, IndexError):
                        continue

            if not data_rows:
                return pd.DataFrame()

            df = pd.DataFrame(data_rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            return df

        except Exception as e:
            logger.error(f"get_stock_daily failed for {stock_code}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_stock_info(stock_code: str) -> Dict:
        """获取股票基本信息（带缓存）"""
        # 缓存股票名称，避免重复查询
        if not hasattr(DataProvider, '_name_cache'):
            DataProvider._name_cache = {}
        if stock_code in DataProvider._name_cache:
            return DataProvider._name_cache[stock_code]

        try:
            import baostock as bs
            if not DataProvider._bs_login():
                return {"code": stock_code, "name": stock_code}
            code = stock_code.replace(".SZ", "").replace(".SH", "")
            if code.startswith("6"):
                code = f"sh.{code}"
            else:
                code = f"sz.{code}"

            rs = bs.query_stock_basic(code=code)
            data = {}
            if rs.next():
                row = rs.get_row_data()
                if row:
                    data = {
                        "code": row[0],
                        "name": row[1] if len(row) > 1 else stock_code,
                        "ipo_date": row[2] if len(row) > 2 else "",
                        "out_date": row[3] if len(row) > 3 else "",
                        "type": row[4] if len(row) > 4 else "",
                        "status": row[5] if len(row) > 5 else "",
                    }
            if not data:
                data = {"code": stock_code, "name": stock_code}
            DataProvider._name_cache[stock_code] = data
            return data
        except:
            return {"code": stock_code, "name": stock_code}

    @staticmethod
    def get_stock_list() -> pd.DataFrame:
        """获取全部A股列表"""
        try:
            import baostock as bs
            lg = bs.login()
            rs = bs.query_stock_basic()
            rows = []
            while rs.next():
                row = rs.get_row_data()
                if row and row[5] == "1":  # 上市状态
                    rows.append({
                        "code": row[0],
                        "name": row[1],
                        "type": row[4],
                    })
            bs.logout()
            return pd.DataFrame(rows)
        except:
            return pd.DataFrame()

    @staticmethod
    def get_index_daily(index_code: str = "sh.000300", days: int = 365) -> pd.DataFrame:
        """获取指数日K"""
        try:
            import baostock as bs
            lg = bs.login()
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            rs = bs.query_history_k_data_plus(
                index_code,
                "date,open,high,low,close,volume",
                start_date=start, end_date=end,
                frequency="d", adjustflag="2"
            )
            rows = []
            while rs.next():
                row = rs.get_row_data()
                if row and row[4] and row[4] != '0':
                    rows.append({
                        "date": row[0],
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                    })
            bs.logout()
            return pd.DataFrame(rows)
        except:
            return pd.DataFrame()

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if df.empty:
            return df

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

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

        # KDJ (简化版)
        low_min = low.rolling(window=9).min()
        high_max = high.rolling(window=9).max()
        rsv = (close - low_min) / (high_max - low_min + 1e-10) * 100
        df["k"] = rsv.ewm(com=2, adjust=False).mean()
        df["d"] = df["k"].ewm(com=2, adjust=False).mean()
        df["j"] = 3 * df["k"] - 2 * df["d"]

        return df


# ═══════════════════════════════════════════════
# 策略信号生成器
# ═══════════════════════════════════════════════

class SignalGenerator:
    """基于内置策略生成交易信号"""

    # 策略配置
    STRATEGIES = {
        "multi_signal": {
            "name": "多信号共振策略",
            "desc": "RSI+MACD+均线三重确认",
            "weight": 3.0,
        },
        "breakout": {
            "name": "突破策略",
            "desc": "价格突破N日新高/新低",
            "weight": 2.0,
        },
        "bollinger_reversal": {
            "name": "布林带回归策略",
            "desc": "触及布林带上下轨后回归",
            "weight": 2.0,
        },
        "volume_breakout": {
            "name": "放量突破策略",
            "desc": "放量突破均线+价格确认",
            "weight": 1.5,
        },
        "momentum_reversal": {
            "name": "动量反转策略",
            "desc": "超跌后反弹+成交量放大",
            "weight": 1.5,
        },
        "trend_follow": {
            "name": "趋势跟踪策略",
            "desc": "均线多头排列+MACD趋势确认",
            "weight": 2.0,
        },
    }

    def generate_signals(self, stock_code: str, stock_name: str = "",
                         days: int = 120) -> List[TradeSignal]:
        """对单只股票生成交易信号"""
        from datetime import timedelta
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        data = DataProvider.get_stock_daily(stock_code, start_date=start)
        if data.empty or len(data) < 60:
            return []

        data = DataProvider.calculate_indicators(data)
        if len(data) < 65:
            return []
        # 用最后一根有效数据行（跳过可能有NaN的前几行）
        data = data.dropna(subset=["rsi", "macd_hist", "ma_20", "ma_60"], how="any").reset_index(drop=True)
        if len(data) < 3:
            return []

        signals = []
        latest = data.iloc[-2]  # 用倒数第二根K线（当天可能未收盘）
        prev = data.iloc[-3]
        current_price = float(latest["close"])

        for strat_key, strat_info in self.STRATEGIES.items():
            buy_signal, sell_signal, reason = self._check_strategy(strat_key, data, latest, prev)
            if buy_signal:
                confidence = min(95, 50 + int(20 * strat_info["weight"]))
                signals.append(TradeSignal(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    direction="BUY",
                    strategy_name=strat_info["name"],
                    confidence=confidence,
                    reason=f"[{strat_info['name']}] {reason}",
                    price=current_price,
                    target_price=round(current_price * 1.08, 2),
                    stop_loss=round(current_price * 0.95, 2),
                ))
            elif sell_signal:
                confidence = min(95, 50 + int(20 * strat_info["weight"]))
                signals.append(TradeSignal(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    direction="SELL",
                    strategy_name=strat_info["name"],
                    confidence=confidence,
                    reason=f"[{strat_info['name']}] {reason}",
                    price=current_price,
                ))

        return signals

    def _check_strategy(self, strat_key: str, data: pd.DataFrame,
                         latest: pd.Series, prev: pd.Series) -> Tuple[bool, bool, str]:
        """检查单个策略的信号"""
        buy, sell = False, False
        reason = ""

        if strat_key == "multi_signal":
            # 三重共振: RSI + MACD + 均线
            rsi = latest["rsi"]
            macd_hist = latest["macd_hist"]
            prev_macd = prev["macd_hist"]
            ma5 = latest["ma_5"]
            ma20 = latest["ma_20"]
            prev_ma5 = prev["ma_5"]
            prev_ma20 = prev["ma_20"]

            buy_signals = 0
            sell_signals = 0

            if rsi < 40: buy_signals += 1  # 放宽到40
            elif rsi > 65: sell_signals += 1  # 放宽到65

            if prev_macd < 0 and macd_hist > 0: buy_signals += 1  # MACD金叉
            elif prev_macd > 0 and macd_hist < 0: sell_signals += 1  # MACD死叉

            if prev_ma5 < prev_ma20 and ma5 > ma20: buy_signals += 1  # 金叉
            elif prev_ma5 > prev_ma20 and ma5 < ma20: sell_signals += 1  # 死叉

            if buy_signals >= 2:
                buy = True
                reason = f"RSI={rsi:.0f} {'超卖' if rsi<35 else ''}, MACD金叉, MA5>MA20 ({buy_signals}/3共振)"
            elif sell_signals >= 2:
                sell = True
                reason = f"RSI={rsi:.0f} {'超买' if rsi>70 else ''}, MACD死叉, MA5<MA20 ({sell_signals}/3共振)"

        elif strat_key == "breakout":
            # 20日新高突破
            high_20 = data["high"].iloc[-22:-2].max()
            low_20 = data["low"].iloc[-22:-2].min()

            if latest["close"] > high_20:
                vol_ok = latest["volume"] > latest["vol_ma_20"] * 1.2
                if vol_ok:
                    buy = True
                    reason = f"放量突破20日新高 {high_20:.2f}，成交量={latest['volume']/1e6:.0f}万"
            elif latest["close"] < low_20:
                sell = True
                reason = f"跌破20日新低 {low_20:.2f}"

        elif strat_key == "bollinger_reversal":
            boll_upper = latest["boll_upper"]
            boll_lower = latest["boll_lower"]
            boll_mid = latest["boll_mid"]
            close = latest["close"]

            if close < boll_lower and prev["close"] >= prev["boll_lower"]:
                buy = True
                reason = f"价格{close:.2f}跌破布林下轨{boll_lower:.2f}，有望回归中轨{boll_mid:.2f}"
            elif close > boll_upper and prev["close"] <= prev["boll_upper"]:
                sell = True
                reason = f"价格{close:.2f}突破布林上轨{boll_upper:.2f}，可能回落"

        elif strat_key == "volume_breakout":
            if (latest["volume"] > latest["vol_ma_20"] * 2 and
                latest["close"] > latest["ma_20"] and
                prev["close"] <= prev["ma_20"]):
                buy = True
                reason = f"放量突破20日均线，成交量是均量{latest['volume']/latest['vol_ma_20']:.1f}倍"

        elif strat_key == "momentum_reversal":
            pct_5d = data["close"].iloc[-2] / data["close"].iloc[-7] - 1
            if pct_5d < -0.08:  # 5日跌超8%
                rsi = latest["rsi"]
                if rsi < 30:
                    vol_up = latest["volume"] > prev["volume"] * 1.3
                    if vol_up:
                        buy = True
                        reason = f"5日跌幅{pct_5d*100:.1f}%+RSI={rsi:.0f}超卖+放量，可能反弹"

        elif strat_key == "trend_follow":
            # 趋势跟踪: 均线多头排列 + MACD正值
            if (latest["ma_5"] > latest["ma_20"] > latest["ma_60"] and
                latest["macd_hist"] > 0 and
                latest["rsi"] < 65):
                buy = True
                reason = f"均线多头排列(MA5>{latest['ma_20']:.0f}>{latest['ma_60']:.0f}), MACD正向, 趋势健康"
            elif (latest["ma_5"] < latest["ma_20"] and
                  latest["macd_hist"] < 0 and latest["macd_hist"] < prev["macd_hist"]):
                sell = True
                reason = f"均线空头排列, MACD柱状线恶化，趋势转弱"

        return buy, sell, reason

    def scan_stocks(self, stock_list: List[str], progress_cb=None) -> List[TradeSignal]:
        """扫描多只股票生成信号"""
        all_signals = []
        total = len(stock_list)

        for i, code in enumerate(stock_list):
            if progress_cb:
                progress_cb((i + 1) / total, f"扫描 {code} ({i+1}/{total})")
            try:
                info = DataProvider.get_stock_info(code)
                name = info.get("name", code)
                signals = self.generate_signals(code, name)
                all_signals.extend(signals)
            except Exception as e:
                logger.warning(f"扫描 {code} 失败: {e}")

        # 按置信度排序
        all_signals.sort(key=lambda x: -x.confidence)
        return all_signals


# ═══════════════════════════════════════════════
# AI策略学习引擎
# ═══════════════════════════════════════════════

class StrategyLearner:
    """AI驱动的策略学习引擎"""

    def __init__(self):
        self.knowledge_base: List[StrategyKnowledge] = []
        self.learning_log: List[LearningRecord] = []
        self._load_data()

    def _load_data(self):
        """加载持久化数据（支持云存储）"""
        kb_data = _load_json_file(STRATEGY_KB_FILE)
        if kb_data:
            self.knowledge_base = [StrategyKnowledge(**d) for d in kb_data]
        log_data = _load_json_file(LEARNING_LOG_FILE)
        if log_data:
            self.learning_log = [LearningRecord(**d) for d in log_data]

    def _save_data(self):
        """保存持久化数据（支持云存储）"""
        _save_json_file(STRATEGY_KB_FILE, [asdict(k) for k in self.knowledge_base])
        _save_json_file(LEARNING_LOG_FILE, [asdict(l) for l in self.learning_log])

    def learn_from_github(self) -> List[StrategyKnowledge]:
        """从GitHub学习策略"""
        from core.strategy_crawler import StrategyCrawler
        crawler = StrategyCrawler()

        new_knowledge = []
        try:
            strategies = crawler.crawl_all()
        except Exception as e:
            logger.error(f"GitHub爬取失败: {e}")
            return []

        for s in strategies:
            if not s.code or not s.backtest_ready:
                continue

            # 检查是否已存在
            exists = any(k.name == s.name and k.source == s.source for k in self.knowledge_base)
            if exists:
                continue

            kb = StrategyKnowledge(
                name=s.name_cn or s.name,
                category=s.category,
                source=s.source,
                code=s.code,
                description=s.description,
                factors=s.factors,
                quality_score=s.quality_score * 10,
                learned_at=datetime.now().strftime("%Y-%m-%d"),
            )
            new_knowledge.append(kb)
            self.knowledge_base.append(kb)

            self.learning_log.append(LearningRecord(
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                action="learn",
                strategy=kb.name,
                result=f"从 {s.source} 学习，评分 {kb.quality_score:.0f}",
                metrics={"factors": s.factors, "quality": s.quality_score},
            ))

        if new_knowledge:
            self._save_data()

        return new_knowledge

    def learn_from_ai(self, prompt: str = "生成一个适合A股的量化交易策略") -> Optional[StrategyKnowledge]:
        """用AI生成/优化策略"""
        from config import ZHIPU_API_KEY
        import requests

        system_prompt = """你是一位资深量化交易策略专家。请生成一个基于Backtrader框架的A股量化策略。
要求:
1. 策略代码必须是完整的Python类，继承bt.Strategy
2. 包含明确的买入(self.buy)和卖出(self.sell/close)逻辑
3. 使用技术指标(均线/RSI/MACD/布林带/ATR等)组合
4. 加入止损逻辑和仓位管理
5. 策略要适合A股T+1规则
6. 直接输出Python代码，不要解释

只输出代码，不要其他文字。"""

        try:
            resp = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {ZHIPU_API_KEY}",
                },
                json={
                    "model": "glm-4-flash",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 4000,
                },
                timeout=60,
            )

            result = resp.json()
            code = result["choices"][0]["message"]["content"].strip()

            # 提取代码块
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            if "class " not in code or "def next" not in code:
                return None

            # 生成策略名
            import re
            m = re.search(r"class\s+(\w+Strategy)", code)
            name = m.group(1) if m else f"AI策略_{len(self.knowledge_base)+1}"

            kb = StrategyKnowledge(
                name=name,
                category="AI生成",
                source="AI/GLM-4-Flash",
                code=code,
                description=prompt,
                factors=["AI生成"],
                quality_score=60.0,
                learned_at=datetime.now().strftime("%Y-%m-%d"),
            )
            self.knowledge_base.append(kb)

            self.learning_log.append(LearningRecord(
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                action="learn",
                strategy=name,
                result="AI生成新策略",
                ai_insight=code[:200],
            ))
            self._save_data()
            return kb

        except Exception as e:
            logger.error(f"AI策略生成失败: {e}")
            return None

    def optimize_strategy(self, strategy_name: str, performance_data: Dict = None) -> Optional[StrategyKnowledge]:
        """用AI优化已有策略"""
        from config import ZHIPU_API_KEY
        import requests

        # 找到策略
        target = None
        for kb in self.knowledge_base:
            if kb.name == strategy_name:
                target = kb
                break

        if not target:
            return None

        perf_desc = ""
        if performance_data:
            perf_desc = f"""
当前策略表现:
- 总收益率: {performance_data.get('total_return', 'N/A')}
- 夏普比率: {performance_data.get('sharpe_ratio', 'N/A')}
- 最大回撤: {performance_data.get('max_drawdown', 'N/A')}
- 胜率: {performance_data.get('win_rate', 'N/A')}
"""

        prompt = f"""请优化以下量化策略。{perf_desc}
原始策略代码:
```python
{target.code}
```

请输出优化后的完整策略代码。优化方向:
1. 改善买卖信号的准确性
2. 添加更好的止损/止盈逻辑
3. 优化仓位管理
4. 减少不必要的交易（过滤假信号）

只输出优化后的完整Python代码。"""

        try:
            resp = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {ZHIPU_API_KEY}",
                },
                json={
                    "model": "glm-4-flash",
                    "messages": [
                        {"role": "system", "content": "你是量化策略优化专家。只输出优化后的代码。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.6,
                    "max_tokens": 4000,
                },
                timeout=60,
            )

            code = resp.json()["choices"][0]["message"]["content"].strip()
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            if "class " not in code:
                return None

            # 记录优化历史
            target.optimization_history.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "old_code_hash": hashlib.md5(target.code.encode()).hexdigest()[:8],
                "performance": performance_data,
            })

            target.code = code
            target.last_optimized = datetime.now().strftime("%Y-%m-%d")

            self.learning_log.append(LearningRecord(
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                action="optimize",
                strategy=strategy_name,
                result="AI优化策略",
                metrics=performance_data or {},
            ))
            self._save_data()
            return target

        except Exception as e:
            logger.error(f"策略优化失败: {e}")
            return None

    def get_best_strategies(self, top_n: int = 5) -> List[StrategyKnowledge]:
        """获取最优策略排名"""
        scored = []
        for kb in self.knowledge_base:
            score = kb.quality_score
            # 实盘表现加分
            if kb.real_trade_count > 0:
                score += kb.real_win_rate * 10
            scored.append((score, kb))
        scored.sort(key=lambda x: -x[0])
        return [kb for _, kb in scored[:top_n]]


# ═══════════════════════════════════════════════
# 持仓与收益跟踪
# ═══════════════════════════════════════════════

class PortfolioTracker:
    """持仓跟踪器"""

    def __init__(self):
        self.positions: List[Position] = []
        self.signals: List[TradeSignal] = []
        self.initial_cash: float = 100000.0
        self._load_data()

    def _load_data(self):
        """加载持久化数据（支持云存储）"""
        pf_data = _load_json_file(PORTFOLIO_FILE)
        if pf_data:
            self.positions = [Position(**d) for d in pf_data.get("positions", [])]
            self.initial_cash = pf_data.get("initial_cash", 100000.0)
        sig_data = _load_json_file(SIGNALS_FILE)
        if sig_data:
            self.signals = [TradeSignal(**d) for d in sig_data]

    def _save_data(self):
        """保存持久化数据（支持云存储）"""
        _save_json_file(PORTFOLIO_FILE, {
            "positions": [asdict(p) for p in self.positions],
            "initial_cash": self.initial_cash,
        })
        _save_json_file(SIGNALS_FILE, [asdict(s) for s in self.signals])

    def add_signal(self, signal: TradeSignal):
        """添加新信号"""
        self.signals.append(signal)
        self._save_data()

    def execute_buy(self, signal: TradeSignal, price: float = None):
        """执行买入"""
        exec_price = price or signal.price
        if exec_price <= 0:
            return False

        shares = int((self.initial_cash * 0.2) / exec_price / 100) * 100  # 20%仓位
        if shares <= 0:
            shares = 100  # 最少1手

        pos = Position(
            stock_code=signal.stock_code,
            stock_name=signal.stock_name,
            shares=shares,
            avg_cost=exec_price,
            current_price=exec_price,
            buy_date=datetime.now().strftime("%Y-%m-%d"),
            strategy_name=signal.strategy_name,
            signal_id=signal.id,
            stop_loss=signal.stop_loss,
            target_price=signal.target_price,
        )
        self.positions.append(pos)

        signal.status = "EXECUTED"
        signal.executed_price = exec_price
        self._save_data()
        return True

    def execute_sell(self, stock_code: str, price: float = None):
        """执行卖出"""
        for i, pos in enumerate(self.positions):
            if pos.stock_code == stock_code:
                sell_price = price or pos.current_price
                profit = round((sell_price - pos.avg_cost) / pos.avg_cost * 100, 2)

                # 更新对应信号
                for sig in self.signals:
                    if sig.id == pos.signal_id:
                        sig.status = "CLOSED"
                        sig.closed_price = sell_price
                        sig.profit_pct = profit
                        sig.closed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
                        break

                self.positions.pop(i)

                # 更新策略实盘统计
                from core.quant_brain import StrategyLearner
                learner = StrategyLearner()
                for kb in learner.knowledge_base:
                    if kb.name == pos.strategy_name:
                        kb.real_trade_count += 1
                        if profit > 0:
                            kb.real_win_rate = (
                                (kb.real_win_rate * (kb.real_trade_count - 1) + 100)
                                / kb.real_trade_count
                            )
                        kb.real_avg_profit = (
                            (kb.real_avg_profit * (kb.real_trade_count - 1) + profit)
                            / kb.real_trade_count
                        )
                learner._save_data()

                self._save_data()
                return profit
        return None

    def update_prices(self):
        """更新持仓最新价格（批量获取，减少BaoStock请求）"""
        codes = list(set(p.stock_code for p in self.positions))
        price_map = {}
        for code in codes:
            data = DataProvider.get_stock_daily(code, days=5)
            if not data.empty:
                price_map[code] = float(data.iloc[-1]["close"])
        for pos in self.positions:
            if pos.stock_code in price_map:
                pos.current_price = price_map[pos.stock_code]
        self._save_data()

    def get_summary(self) -> Dict:
        """获取持仓概要"""
        total_value = sum(p.market_value for p in self.positions)
        total_cost = sum(p.cost_basis for p in self.positions)
        cash = self.initial_cash - total_cost

        return {
            "initial_cash": self.initial_cash,
            "total_positions": len(self.positions),
            "total_market_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_profit": round(total_value - total_cost, 2),
            "total_profit_pct": round((total_value - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0,
            "available_cash": round(cash, 2),
            "positions": [asdict(p) for p in self.positions],
        }

    def get_recent_signals(self, n: int = 20) -> List[Dict]:
        """获取最近信号"""
        return [asdict(s) for s in self.signals[-n:]]

    def get_closed_trades(self) -> List[Dict]:
        """获取已平仓交易"""
        return [asdict(s) for s in self.signals if s.status == "CLOSED"]


# ═══════════════════════════════════════════════
# 主引擎 — QuantBrain
# ═══════════════════════════════════════════════

class QuantBrain:
    """量化大脑 — 统一入口"""

    def __init__(self):
        self.signal_gen = SignalGenerator()
        self.learner = StrategyLearner()
        self.portfolio = PortfolioTracker()
        self.data = DataProvider()

    def daily_scan(self, watch_list: List[str]) -> List[TradeSignal]:
        """每日扫描: 生成信号 → 筛选 → 推送"""
        signals = self.signal_gen.scan_stocks(watch_list)

        # 过滤低置信度
        quality_signals = [s for s in signals if s.confidence >= 60]

        # 保存所有信号
        for s in quality_signals:
            self.portfolio.add_signal(s)

        # 自动学习（用最新信号让AI学习）
        if quality_signals:
            self._auto_learn(quality_signals)

        return quality_signals

    def _auto_learn(self, signals: List[TradeSignal]):
        """自动学习：让AI分析信号质量并优化策略"""
        from config import ZHIPU_API_KEY
        import requests

        signal_summary = "\n".join([
            f"- {s.stock_code} {s.direction} (置信度{s.confidence}%) {s.reason}"
            for s in signals[:10]
        ])

        prompt = f"""分析以下A股交易信号的质量，并给出改进建议:

{signal_summary}

请简要分析:
1. 哪些信号质量较高？
2. 是否存在假信号风险？
3. 如何提高信号准确率？

用简洁的中文回答，100字以内。"""

        try:
            resp = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {ZHIPU_API_KEY}",
                },
                json={
                    "model": "glm-4-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30,
            )

            insight = resp.json()["choices"][0]["message"]["content"].strip()

            self.learner.learning_log.append(LearningRecord(
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                action="evaluate",
                strategy="多策略",
                result=f"分析了{len(signals)}个信号",
                ai_insight=insight,
            ))
            self.learner._save_data()

        except Exception as e:
            logger.warning(f"自动学习失败: {e}")

    def backtest_strategy_code(self, code: str, stock_code: str = "000001",
                                start_date: str = None, end_date: str = None) -> Dict:
        """回测策略代码"""
        from core.engine import BacktestEngine
        import backtrader as bt
        import importlib

        # 准备数据
        data = DataProvider.get_stock_daily(stock_code, start_date, end_date)
        if data.empty:
            return {"error": "无法获取股票数据"}

        data = DataProvider.calculate_indicators(data)

        # 动态加载策略
        namespace = {}
        try:
            exec(code, namespace)
        except Exception as e:
            return {"error": f"策略代码执行错误: {e}"}

        # 查找Strategy类
        strategy_class = None
        for name, obj in namespace.items():
            if isinstance(obj, type) and issubclass(obj, bt.Strategy) and obj is not bt.Strategy:
                strategy_class = obj
                break

        if not strategy_class:
            return {"error": "代码中未找到有效的bt.Strategy类"}

        # 执行回测
        try:
            engine = BacktestEngine(initial_cash=100000)
            result = engine.run(strategy_class, data)
            return result
        except Exception as e:
            return {"error": f"回测执行错误: {e}"}

    def get_watchlist_stocks(self) -> List[str]:
        """获取默认关注列表（沪深300成分股前50）"""
        cache_file = DATA_DIR / "watchlist.txt"
        if cache_file.exists():
            try:
                stocks = cache_file.read_text(encoding="utf-8").strip().split("\n")
                return [s.strip() for s in stocks if s.strip()]
            except:
                pass

        # 默认热门股
        defaults = [
            "000001", "000002", "000063", "000333", "000568", "000651", "000858",
            "002415", "002475", "002714", "002304", "002142",
            "300750", "300059", "300015", "300014",
            "600036", "600276", "600519", "600887", "600309",
            "601318", "601888", "601398", "601939", "601012",
            "603259", "603288",
        ]
        return defaults

    def save_watchlist(self, stocks: List[str]):
        """保存关注列表"""
        cache_file = DATA_DIR / "watchlist.txt"
        cache_file.write_text("\n".join(stocks), encoding="utf-8")

    def get_dashboard_data(self) -> Dict:
        """获取仪表盘所有数据"""
        portfolio = self.portfolio.get_summary()
        recent_signals = self.portfolio.get_recent_signals(20)
        closed_trades = self.portfolio.get_closed_trades()

        # 更新持仓价格
        self.portfolio.update_prices()
        portfolio = self.portfolio.get_summary()

        return {
            "portfolio": portfolio,
            "recent_signals": recent_signals,
            "closed_trades": closed_trades,
            "strategy_count": len(self.learner.knowledge_base),
            "best_strategies": [
                {"name": kb.name, "score": kb.quality_score,
                 "trades": kb.real_trade_count, "win_rate": kb.real_win_rate}
                for kb in self.learner.get_best_strategies(5)
            ],
            "learning_count": len(self.learner.learning_log),
            "recent_learning": [
                {"date": l.date, "action": l.action, "strategy": l.strategy, "result": l.result}
                for l in self.learner.learning_log[-10:]
            ],
        }
