"""
风险控制模块 (Risk Manager)

功能职责：
1. 止损止盈管理
2. 最大回撤控制
3. 波动率监控
4. 相关性风险控制
5. 仓位大小计算（基于风险）

支持的风险控制方法：
- 止损：固定止损、移动止损、ATR止损、波动率止损
- 仓位计算：固定风险、百分比风险、最优f值
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int
    avg_cost: float  # 平均成本
    current_price: float
    entry_time: datetime
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    metadata: Optional[Dict] = None


@dataclass
class Portfolio:
    """投资组合"""
    total_value: float  # 总市值
    cash: float  # 现金
    positions: Dict[str, Position]  # 持仓字典，key为symbol
    max_drawdown: float = 0.0  # 当前最大回撤
    peak_value: float = 0.0  # 峰值资产
    daily_pnl: float = 0.0  # 当日盈亏
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.peak_value == 0:
            self.peak_value = self.total_value


@dataclass
class MarketData:
    """市场数据"""
    symbol: str
    price: float  # 当前价格
    high: float  # 当日最高价
    low: float  # 当日最低价
    open: float  # 开盘价
    close: float  # 收盘价
    volume: float  # 成交量
    atr: Optional[float] = None  # 平均真实波幅
    volatility: Optional[float] = None  # 波动率
    beta: Optional[float] = None  # Beta系数
    timestamp: Optional[datetime] = None


@dataclass
class AccountInfo:
    """账户信息"""
    total_assets: float  # 总资产
    available_cash: float  # 可用现金
    total_positions_value: float  # 持仓总价值
    total_market_value: float  # 总市值
    total_pnl: float  # 总盈亏
    today_pnl: float  # 当日盈亏
    account_id: Optional[str] = None  # 账户ID
    broker: Optional[str] = None  # 券商
    timestamp: Optional[datetime] = None


@dataclass
class RiskParams:
    """风险参数"""
    max_drawdown_limit: float = 0.2  # 最大回撤限制（20%）
    max_position_risk: float = 0.02  # 单笔交易最大风险（2%）
    max_portfolio_risk: float = 0.1  # 组合最大风险（10%）
    stop_loss_width: float = 0.1  # 止损宽度（10%）
    take_profit_width: float = 0.2  # 止盈宽度（20%）
    trailing_stop_activation: float = 0.05  # 移动止损激活阈值（5%）
    trailing_stop_width: float = 0.03  # 移动止损宽度（3%）
    volatility_multiplier: float = 2.0  # 波动率乘数
    correlation_threshold: float = 0.7  # 相关性阈值


@dataclass
class RiskCheckResult:
    """风险检查结果"""
    stop_loss_triggered: bool = False
    take_profit_triggered: bool = False
    max_drawdown_breached: bool = False
    volatility_alert: bool = False
    correlation_alert: bool = False
    position_size_adjustment: Optional[float] = None  # 仓位调整建议（乘数）
    risk_score: float = 0.0  # 综合风险评分（0-1，越高越危险）
    alerts: List[str] = None  # 报警信息
    
    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []


@dataclass
class RiskAssessment:
    """风险评估结果"""
    is_approved: bool = True  # 是否通过风险评估
    risk_score: float = 0.0  # 风险分数，0-1，越高风险越大
    stop_loss_price: Optional[float] = None  # 建议止损价
    take_profit_price: Optional[float] = None  # 建议止盈价
    max_position_value: Optional[float] = None  # 最大仓位价值
    rejection_reason: Optional[str] = None  # 拒绝原因
    warnings: List[str] = None  # 警告信息
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class TradingSignal:
    """交易信号"""
    symbol: str
    direction: str  # "buy", "sell", "hold"
    strength: float  # 信号强度，0-1
    confidence: float  # 置信度，0-1
    timestamp: datetime
    price: Optional[float] = None
    expected_return: Optional[float] = None  # 预期收益率
    win_rate: Optional[float] = None  # 胜率估计
    profit_loss_ratio: Optional[float] = None  # 盈亏比


class RiskManager:
    """风险控制器"""
    
    def __init__(self, config: Dict):
        """
        初始化风险控制器
        
        Args:
            config: 配置字典，包含：
                - stop_loss_method: 止损方法（fixed/trailing/atr/volatility）
                - position_sizing_method: 仓位计算方法（fixed_risk/percent_risk/optimal_f）
                - risk_params: RiskParams参数
                - max_correlation: 最大允许相关性（默认0.7）
                - volatility_threshold: 波动率阈值（默认0.3）
                - enable_circuit_breaker: 是否启用熔断机制
        """
        self.config = config
        
        # 止损方法映射
        self.stop_loss_methods = {
            "fixed": self._fixed_stop_loss,
            "trailing": self._trailing_stop_loss,
            "atr": self._atr_stop_loss,
            "volatility": self._volatility_stop_loss
        }
        
        # 仓位计算方法映射
        self.position_sizing_methods = {
            "fixed_risk": self._fixed_risk_sizing,
            "percent_risk": self._percent_risk_sizing,
            "optimal_f": self._optimal_f_sizing
        }
        
        # 风险参数
        self.risk_params = RiskParams(**config.get("risk_params", {}))
        
        # 历史数据存储
        self.price_history = defaultdict(list)
        self.performance_history = []
        
        # 熔断状态
        self.circuit_breaker_state = "normal"  # normal/mild/severe
        self.circuit_breaker_triggers = []
        
        logger.info(f"风险控制器初始化完成，止损方法: {config.get('stop_loss_method', 'fixed')}")
    
    def check_risk(self, position: Position, 
                   market_data: MarketData,
                   portfolio: Portfolio) -> RiskCheckResult:
        """
        检查风险并返回调整建议
        
        Args:
            position: 持仓信息
            market_data: 市场数据
            portfolio: 投资组合
            
        Returns:
            RiskCheckResult: 风险检查结果
        """
        result = RiskCheckResult()
        
        # 检查止损
        result.stop_loss_triggered = self._check_stop_loss(position, market_data)
        if result.stop_loss_triggered:
            result.alerts.append(f"止损触发: {position.symbol} 当前价{market_data.price:.2f} <= 止损价{position.stop_loss_price:.2f}")
        
        # 检查止盈
        result.take_profit_triggered = self._check_take_profit(position, market_data)
        if result.take_profit_triggered:
            result.alerts.append(f"止盈触发: {position.symbol} 当前价{market_data.price:.2f} >= 止盈价{position.take_profit_price:.2f}")
        
        # 检查组合风险
        portfolio_risk = self._check_portfolio_risk(portfolio, market_data)
        result.max_drawdown_breached = portfolio_risk["max_drawdown_breached"]
        result.volatility_alert = portfolio_risk["volatility_alert"]
        
        if result.max_drawdown_breached:
            result.alerts.append(f"最大回撤超限: 当前回撤{portfolio.max_drawdown:.2%} > 限制{self.risk_params.max_drawdown_limit:.2%}")
        
        if result.volatility_alert:
            result.alerts.append(f"波动率警报: 组合波动率过高")
        
        # 检查相关性风险（需要多只股票数据，这里简化）
        # result.correlation_alert = self._check_correlation_risk(portfolio)
        
        # 计算综合风险评分
        result.risk_score = self._calculate_overall_risk_score(
            position, market_data, portfolio, result
        )
        
        # 根据风险评分建议仓位调整
        if result.risk_score > 0.7:
            result.position_size_adjustment = 0.5  # 高风险，减半仓位
            result.alerts.append(f"高风险警报: 风险评分{result.risk_score:.2f}，建议减半仓位")
        elif result.risk_score > 0.5:
            result.position_size_adjustment = 0.8  # 中等风险，减少20%仓位
            result.alerts.append(f"中等风险警报: 风险评分{result.risk_score:.2f}，建议减少20%仓位")
        
        # 检查熔断条件
        circuit_check = self._check_circuit_breaker(portfolio, result)
        if circuit_check["triggered"]:
            result.alerts.append(f"熔断触发: {circuit_check['level']}级熔断 - {circuit_check['reason']}")
        
        return result
    
    def calculate_position_size(self, signal: TradingSignal,
                               account_cash: float,
                               risk_params: Optional[RiskParams] = None) -> float:
        """
        基于风险计算仓位大小
        
        Args:
            signal: 交易信号
            account_cash: 账户可用现金
            risk_params: 风险参数（如为None则使用默认）
            
        Returns:
            float: 建议交易金额
        """
        if risk_params is None:
            risk_params = self.risk_params
        
        method = self.config.get("position_sizing_method", "fixed_risk")
        sizing_func = self.position_sizing_methods[method]
        
        try:
            position_value = sizing_func(signal, account_cash, risk_params)
            
            # 应用限制：不超过可用现金的80%
            max_position = account_cash * 0.8
            position_value = min(position_value, max_position)
            
            # 确保不低于最小交易金额（假设1000元）
            min_trade_value = 1000
            if position_value < min_trade_value:
                logger.warning(f"计算仓位{position_value:.2f}低于最小交易金额{min_trade_value}，调整为最小交易")
                position_value = min_trade_value
            
            logger.info(f"风险仓位计算完成: {signal.symbol} {signal.direction} "
                       f"建议金额{position_value:.2f}元，算法: {method}")
            
            return position_value
            
        except Exception as e:
            logger.error(f"风险仓位计算失败: {e}")
            # 失败时返回保守仓位（可用现金的5%）
            return account_cash * 0.05
    
    def calculate_stop_loss_take_profit(self, entry_price: float,
                                       signal: TradingSignal,
                                       market_data: MarketData) -> Tuple[float, float]:
        """
        计算止损止盈价格
        
        Args:
            entry_price: 入场价格
            signal: 交易信号
            market_data: 市场数据
            
        Returns:
            Tuple[float, float]: (stop_loss_price, take_profit_price)
        """
        method = self.config.get("stop_loss_method", "fixed")
        stop_loss_func = self.stop_loss_methods[method]
        
        stop_loss_price = stop_loss_func(entry_price, signal, market_data)
        
        # 计算止盈价格（固定比例）
        if signal.direction == "buy":
            take_profit_price = entry_price * (1 + self.risk_params.take_profit_width)
        else:  # sell/short
            take_profit_price = entry_price * (1 - self.risk_params.take_profit_width)
        
        return stop_loss_price, take_profit_price
    
    def _fixed_stop_loss(self, entry_price: float,
                        signal: TradingSignal,
                        market_data: MarketData) -> float:
        """固定止损"""
        if signal.direction == "buy":
            return entry_price * (1 - self.risk_params.stop_loss_width)
        else:  # sell/short
            return entry_price * (1 + self.risk_params.stop_loss_width)
    
    def _trailing_stop_loss(self, entry_price: float,
                           signal: TradingSignal,
                           market_data: MarketData) -> float:
        """移动止损"""
        # 这里简化：实际需要跟踪最高/最低价
        # 使用当前价格计算
        current_price = market_data.price
        
        if signal.direction == "buy":
            # 买入：从最高点回落一定比例止损
            # 这里用entry_price作为初始最高价
            highest_price = max(entry_price, current_price)
            
            # 检查是否达到激活阈值
            if highest_price >= entry_price * (1 + self.risk_params.trailing_stop_activation):
                # 激活移动止损：从最高点回落trailing_stop_width
                return highest_price * (1 - self.risk_params.trailing_stop_width)
            else:
                # 未激活，使用固定止损
                return entry_price * (1 - self.risk_params.stop_loss_width)
        else:  # sell/short
            # 卖出：从最低点回升一定比例止损
            lowest_price = min(entry_price, current_price)
            
            if lowest_price <= entry_price * (1 - self.risk_params.trailing_stop_activation):
                return lowest_price * (1 + self.risk_params.trailing_stop_width)
            else:
                return entry_price * (1 + self.risk_params.stop_loss_width)
    
    def _atr_stop_loss(self, entry_price: float,
                      signal: TradingSignal,
                      market_data: MarketData) -> float:
        """ATR止损"""
        if market_data.atr is None:
            # 如果没有ATR数据，回退到固定止损
            return self._fixed_stop_loss(entry_price, signal, market_data)
        
        atr = market_data.atr
        atr_multiplier = self.config.get("atr_multiplier", 2.0)
        
        if signal.direction == "buy":
            return entry_price - atr * atr_multiplier
        else:  # sell/short
            return entry_price + atr * atr_multiplier
    
    def _volatility_stop_loss(self, entry_price: float,
                             signal: TradingSignal,
                             market_data: MarketData) -> float:
        """波动率止损"""
        if market_data.volatility is None:
            # 如果没有波动率数据，回退到固定止损
            return self._fixed_stop_loss(entry_price, signal, market_data)
        
        volatility = market_data.volatility
        volatility_multiplier = self.config.get("volatility_multiplier", 2.0)
        
        # 计算基于波动率的止损宽度
        stop_loss_width = volatility * volatility_multiplier
        
        if signal.direction == "buy":
            return entry_price * (1 - stop_loss_width)
        else:  # sell/short
            return entry_price * (1 + stop_loss_width)
    
    def _fixed_risk_sizing(self, signal: TradingSignal,
                          account_cash: float,
                          risk_params: RiskParams) -> float:
        """固定风险仓位计算"""
        # 单笔交易最大风险金额
        max_risk_per_trade = account_cash * risk_params.max_position_risk
        
        # 估计每单位风险（这里简化：使用信号强度作为风险估计）
        risk_per_unit = 1.0 - signal.strength  # 信号越强，风险越低
        
        # 计算仓位：最大风险金额 / 每单位风险
        if risk_per_unit > 0:
            position_value = max_risk_per_trade / risk_per_unit
        else:
            position_value = max_risk_per_trade * 2  # 零风险时给双倍仓位
        
        # 应用信号强度调整
        position_value = position_value * signal.strength
        
        return position_value
    
    def _percent_risk_sizing(self, signal: TradingSignal,
                            account_cash: float,
                            risk_params: RiskParams) -> float:
        """百分比风险仓位计算"""
        # 直接使用账户固定百分比
        position_percent = risk_params.max_position_risk * signal.strength * 2  # 基础2倍
        
        # 限制在合理范围（1%-20%）
        position_percent = max(0.01, min(position_percent, 0.2))
        
        position_value = account_cash * position_percent
        
        return position_value
    
    def _optimal_f_sizing(self, signal: TradingSignal,
                         account_cash: float,
                         risk_params: RiskParams) -> float:
        """最优f值仓位计算（凯利公式变体）"""
        # 需要胜率和盈亏比数据
        win_rate = signal.win_rate or 0.5  # 默认50%胜率
        profit_loss_ratio = signal.profit_loss_ratio or 1.5  # 默认1.5盈亏比
        
        # 凯利公式：f* = (bp - q) / b
        # 其中：b = 盈亏比，p = 胜率，q = 1-p
        b = profit_loss_ratio
        p = win_rate
        q = 1 - p
        
        if b > 0:
            kelly_fraction = (b * p - q) / b
        else:
            kelly_fraction = 0
        
        # 应用半凯利或其他保守系数
        conservative_factor = 0.5  # 半凯利
        kelly_fraction = max(0, min(kelly_fraction * conservative_factor, 0.25))  # 最大25%
        
        # 应用信号强度调整
        kelly_fraction = kelly_fraction * signal.strength
        
        position_value = account_cash * kelly_fraction
        
        return position_value
    
    def _check_stop_loss(self, position: Position,
                        market_data: MarketData) -> bool:
        """检查止损是否触发"""
        if position.stop_loss_price is None:
            return False
        
        if position.quantity > 0:  # 多头持仓
            return market_data.price <= position.stop_loss_price
        else:  # 空头持仓
            return market_data.price >= position.stop_loss_price
    
    def _check_take_profit(self, position: Position,
                          market_data: MarketData) -> bool:
        """检查止盈是否触发"""
        if position.take_profit_price is None:
            return False
        
        if position.quantity > 0:  # 多头持仓
            return market_data.price >= position.take_profit_price
        else:  # 空头持仓
            return market_data.price <= position.take_profit_price
    
    def _check_portfolio_risk(self, portfolio: Portfolio,
                             market_data: MarketData) -> Dict:
        """检查组合风险"""
        result = {
            "max_drawdown_breached": False,
            "volatility_alert": False
        }
        
        # 更新峰值和回撤
        if portfolio.total_value > portfolio.peak_value:
            portfolio.peak_value = portfolio.total_value
        
        # 计算当前回撤
        if portfolio.peak_value > 0:
            current_drawdown = (portfolio.peak_value - portfolio.total_value) / portfolio.peak_value
            portfolio.max_drawdown = max(portfolio.max_drawdown, current_drawdown)
            
            # 检查是否超过限制
            if current_drawdown > self.risk_params.max_drawdown_limit:
                result["max_drawdown_breached"] = True
        
        # 检查波动率（这里简化：使用价格变化作为波动率代理）
        # 实际应用中应该计算历史波动率
        price_change = abs(market_data.close - market_data.open) / market_data.open
        if price_change > 0.05:  # 单日涨跌幅超过5%
            result["volatility_alert"] = True
        
        return result
    
    def _check_correlation_risk(self, portfolio: Portfolio) -> bool:
        """检查相关性风险（需要多只股票的历史数据）"""
        # 这里简化实现
        # 实际应用中需要计算组合内股票的相关性矩阵
        # 如果相关性过高，则存在集中风险
        
        if len(portfolio.positions) < 2:
            return False  # 单只股票无相关性风险
        
        # 简单检查：如果持仓集中在同一行业，则风险较高
        # 这里假设metadata中有行业信息
        industries = []
        for position in portfolio.positions.values():
            if position.metadata and "industry" in position.metadata:
                industries.append(position.metadata["industry"])
        
        # 如果超过50%的持仓在同一行业，则报警
        if industries:
            from collections import Counter
            industry_counts = Counter(industries)
            most_common_count = industry_counts.most_common(1)[0][1]
            
            if most_common_count / len(industries) > 0.5:
                return True
        
        return False
    
    def _calculate_overall_risk_score(self, position: Position,
                                     market_data: MarketData,
                                     portfolio: Portfolio,
                                     risk_check: RiskCheckResult) -> float:
        """计算综合风险评分（0-1，越高越危险）"""
        risk_factors = []
        weights = []
        
        # 1. 止损距离风险（离止损价越近风险越高）
        if position.stop_loss_price is not None:
            if position.quantity > 0:  # 多头
                stop_distance = (market_data.price - position.stop_loss_price) / market_data.price
            else:  # 空头
                stop_distance = (position.stop_loss_price - market_data.price) / market_data.price
            
            # 归一化到0-1：距离越小风险越高
            stop_risk = max(0, 1 - stop_distance / 0.1)  # 假设10%是正常止损距离
            risk_factors.append(stop_risk)
            weights.append(0.3)
        
        # 2. 仓位集中度风险
        if position.quantity > 0:
            position_value = position.quantity * market_data.price
            concentration = position_value / portfolio.total_value if portfolio.total_value > 0 else 0
            concentration_risk = min(concentration * 5, 1.0)  # 20%仓位对应风险1.0
            risk_factors.append(concentration_risk)
            weights.append(0.25)
        
        # 3. 组合回撤风险
        if portfolio.peak_value > 0:
            current_drawdown = (portfolio.peak_value - portfolio.total_value) / portfolio.peak_value
            drawdown_risk = min(current_drawdown / self.risk_params.max_drawdown_limit, 1.0)
            risk_factors.append(drawdown_risk)
            weights.append(0.25)
        
        # 4. 市场波动率风险
        if market_data.volatility is not None:
            volatility_risk = min(market_data.volatility / 0.3, 1.0)  # 30%波动率对应风险1.0
            risk_factors.append(volatility_risk)
            weights.append(0.2)
        
        # 计算加权平均风险
        if risk_factors and weights:
            total_weight = sum(weights[:len(risk_factors)])
            if total_weight > 0:
                weighted_risk = sum(r * w for r, w in zip(risk_factors, weights)) / total_weight
                return min(max(weighted_risk, 0), 1)
        
        return 0.5  # 默认中等风险
    
    def _check_circuit_breaker(self, portfolio: Portfolio,
                              risk_check: RiskCheckResult) -> Dict:
        """检查熔断条件"""
        result = {
            "triggered": False,
            "level": "normal",
            "reason": ""
        }
        
        # 轻度熔断条件：单日亏损超过5%
        if portfolio.daily_pnl < -portfolio.total_value * 0.05:
            result["triggered"] = True
            result["level"] = "mild"
            result["reason"] = f"单日亏损{abs(portfolio.daily_pnl/portfolio.total_value):.2%}超过5%"
            self.circuit_breaker_state = "mild"
            self.circuit_breaker_triggers.append(result.copy())
        
        # 中度熔断条件：最大回撤超过15%
        elif portfolio.max_drawdown > 0.15:
            result["triggered"] = True
            result["level"] = "moderate"
            result["reason"] = f"最大回撤{portfolio.max_drawdown:.2%}超过15%"
            self.circuit_breaker_state = "moderate"
            self.circuit_breaker_triggers.append(result.copy())
        
        # 重度熔断条件：最大回撤超过25%或连续3次触发轻度熔断
        elif (portfolio.max_drawdown > 0.25 or 
              len([t for t in self.circuit_breaker_triggers[-3:] if t["level"] == "mild"]) >= 3):
            result["triggered"] = True
            result["level"] = "severe"
            result["reason"] = f"最大回撤{portfolio.max_drawdown:.2%}超过25%或连续触发轻度熔断"
            self.circuit_breaker_state = "severe"
            self.circuit_breaker_triggers.append(result.copy())
        
        return result
    
    def get_circuit_breaker_action(self) -> str:
        """获取熔断措施"""
        if self.circuit_breaker_state == "mild":
            return "暂停新开仓，允许平仓"
        elif self.circuit_breaker_state == "moderate":
            return "强制平仓50%仓位"
        elif self.circuit_breaker_state == "severe":
            return "全部平仓，停止交易"
        else:
            return "正常交易"


# 测试函数
def test_risk_manager():
    """测试风险控制器"""
    print("=== 测试风险控制器 ===")
    
    # 创建配置
    config = {
        "stop_loss_method": "fixed",
        "position_sizing_method": "fixed_risk",
        "risk_params": {
            "max_drawdown_limit": 0.2,
            "max_position_risk": 0.02,
            "stop_loss_width": 0.1,
            "take_profit_width": 0.2,
            "trailing_stop_activation": 0.05,
            "trailing_stop_width": 0.03
        },
        "max_correlation": 0.7,
        "volatility_threshold": 0.3,
        "enable_circuit_breaker": True
    }
    
    # 创建风险控制器
    rm = RiskManager(config)
    
    # 创建测试数据
    from datetime import datetime
    
    # 交易信号
    signal = TradingSignal(
        symbol="000001.SZ",
        direction="buy",
        strength=0.8,
        confidence=0.7,
        timestamp=datetime.now(),
        price=10.5,
        expected_return=0.15,
        win_rate=0.6,
        profit_loss_ratio=1.8
    )
    
    # 持仓
    position = Position(
        symbol="000001.SZ",
        quantity=1000,
        avg_cost=10.0,
        current_price=10.5,
        entry_time=datetime.now(),
        stop_loss_price=9.0,
        take_profit_price=12.0,
        metadata={"industry": "银行"}
    )
    
    # 市场数据
    market_data = MarketData(
        symbol="000001.SZ",
        price=10.5,
        high=11.0,
        low=10.0,
        open=10.2,
        close=10.5,
        volume=1000000,
        atr=0.3,
        volatility=0.15,
        beta=1.2,
        timestamp=datetime.now()
    )
    
    # 投资组合
    portfolio = Portfolio(
        total_value=150000,
        cash=50000,
        positions={"000001.SZ": position},
        max_drawdown=0.05,
        peak_value=160000,
        daily_pnl=-2000
    )
    
    print("\n--- 测试风险检查 ---")
    risk_result = rm.check_risk(position, market_data, portfolio)
    
    print(f"止损触发: {risk_result.stop_loss_triggered}")
    print(f"止盈触发: {risk_result.take_profit_triggered}")
    print(f"最大回撤超限: {risk_result.max_drawdown_breached}")
    print(f"波动率警报: {risk_result.volatility_alert}")
    print(f"风险评分: {risk_result.risk_score:.3f}")
    print(f"仓位调整建议: {risk_result.position_size_adjustment}")
    
    if risk_result.alerts:
        print("报警信息:")
        for alert in risk_result.alerts:
            print(f"  - {alert}")
    
    print("\n--- 测试仓位计算 ---")
    account_cash = 100000
    position_value = rm.calculate_position_size(signal, account_cash)
    print(f"建议交易金额: {position_value:.2f}元")
    
    print("\n--- 测试止损止盈计算 ---")
    entry_price = 10.0
    stop_loss, take_profit = rm.calculate_stop_loss_take_profit(
        entry_price, signal, market_data
    )
    print(f"止损价: {stop_loss:.2f}")
    print(f"止盈价: {take_profit:.2f}")
    
    print("\n--- 测试不同止损方法 ---")
    stop_methods = ["fixed", "trailing", "atr", "volatility"]
    
    for method in stop_methods:
        config["stop_loss_method"] = method
        rm = RiskManager(config)
        
        stop_loss, take_profit = rm.calculate_stop_loss_take_profit(
            entry_price, signal, market_data
        )
        print(f"{method}止损: {stop_loss:.2f}, 止盈: {take_profit:.2f}")
    
    print("\n--- 测试不同仓位计算方法 ---")
    sizing_methods = ["fixed_risk", "percent_risk", "optimal_f"]
    
    for method in sizing_methods:
        config["position_sizing_method"] = method
        rm = RiskManager(config)
        
        position_value = rm.calculate_position_size(signal, account_cash)
        print(f"{method}仓位: {position_value:.2f}元")
    
    print("\n--- 测试熔断机制 ---")
    # 模拟触发熔断
    portfolio.daily_pnl = -10000  # 单日亏损10%
    risk_result = rm.check_risk(position, market_data, portfolio)
    
    if risk_result.alerts:
        for alert in risk_result.alerts:
            if "熔断" in alert:
                print(f"熔断测试: {alert}")
                print(f"熔断措施: {rm.get_circuit_breaker_action()}")


if __name__ == "__main__":
    test_risk_manager()