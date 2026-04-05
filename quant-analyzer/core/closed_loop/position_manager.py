"""
仓位管理模块 (Position Manager)

功能职责：
1. 根据策略信号计算具体仓位
2. 管理多种仓位分配算法
3. 处理加仓/减仓逻辑
4. 监控持仓风险

支持的仓位算法：
- fixed: 固定仓位
- kelly: 凯利公式仓位
- volatility: 波动率调整仓位
- risk_parity: 风险平价
- pyramid: 金字塔加仓
- grid: 网格交易
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """交易信号"""
    symbol: str
    direction: str  # "buy", "sell", "hold"
    strength: float  # 信号强度，0-1
    confidence: float  # 置信度，0-1
    timestamp: datetime
    price: Optional[float] = None  # 当前价格
    volume: Optional[float] = None  # 成交量
    factor_scores: Optional[Dict[str, float]] = None  # 因子得分


@dataclass
class AccountInfo:
    """账户信息"""
    total_assets: float  # 总资产
    available_cash: float  # 可用现金
    market_value: float  # 持仓市值
    margin_available: Optional[float] = None  # 可用保证金
    risk_tolerance: float = 0.02  # 风险容忍度（单笔交易最大亏损比例）


@dataclass
class MarketData:
    """市场数据"""
    symbol: str
    price: float  # 当前价格
    volume: float  # 成交量
    high: float  # 当日最高价
    low: float  # 当日最低价
    open: float  # 开盘价
    close: float  # 收盘价
    vwap: Optional[float] = None  # 成交量加权平均价
    atr: Optional[float] = None  # 平均真实波幅
    volatility: Optional[float] = None  # 波动率
    beta: Optional[float] = None  # Beta系数


@dataclass
class PositionDecision:
    """仓位决策"""
    symbol: str
    action: str  # "buy", "sell", "hold"
    quantity: int  # 交易数量
    price: float  # 建议价格
    value: float  # 交易金额
    position_method: str  # 使用的仓位算法
    risk_score: float  # 风险评分（0-1，越低越好）
    timestamp: datetime
    metadata: Optional[Dict] = None  # 额外信息


class PositionManager:
    """仓位管理器"""
    
    def __init__(self, config: Dict):
        """
        初始化仓位管理器
        
        Args:
            config: 配置字典，包含：
                - position_method: 仓位算法（默认"fixed"）
                - fixed_position_size: 固定仓位大小（默认0.1，即10%）
                - max_position_per_stock: 单只股票最大仓位（默认0.2，即20%）
                - min_trade_value: 最小交易金额（默认1000）
                - kelly_fraction: 凯利公式分数（默认0.5，即半凯利）
                - atr_multiplier: ATR乘数（默认2.0）
                - grid_levels: 网格交易层数（默认5）
                - pyramid_levels: 金字塔层数（默认3）
        """
        self.config = config
        
        # 仓位算法映射
        self.position_methods = {
            "fixed": self._fixed_position,
            "kelly": self._kelly_position,
            "volatility": self._volatility_adjusted,
            "risk_parity": self._risk_parity,
            "pyramid": self._pyramid_position,
            "grid": self._grid_trading
        }
        
        # 验证配置
        self._validate_config()
        
        logger.info(f"仓位管理器初始化完成，使用算法: {config.get('position_method', 'fixed')}")
    
    def _validate_config(self):
        """验证配置"""
        method = self.config.get("position_method", "fixed")
        if method not in self.position_methods:
            raise ValueError(f"不支持的仓位算法: {method}，支持的算法: {list(self.position_methods.keys())}")
    
    def calculate_position(self, signal: TradingSignal, 
                          account_info: AccountInfo,
                          market_data: MarketData) -> PositionDecision:
        """
        计算具体仓位
        
        Args:
            signal: 交易信号
            account_info: 账户信息
            market_data: 市场数据
            
        Returns:
            PositionDecision: 仓位决策
        """
        # 检查信号有效性
        if signal.direction == "hold":
            return self._create_hold_decision(signal, market_data)
        
        # 获取仓位算法
        method = self.config.get("position_method", "fixed")
        position_func = self.position_methods[method]
        
        # 计算仓位
        try:
            decision = position_func(signal, account_info, market_data)
            
            # 应用风险限制
            decision = self._apply_risk_limits(decision, account_info, market_data)
            
            # 计算风险评分
            decision.risk_score = self._calculate_risk_score(decision, account_info, market_data, signal)
            
            logger.info(f"仓位计算完成: {signal.symbol} {decision.action} {decision.quantity}股 "
                       f"({decision.value:.2f}元)，算法: {method}，风险评分: {decision.risk_score:.3f}")
            
            return decision
            
        except Exception as e:
            logger.error(f"仓位计算失败: {e}")
            # 失败时返回hold决策
            return self._create_hold_decision(signal, market_data, error=str(e))
    
    def _fixed_position(self, signal: TradingSignal, 
                       account_info: AccountInfo,
                       market_data: MarketData) -> PositionDecision:
        """
        固定仓位算法
        
        每次交易固定比例的资金
        """
        # 获取配置参数
        position_size = self.config.get("fixed_position_size", 0.1)  # 默认10%
        min_trade_value = self.config.get("min_trade_value", 1000)
        
        # 计算交易金额
        trade_value = account_info.total_assets * position_size * signal.strength
        
        # 确保不低于最小交易金额
        trade_value = max(trade_value, min_trade_value)
        
        # 计算交易数量（向下取整到100的倍数）
        quantity = int(trade_value // market_data.price // 100) * 100
        
        # 确保至少交易100股
        quantity = max(quantity, 100)
        
        # 计算实际交易金额
        actual_value = quantity * market_data.price
        
        return PositionDecision(
            symbol=signal.symbol,
            action=signal.direction,
            quantity=quantity,
            price=market_data.price,
            value=actual_value,
            position_method="fixed",
            risk_score=0.5,  # 临时值，后面会重新计算
            timestamp=datetime.now(),
            metadata={
                "position_size": position_size,
                "signal_strength": signal.strength,
                "calculated_value": trade_value,
                "actual_value": actual_value
            }
        )
    
    def _kelly_position(self, signal: TradingSignal,
                       account_info: AccountInfo,
                       market_data: MarketData) -> PositionDecision:
        """
        凯利公式仓位算法
        
        基于胜率和赔率计算最优仓位
        f* = (bp - q) / b
        其中：
        - b: 赔率（盈利/亏损）
        - p: 胜率
        - q: 败率 = 1 - p
        """
        # 获取配置参数
        kelly_fraction = self.config.get("kelly_fraction", 0.5)  # 半凯利
        min_trade_value = self.config.get("min_trade_value", 1000)
        
        # 估计胜率和赔率（这里简化处理，实际应从历史数据计算）
        # 使用信号强度和置信度估计胜率
        win_rate = signal.confidence * 0.7 + 0.3  # 基础胜率30%，加上信号置信度调整
        
        # 估计赔率（盈利/亏损比例）
        # 使用信号强度估计赔率，强信号通常有更高赔率
        odds_ratio = 1.5 + signal.strength * 1.5  # 赔率在1.5-3.0之间
        
        # 计算凯利公式
        b = odds_ratio - 1  # 净赔率
        p = win_rate
        q = 1 - p
        
        # 凯利公式：f* = (bp - q) / b
        if b > 0:
            kelly_fraction_raw = (b * p - q) / b
        else:
            kelly_fraction_raw = 0
        
        # 应用凯利分数限制（避免过度杠杆）
        kelly_fraction_raw = max(0, min(kelly_fraction_raw, 0.25))  # 最大25%
        
        # 应用半凯利或其他分数
        position_size = kelly_fraction_raw * kelly_fraction
        
        # 计算交易金额
        trade_value = account_info.total_assets * position_size
        
        # 确保不低于最小交易金额
        trade_value = max(trade_value, min_trade_value)
        
        # 计算交易数量
        quantity = int(trade_value // market_data.price // 100) * 100
        quantity = max(quantity, 100)
        
        actual_value = quantity * market_data.price
        
        return PositionDecision(
            symbol=signal.symbol,
            action=signal.direction,
            quantity=quantity,
            price=market_data.price,
            value=actual_value,
            position_method="kelly",
            risk_score=0.5,
            timestamp=datetime.now(),
            metadata={
                "win_rate": win_rate,
                "odds_ratio": odds_ratio,
                "kelly_fraction_raw": kelly_fraction_raw,
                "kelly_fraction_applied": kelly_fraction,
                "position_size": position_size,
                "calculated_value": trade_value
            }
        )
    
    def _volatility_adjusted(self, signal: TradingSignal,
                           account_info: AccountInfo,
                           market_data: MarketData) -> PositionDecision:
        """
        波动率调整仓位算法
        
        基于波动率（ATR或历史波动率）调整仓位
        波动率越高，仓位越小
        """
        min_trade_value = self.config.get("min_trade_value", 1000)
        atr_multiplier = self.config.get("atr_multiplier", 2.0)
        
        # 获取波动率数据
        if market_data.atr is not None:
            volatility = market_data.atr
        elif market_data.volatility is not None:
            volatility = market_data.volatility
        else:
            # 如果没有波动率数据，使用价格范围的10%作为估计
            volatility = (market_data.high - market_data.low) * 0.1
        
        # 计算波动率调整因子
        # 基础波动率参考：假设正常波动率为价格的2%
        normal_volatility = market_data.price * 0.02
        
        if volatility > 0:
            volatility_ratio = normal_volatility / volatility
        else:
            volatility_ratio = 1.0
        
        # 限制波动率调整因子范围
        volatility_ratio = max(0.5, min(volatility_ratio, 2.0))
        
        # 基础仓位大小
        base_position = 0.1  # 10%
        
        # 应用波动率调整
        position_size = base_position * volatility_ratio * signal.strength
        
        # 计算交易金额
        trade_value = account_info.total_assets * position_size
        
        # 确保不低于最小交易金额
        trade_value = max(trade_value, min_trade_value)
        
        # 计算交易数量
        quantity = int(trade_value // market_data.price // 100) * 100
        quantity = max(quantity, 100)
        
        actual_value = quantity * market_data.price
        
        return PositionDecision(
            symbol=signal.symbol,
            action=signal.direction,
            quantity=quantity,
            price=market_data.price,
            value=actual_value,
            position_method="volatility",
            risk_score=0.5,
            timestamp=datetime.now(),
            metadata={
                "volatility": volatility,
                "normal_volatility": normal_volatility,
                "volatility_ratio": volatility_ratio,
                "position_size": position_size,
                "atr_multiplier": atr_multiplier,
                "calculated_value": trade_value
            }
        )
    
    def _risk_parity(self, signal: TradingSignal,
                    account_info: AccountInfo,
                    market_data: MarketData) -> PositionDecision:
        """
        风险平价算法
        
        等风险贡献原则
        """
        min_trade_value = self.config.get("min_trade_value", 1000)
        
        # 估计风险贡献（这里简化处理）
        # 使用波动率和Beta估计风险
        volatility = market_data.volatility or (market_data.high - market_data.low) / market_data.price
        beta = market_data.beta or 1.0
        
        # 风险贡献 = 波动率 * Beta
        risk_contribution = volatility * beta
        
        # 基础风险预算（假设总风险预算为1）
        # 这里简化：每只股票分配相等的风险预算
        # 实际应用中需要知道组合中其他股票的风险
        risk_budget = 0.1  # 10%的风险预算
        
        # 计算仓位：风险预算 / 风险贡献
        if risk_contribution > 0:
            position_size = risk_budget / risk_contribution
        else:
            position_size = 0.1  # 默认10%
        
        # 限制仓位大小
        position_size = max(0.05, min(position_size, 0.2))  # 5%-20%
        
        # 应用信号强度
        position_size = position_size * signal.strength
        
        # 计算交易金额
        trade_value = account_info.total_assets * position_size
        
        # 确保不低于最小交易金额
        trade_value = max(trade_value, min_trade_value)
        
        # 计算交易数量
        quantity = int(trade_value // market_data.price // 100) * 100
        quantity = max(quantity, 100)
        
        actual_value = quantity * market_data.price
        
        return PositionDecision(
            symbol=signal.symbol,
            action=signal.direction,
            quantity=quantity,
            price=market_data.price,
            value=actual_value,
            position_method="risk_parity",
            risk_score=0.5,
            timestamp=datetime.now(),
            metadata={
                "volatility": volatility,
                "beta": beta,
                "risk_contribution": risk_contribution,
                "risk_budget": risk_budget,
                "position_size": position_size,
                "calculated_value": trade_value
            }
        )
    
    def _pyramid_position(self, signal: TradingSignal,
                         account_info: AccountInfo,
                         market_data: MarketData) -> PositionDecision:
        """
        金字塔加仓算法
        
        盈利加仓策略：随着价格上涨，逐步减少加仓量
        """
        min_trade_value = self.config.get("min_trade_value", 1000)
        pyramid_levels = self.config.get("pyramid_levels", 3)
        
        # 金字塔加仓：每层仓位递减
        # 例如：第一层40%，第二层30%，第三层20%，第四层10%
        level_weights = []
        total_weight = 0
        
        for i in range(pyramid_levels):
            weight = (pyramid_levels - i) / sum(range(1, pyramid_levels + 1))
            level_weights.append(weight)
            total_weight += weight
        
        # 归一化权重
        level_weights = [w / total_weight for w in level_weights]
        
        # 假设当前是第一层（实际应用中需要知道当前持仓和成本）
        current_level = 0
        position_size = level_weights[current_level] * signal.strength
        
        # 计算交易金额
        trade_value = account_info.total_assets * position_size
        
        # 确保不低于最小交易金额
        trade_value = max(trade_value, min_trade_value)
        
        # 计算交易数量
        quantity = int(trade_value // market_data.price // 100) * 100
        quantity = max(quantity, 100)
        
        actual_value = quantity * market_data.price
        
        return PositionDecision(
            symbol=signal.symbol,
            action=signal.direction,
            quantity=quantity,
            price=market_data.price,
            value=actual_value,
            position_method="pyramid",
            risk_score=0.5,
            timestamp=datetime.now(),
            metadata={
                "pyramid_levels": pyramid_levels,
                "current_level": current_level,
                "level_weights": level_weights,
                "position_size": position_size,
                "calculated_value": trade_value
            }
        )
    
    def _grid_trading(self, signal: TradingSignal,
                     account_info: AccountInfo,
                     market_data: MarketData) -> PositionDecision:
        """
        网格交易算法
        
        在价格区间内分批建仓
        """
        min_trade_value = self.config.get("min_trade_value", 1000)
        grid_levels = self.config.get("grid_levels", 5)
        
        # 网格交易：在价格区间内等分网格
        # 这里简化：假设价格在当前价格的±10%范围内
        price_range_low = market_data.price * 0.9
        price_range_high = market_data.price * 1.1
        
        # 计算网格间距
        grid_spacing = (price_range_high - price_range_low) / grid_levels
        
        # 确定当前价格所在的网格位置
        if market_data.price <= price_range_low:
            grid_position = 0
        elif market_data.price >= price_range_high:
            grid_position = grid_levels - 1
        else:
            grid_position = int((market_data.price - price_range_low) // grid_spacing)
        
        # 网格仓位：越靠近区间底部，仓位越大
        # 线性递减：从底部到顶部，仓位从大到小
        position_weight = 1.0 - (grid_position / grid_levels)
        
        # 基础仓位大小
        base_position = 0.15  # 15%
        
        # 计算仓位
        position_size = base_position * position_weight * signal.strength
        
        # 计算交易金额
        trade_value = account_info.total_assets * position_size
        
        # 确保不低于最小交易金额
        trade_value = max(trade_value, min_trade_value)
        
        # 计算交易数量
        quantity = int(trade_value // market_data.price // 100) * 100
        quantity = max(quantity, 100)
        
        actual_value = quantity * market_data.price
        
        return PositionDecision(
            symbol=signal.symbol,
            action=signal.direction,
            quantity=quantity,
            price=market_data.price,
            value=actual_value,
            position_method="grid",
            risk_score=0.5,
            timestamp=datetime.now(),
            metadata={
                "grid_levels": grid_levels,
                "grid_position": grid_position,
                "price_range_low": price_range_low,
                "price_range_high": price_range_high,
                "position_weight": position_weight,
                "position_size": position_size,
                "calculated_value": trade_value
            }
        )
    
    def _apply_risk_limits(self, decision: PositionDecision,
                          account_info: AccountInfo,
                          market_data: MarketData) -> PositionDecision:
        """
        应用风险限制
        
        包括：
        1. 单只股票最大仓位限制
        2. 可用资金检查
        3. 最小交易金额检查
        """
        # 单只股票最大仓位限制
        max_position_per_stock = self.config.get("max_position_per_stock", 0.2)  # 20%
        max_value_per_stock = account_info.total_assets * max_position_per_stock
        
        if decision.value > max_value_per_stock:
            logger.warning(f"交易金额{decision.value:.2f}超过单股最大限制{max_value_per_stock:.2f}，进行限制")
            decision.value = max_value_per_stock
            decision.quantity = int(decision.value // market_data.price // 100) * 100
            decision.quantity = max(decision.quantity, 100)
            decision.value = decision.quantity * market_data.price
        
        # 可用资金检查
        if decision.action == "buy":
            # 买入金额不能超过可用现金的80%（留有余地）
            max_buy_value = account_info.available_cash * 0.8
            
            if decision.value > max_buy_value:
                logger.warning(f"交易金额{decision.value:.2f}超过可用资金限制{max_buy_value:.2f}，进行调整")
                
                # 调整到可用资金的80%
                decision.value = max_buy_value
                decision.quantity = int(decision.value // market_data.price // 100) * 100
                decision.quantity = max(decision.quantity, 100)
                decision.value = decision.quantity * market_data.price
        
        # 最小交易金额检查
        min_trade_value = self.config.get("min_trade_value", 1000)
        if decision.value < min_trade_value:
            logger.warning(f"交易金额{decision.value:.2f}低于最小交易金额{min_trade_value}，调整为最小交易")
            decision.value = min_trade_value
            decision.quantity = int(decision.value // market_data.price // 100) * 100
            decision.quantity = max(decision.quantity, 100)
            decision.value = decision.quantity * market_data.price
        
        return decision
    
    def _calculate_risk_score(self, decision: PositionDecision,
                            account_info: AccountInfo,
                            market_data: MarketData,
                            signal: TradingSignal) -> float:
        """
        计算风险评分（0-1，越低表示风险越小）
        
        考虑因素：
        1. 仓位大小（占资产比例）
        2. 波动率
        3. 信号强度
        4. 市场状态
        """
        # 仓位风险：仓位越大风险越高
        position_risk = min(decision.value / account_info.total_assets * 5, 1.0)
        
        # 波动率风险：波动率越高风险越高
        volatility = market_data.volatility or (market_data.high - market_data.low) / market_data.price
        volatility_risk = min(volatility * 10, 1.0)  # 假设正常波动率10%
        
        # 信号风险：信号越弱风险越高
        signal_risk = 1.0 - signal.strength
        
        # 综合风险评分（加权平均）
        weights = {
            "position": 0.4,
            "volatility": 0.3,
            "signal": 0.3
        }
        
        risk_score = (
            position_risk * weights["position"] +
            volatility_risk * weights["volatility"] +
            signal_risk * weights["signal"]
        )
        
        # 限制在0-1范围内
        return max(0.0, min(risk_score, 1.0))
    
    def _create_hold_decision(self, signal: TradingSignal,
                             market_data: MarketData,
                             error: Optional[str] = None) -> PositionDecision:
        """创建hold决策"""
        metadata = {"reason": "hold signal"}
        if error:
            metadata["error"] = error
        
        return PositionDecision(
            symbol=signal.symbol,
            action="hold",
            quantity=0,
            price=market_data.price,
            value=0.0,
            position_method="hold",
            risk_score=0.1,  # hold的风险很低
            timestamp=datetime.now(),
            metadata=metadata
        )


# 测试函数
def test_position_manager():
    """测试仓位管理器"""
    print("=== 测试仓位管理器 ===")
    
    # 创建配置
    config = {
        "position_method": "fixed",
        "fixed_position_size": 0.1,  # 10%
        "max_position_per_stock": 0.2,  # 20%
        "min_trade_value": 1000,
        "kelly_fraction": 0.5,
        "atr_multiplier": 2.0,
        "grid_levels": 5,
        "pyramid_levels": 3
    }
    
    # 创建仓位管理器
    pm = PositionManager(config)
    
    # 创建测试数据
    from datetime import datetime
    
    signal = TradingSignal(
        symbol="000001.SZ",
        direction="buy",
        strength=0.8,
        confidence=0.7,
        timestamp=datetime.now(),
        price=10.5,
        volume=1000000,
        factor_scores={"momentum": 0.8, "value": 0.6}
    )
    
    account_info = AccountInfo(
        total_assets=100000,
        available_cash=50000,
        market_value=50000,
        risk_tolerance=0.02
    )
    
    market_data = MarketData(
        symbol="000001.SZ",
        price=10.5,
        volume=1000000,
        high=11.0,
        low=10.0,
        open=10.2,
        close=10.5,
        atr=0.3,
        volatility=0.15,
        beta=1.2
    )
    
    # 测试不同算法
    methods = ["fixed", "kelly", "volatility", "risk_parity", "pyramid", "grid"]
    
    for method in methods:
        print(f"\n--- 测试 {method} 算法 ---")
        config["position_method"] = method
        
        pm = PositionManager(config)
        decision = pm.calculate_position(signal, account_info, market_data)
        
        print(f"决策: {decision.action} {decision.quantity}股 @ {decision.price:.2f}")
        print(f"金额: {decision.value:.2f}元")
        print(f"算法: {decision.position_method}")
        print(f"风险评分: {decision.risk_score:.3f}")
        
        if decision.metadata:
            print("元数据:")
            for key, value in decision.metadata.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")


if __name__ == "__main__":
    test_position_manager()