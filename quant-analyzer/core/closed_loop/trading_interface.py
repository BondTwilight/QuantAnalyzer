"""
统一交易接口模块
支持多种交易接口：QMT、Easytrader、THS、模拟交易等
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import json
import time
import threading
from abc import ABC, abstractmethod

# 设置日志
logger = logging.getLogger(__name__)

# ==================== 基础数据结构 ====================

class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    """订单类型"""
    MARKET = "market"  # 市价单
    LIMIT = "limit"    # 限价单
    STOP = "stop"      # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单


class TradingInterfaceType(Enum):
    """交易接口类型"""
    SIMULATION = "simulation"  # 模拟交易
    QMT = "qmt"                # QMT接口
    EASYTRADER = "easytrader"  # Easytrader接口
    THS = "ths"                # 同花顺接口
    CTP = "ctp"                # CTP期货接口
    IB = "ib"                  # Interactive Brokers接口
    ALPACA = "alpaca"          # Alpaca接口


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None  # 限价单价格
    stop_price: Optional[float] = None  # 止损单触发价格
    order_time: datetime = field(default_factory=datetime.now)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0
    filled_price: float = 0
    filled_time: Optional[datetime] = None
    commission: float = 0
    message: str = ""
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "order_time": self.order_time.isoformat(),
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "filled_time": self.filled_time.isoformat() if self.filled_time else None,
            "commission": self.commission,
            "message": self.message
        }

@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    available_quantity: float  # 可卖数量（考虑T+1）
    avg_cost: float
    market_value: float = 0
    unrealized_pnl: float = 0
    realized_pnl: float = 0
    open_time: Optional[datetime] = None
    last_price: float = 0
    
    def update(self, current_price: float):
        """更新持仓信息"""
        self.last_price = current_price
        self.market_value = self.quantity * current_price
        self.unrealized_pnl = self.market_value - (self.quantity * self.avg_cost)

@dataclass
class AccountInfo:
    """账户信息"""
    account_id: str
    total_assets: float
    available_cash: float
    market_value: float
    frozen_cash: float = 0
    total_pnl: float = 0
    daily_pnl: float = 0
    update_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "account_id": self.account_id,
            "total_assets": self.total_assets,
            "available_cash": self.available_cash,
            "market_value": self.market_value,
            "frozen_cash": self.frozen_cash,
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "update_time": self.update_time.isoformat()
        }

@dataclass
class MarketData:
    """市场数据"""
    symbol: str
    last_price: float
    bid_price: float
    ask_price: float
    bid_volume: int
    ask_volume: int
    volume: int
    turnover: float
    open: float
    high: float
    low: float
    pre_close: float
    update_time: datetime
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "last_price": self.last_price,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "volume": self.volume,
            "turnover": self.turnover,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "pre_close": self.pre_close,
            "update_time": self.update_time.isoformat()
        }

# ==================== 抽象接口 ====================

class TradingInterface(ABC):
    """交易接口抽象基类"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接交易接口"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否连接"""
        pass
    
    @abstractmethod
    def place_order(self, order: Order) -> Order:
        """下单"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """获取订单状态"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """获取持仓"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        pass
    
    @abstractmethod
    def get_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """获取行情数据"""
        pass
    
    @abstractmethod
    def get_order_history(self, start_date: datetime, end_date: datetime) -> List[Order]:
        """获取历史订单"""
        pass

# ==================== 模拟交易接口 ====================

class SimulationInterface(TradingInterface):
    """模拟交易接口（用于回测和模拟盘）"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.account_id = config.get("account_id", "simulation_001")
        self.initial_capital = config.get("initial_capital", 100000)
        
        # 账户状态
        self.account = AccountInfo(
            account_id=self.account_id,
            total_assets=self.initial_capital,
            available_cash=self.initial_capital,
            market_value=0
        )
        
        # 持仓
        self.positions: Dict[str, Position] = {}
        
        # 订单
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0
        
        # 市场数据（模拟）
        self.market_data: Dict[str, MarketData] = {}
        
        # 交易记录
        self.trade_history: List[Order] = []
        
        # T+1标记
        self.tplus1_enabled = config.get("tplus1", True)
        self.buy_records: Dict[str, List[datetime]] = {}  # 买入时间记录
        
        # 手续费配置
        self.commission_rate = config.get("commission_rate", 0.0003)
        self.stamp_tax = config.get("stamp_tax", 0.001)
        self.transfer_fee = config.get("transfer_fee", 0.00002)
        
        # 滑点配置
        self.slippage = config.get("slippage", 0.001)
        
        logger.info(f"模拟交易接口初始化完成，初始资金: {self.initial_capital}")
    
    def connect(self) -> bool:
        """连接模拟接口（总是成功）"""
        logger.info("模拟交易接口连接成功")
        return True
    
    def disconnect(self) -> bool:
        """断开连接"""
        logger.info("模拟交易接口断开连接")
        return True
    
    def is_connected(self) -> bool:
        """检查是否连接"""
        return True
    
    def place_order(self, order: Order) -> Order:
        """模拟下单"""
        # 生成订单ID
        self.order_counter += 1
        order.order_id = f"sim_order_{self.order_counter:06d}"
        
        # 检查订单有效性
        is_valid, message = self._check_order_validity(order)
        if not is_valid:
            order.status = OrderStatus.REJECTED
            order.message = message
            logger.warning(f"订单被拒绝: {message}")
            return order
        
        # 模拟成交
        filled_price = self._simulate_fill(order)
        
        # 计算手续费
        commission = self._calculate_commission(order, filled_price)
        
        # 更新订单状态
        order.filled_quantity = order.quantity
        order.filled_price = filled_price
        order.filled_time = datetime.now()
        order.commission = commission
        order.status = OrderStatus.FILLED
        order.message = "模拟成交成功"
        
        # 更新账户和持仓
        self._update_account_and_positions(order, filled_price, commission)
        
        # 记录订单
        self.orders[order.order_id] = order
        self.trade_history.append(order)
        
        logger.info(f"模拟成交: {order.symbol} {order.side.value} {order.quantity} @ {filled_price:.2f}")
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """模拟撤单"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                order.message = "模拟撤单成功"
                logger.info(f"订单 {order_id} 撤单成功")
                return True
            else:
                logger.warning(f"订单 {order_id} 状态为 {order.status.value}，无法撤单")
                return False
        else:
            logger.warning(f"订单 {order_id} 不存在")
            return False
    
    def get_order_status(self, order_id: str) -> OrderStatus:
        """获取订单状态"""
        if order_id in self.orders:
            return self.orders[order_id].status
        return OrderStatus.REJECTED
    
    def get_positions(self) -> List[Position]:
        """获取持仓"""
        # 更新持仓市值
        for symbol, position in self.positions.items():
            if symbol in self.market_data:
                position.update(self.market_data[symbol].last_price)
        
        return list(self.positions.values())
    
    def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        # 更新账户信息
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        self.account.market_value = total_market_value
        self.account.total_assets = self.account.available_cash + total_market_value
        
        # 计算总盈亏
        total_cost = sum(pos.quantity * pos.avg_cost for pos in self.positions.values())
        self.account.total_pnl = total_market_value - total_cost
        
        return self.account
    
    def get_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """获取模拟行情数据"""
        # 这里应该从外部数据源获取真实数据
        # 目前返回模拟数据
        result = {}
        
        for symbol in symbols:
            if symbol not in self.market_data:
                # 生成模拟数据
                self.market_data[symbol] = self._generate_mock_market_data(symbol)
            
            result[symbol] = self.market_data[symbol]
        
        return result
    
    def get_order_history(self, start_date: datetime, end_date: datetime) -> List[Order]:
        """获取历史订单"""
        return [order for order in self.trade_history 
                if start_date <= order.order_time <= end_date]
    
    def update_market_data(self, symbol: str, price: float, volume: int = 0):
        """更新市场数据（用于测试）"""
        now = datetime.now()
        self.market_data[symbol] = MarketData(
            symbol=symbol,
            last_price=price,
            bid_price=price * 0.999,
            ask_price=price * 1.001,
            bid_volume=volume // 2,
            ask_volume=volume // 2,
            volume=volume,
            turnover=price * volume,
            open=price * 0.99,
            high=price * 1.01,
            low=price * 0.99,
            pre_close=price * 0.995,
            update_time=now
        )
    
    def _check_order_validity(self, order: Order) -> Tuple[bool, str]:
        """检查订单有效性"""
        # 检查资金是否足够（买入时）
        if order.side == OrderSide.BUY:
            estimated_cost = order.quantity * (order.price or 100) * 1.001  # 包含预估手续费
            if estimated_cost > self.account.available_cash:
                return False, f"资金不足，需要{estimated_cost:.2f}，可用{self.account.available_cash:.2f}"
        
        # 检查持仓是否足够（卖出时）
        if order.side == OrderSide.SELL:
            if order.symbol not in self.positions:
                return False, f"没有{order.symbol}的持仓"
            
            pos = self.positions[order.symbol]
            
            # 检查T+1限制
            if self.tplus1_enabled:
                available_qty = self._get_available_sell_quantity(order.symbol)
                if order.quantity > available_qty:
                    return False, f"可卖数量不足，需要{order.quantity}，可卖{available_qty}"
            else:
                if order.quantity > pos.quantity:
                    return False, f"卖出数量{order.quantity}超过持仓数量{pos.quantity}"
        
        # 检查价格合理性
        if order.price is not None and order.price <= 0:
            return False, f"价格{order.price}无效"
        
        # 检查数量合理性
        if order.quantity <= 0:
            return False, f"数量{order.quantity}无效"
        
        return True, "订单有效"
    
    def _simulate_fill(self, order: Order) -> float:
        """模拟成交"""
        if order.order_type == OrderType.MARKET:
            # 市价单：使用当前卖一价（买入）或买一价（卖出）
            if order.symbol in self.market_data:
                md = self.market_data[order.symbol]
                if order.side == OrderSide.BUY:
                    base_price = md.ask_price
                else:
                    base_price = md.bid_price
            else:
                base_price = 100  # 默认价格
            
            # 应用滑点
            if order.side == OrderSide.BUY:
                filled_price = base_price * (1 + self.slippage)
            else:
                filled_price = base_price * (1 - self.slippage)
            
        elif order.order_type == OrderType.LIMIT and order.price is not None:
            # 限价单：检查是否可成交
            if order.symbol in self.market_data:
                md = self.market_data[order.symbol]
                
                if order.side == OrderSide.BUY:
                    # 买入：限价 >= 卖一价 可成交
                    if order.price >= md.ask_price:
                        filled_price = min(order.price, md.ask_price * (1 + self.slippage))
                    else:
                        # 无法立即成交，这里简化处理为按限价成交
                        filled_price = order.price
                else:
                    # 卖出：限价 <= 买一价 可成交
                    if order.price <= md.bid_price:
                        filled_price = max(order.price, md.bid_price * (1 - self.slippage))
                    else:
                        filled_price = order.price
            else:
                filled_price = order.price
        
        else:
            # 其他订单类型暂不支持
            filled_price = order.price or 100
        
        return filled_price
    
    def _calculate_commission(self, order: Order, filled_price: float) -> float:
        """计算手续费"""
        trade_value = order.quantity * filled_price
        
        # 佣金（双向收取）
        commission = trade_value * self.commission_rate
        
        # 印花税（卖出时收取）
        if order.side == OrderSide.SELL:
            commission += trade_value * self.stamp_tax
        
        # 过户费（双向收取）
        commission += trade_value * self.transfer_fee
        
        return commission
    
    def _update_account_and_positions(self, order: Order, filled_price: float, commission: float):
        """更新账户和持仓"""
        trade_value = order.quantity * filled_price
        
        if order.side == OrderSide.BUY:
            # 买入：减少现金，增加持仓
            total_cost = trade_value + commission
            self.account.available_cash -= total_cost
            
            # 记录买入时间（用于T+1）
            if self.tplus1_enabled:
                if order.symbol not in self.buy_records:
                    self.buy_records[order.symbol] = []
                self.buy_records[order.symbol].append(order.filled_time)
            
            # 更新持仓
            if order.symbol not in self.positions:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    available_quantity=0 if self.tplus1_enabled else order.quantity,
                    avg_cost=filled_price,
                    open_time=order.filled_time
                )
            else:
                pos = self.positions[order.symbol]
                total_qty = pos.quantity + order.quantity
                total_cost_basis = (pos.quantity * pos.avg_cost + 
                                   order.quantity * filled_price)
                pos.quantity = total_qty
                pos.avg_cost = total_cost_basis / total_qty if total_qty > 0 else 0
                
                # 更新可卖数量
                if not self.tplus1_enabled:
                    pos.available_quantity = pos.quantity
        
        else:  # SELL
            # 卖出：增加现金，减少持仓
            proceeds = trade_value - commission
            self.account.available_cash += proceeds
            
            # 更新持仓
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                
                # 计算盈亏
                cost_basis = pos.avg_cost * order.quantity
                pnl = proceeds - cost_basis
                pos.realized_pnl += pnl
                
                # 减少持仓
                pos.quantity -= order.quantity
                pos.available_quantity -= order.quantity
                
                # 如果持仓为0，移除该持仓
                if pos.quantity <= 0:
                    del self.positions[order.symbol]
                    if order.symbol in self.buy_records:
                        del self.buy_records[order.symbol]
    
    def _get_available_sell_quantity(self, symbol: str) -> float:
        """获取可卖数量（考虑T+1）"""
        if symbol not in self.positions:
            return 0
        
        pos = self.positions[symbol]
        
        if not self.tplus1_enabled:
            return pos.quantity
        
        # 计算T+1可卖数量
        now = datetime.now()
        available_qty = 0
        
        if symbol in self.buy_records:
            for buy_time in self.buy_records[symbol]:
                # 检查是否已过T+1（买入后下一个交易日）
                # 这里简化处理：买入时间超过24小时即可卖
                if (now - buy_time) > timedelta(hours=24):
                    available_qty += pos.quantity / len(self.buy_records[symbol])
        
        return available_qty
    
    def _generate_mock_market_data(self, symbol: str) -> MarketData:
        """生成模拟市场数据"""
        now = datetime.now()
        base_price = 100 + np.random.randn() * 10
        
        return MarketData(
            symbol=symbol,
            last_price=base_price,
            bid_price=base_price * 0.999,
            ask_price=base_price * 1.001,
            bid_volume=np.random.randint(100, 1000),
            ask_volume=np.random.randint(100, 1000),
            volume=np.random.randint(10000, 100000),
            turnover=base_price * np.random.randint(10000, 100000),
            open=base_price * (1 + np.random.randn() * 0.01),
            high=base_price * (1 + abs(np.random.randn()) * 0.02),
            low=base_price * (1 - abs(np.random.randn()) * 0.02),
            pre_close=base_price * 0.995,
            update_time=now
        )

# ==================== 统一交易接口 ====================

class UnifiedTradingInterface:
    """统一交易接口（适配多种交易接口）"""
    
    def __init__(self, interface_type: str, config: Dict):
        self.interface_type = interface_type
        self.config = config
        
        # 根据类型初始化具体接口
        if interface_type == "simulation":
            self.impl = SimulationInterface(config)
        elif interface_type == "qmt":
            # QMT接口（需要安装QMT SDK）
            self.impl = self._create_qmt_interface(config)
        elif interface_type == "easytrader":
            # Easytrader接口
            self.impl = self._create_easytrader_interface(config)
        elif interface_type == "ths":
            # 同花顺接口
            self.impl = self._create_ths_interface(config)
        else:
            raise ValueError(f"不支持的接口类型: {interface_type}")
        
        logger.info(f"统一交易接口初始化完成，类型: {interface_type}")
    
    def _create_qmt_interface(self, config: Dict) -> TradingInterface:
        """创建QMT接口"""
        # 这里应该实现真实的QMT接口
        # 目前返回模拟接口
        logger.warning("QMT接口暂未实现，使用模拟接口替代")
        return SimulationInterface(config)
    
    def _create_easytrader_interface(self, config: Dict) -> TradingInterface:
        """创建Easytrader接口"""
        # 这里应该实现真实的Easytrader接口
        logger.warning("Easytrader接口暂未实现，使用模拟接口替代")
        return SimulationInterface(config)
    
    def _create_ths_interface(self, config: Dict) -> TradingInterface:
        """创建同花顺接口"""
        # 这里应该实现真实的同花顺接口
        logger.warning("同花顺接口暂未实现，使用模拟接口替代")
        return SimulationInterface(config)
    
    def connect(self) -> bool:
        """连接交易接口"""
        return self.impl.connect()
    
    def disconnect(self) -> bool:
        """断开连接"""
        return self.impl.disconnect()
    
    def is_connected(self) -> bool:
        """检查是否连接"""
        return self.impl.is_connected()
    
    def place_order(self, symbol: str, side: str, quantity: float, 
                   order_type: str = "limit", price: Optional[float] = None,
                   stop_price: Optional[float] = None) -> Dict:
        """下单（简化接口）"""
        # 创建订单对象
        order = Order(
            order_id="",  # 由接口生成
            symbol=symbol,
            side=OrderSide(side),
            order_type=OrderType(order_type),
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
        
        # 下单
        result = self.impl.place_order(order)
        
        return result.to_dict()
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        return self.impl.cancel_order(order_id)
    
    def get_order_status(self, order_id: str) -> str:
        """获取订单状态"""
        status = self.impl.get_order_status(order_id)
        return status.value
    
    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        positions = self.impl.get_positions()
        return [self._position_to_dict(pos) for pos in positions]
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        account = self.impl.get_account_info()
        return account.to_dict()
    
    def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """获取行情数据"""
        market_data = self.impl.get_market_data(symbols)
        return {symbol: md.to_dict() for symbol, md in market_data.items()}
    
    def get_order_history(self, start_date: str, end_date: str) -> List[Dict]:
        """获取历史订单"""
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        orders = self.impl.get_order_history(start, end)
        return [order.to_dict() for order in orders]
    
    def _position_to_dict(self, position: Position) -> Dict:
        """持仓对象转字典"""
        return {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "available_quantity": position.available_quantity,
            "avg_cost": position.avg_cost,
            "market_value": position.market_value,
            "unrealized_pnl": position.unrealized_pnl,
            "realized_pnl": position.realized_pnl,
            "open_time": position.open_time.isoformat() if position.open_time else None,
            "last_price": position.last_price
        }

# ==================== 订单管理器 ====================

class OrderManager:
    """订单管理器（用于批量订单管理和状态跟踪）"""
    
    def __init__(self, trading_interface: UnifiedTradingInterface):
        self.interface = trading_interface
        self.active_orders: Dict[str, Order] = {}
        self.order_callbacks = {}  # 订单回调函数
        
    def place_batch_orders(self, orders: List[Dict]) -> List[Dict]:
        """批量下单"""
        results = []
        
        for order_spec in orders:
            try:
                result = self.interface.place_order(**order_spec)
                results.append(result)
                
                # 记录活跃订单
                if result["status"] == OrderStatus.PENDING.value:
                    order = self._dict_to_order(result)
                    self.active_orders[order.order_id] = order
                    
                    # 设置回调
                    if "callback" in order_spec:
                        self.order_callbacks[order.order_id] = order_spec["callback"]
                
            except Exception as e:
                logger.error(f"下单失败: {e}")
                results.append({
                    "status": OrderStatus.REJECTED.value,
                    "message": str(e)
                })
        
        return results
    
    def cancel_batch_orders(self, order_ids: List[str]) -> List[bool]:
        """批量撤单"""
        results = []
        
        for order_id in order_ids:
            try:
                success = self.interface.cancel_order(order_id)
                results.append(success)
                
                if success and order_id in self.active_orders:
                    del self.active_orders[order_id]
                    if order_id in self.order_callbacks:
                        del self.order_callbacks[order_id]
                
            except Exception as e:
                logger.error(f"撤单失败 {order_id}: {e}")
                results.append(False)
        
        return results
    
    def monitor_orders(self, interval: int = 5):
        """监控订单状态"""
        import threading
        import time
        
        def monitor_loop():
            while True:
                try:
                    self._check_order_status()
                except Exception as e:
                    logger.error(f"订单监控错误: {e}")
                
                time.sleep(interval)
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info(f"订单监控启动，检查间隔: {interval}秒")
    
    def _check_order_status(self):
        """检查订单状态"""
        for order_id in list(self.active_orders.keys()):
            try:
                status_str = self.interface.get_order_status(order_id)
                status = OrderStatus(status_str)
                
                if status != self.active_orders[order_id].status:
                    # 状态变化
                    old_status = self.active_orders[order_id].status
                    self.active_orders[order_id].status = status
                    
                    logger.info(f"订单 {order_id} 状态变化: {old_status.value} -> {status.value}")
                    
                    # 触发回调
                    if order_id in self.order_callbacks:
                        try:
                            self.order_callbacks[order_id](order_id, status)
                        except Exception as e:
                            logger.error(f"订单回调执行失败 {order_id}: {e}")
                    
                    # 如果订单已完成，从活跃订单中移除
                    if status in [OrderStatus.FILLED, OrderStatus.CANCELLED, 
                                 OrderStatus.REJECTED, OrderStatus.EXPIRED]:
                        del self.active_orders[order_id]
                        if order_id in self.order_callbacks:
                            del self.order_callbacks[order_id]
                
            except Exception as e:
                logger.error(f"检查订单状态失败 {order_id}: {e}")
    
    def _dict_to_order(self, data: Dict) -> Order:
        """字典转订单对象"""
        return Order(
            order_id=data["order_id"],
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            order_type=OrderType(data["order_type"]),
            quantity=data["quantity"],
            price=data.get("price"),
            stop_price=data.get("stop_price"),
            order_time=datetime.fromisoformat(data["order_time"]),
            status=OrderStatus(data["status"]),
            filled_quantity=data.get("filled_quantity", 0),
            filled_price=data.get("filled_price", 0),
            filled_time=datetime.fromisoformat(data["filled_time"]) if data.get("filled_time") else None,
            commission=data.get("commission", 0),
            message=data.get("message", "")
        )

# ==================== 测试函数 ====================

def test_trading_interface():
    """测试交易接口"""
    print("测试交易接口...")
    
    # 创建模拟交易接口
    config = {
        "account_id": "test_001",
        "initial_capital": 100000,
        "tplus1": True,
        "commission_rate": 0.0003,
        "stamp_tax": 0.001,
        "transfer_fee": 0.00002,
        "slippage": 0.001
    }
    
    interface = UnifiedTradingInterface("simulation", config)
    
    # 连接
    if not interface.connect():
        print("连接失败")
        return
    
    print("连接成功")
    
    # 获取账户信息
    account = interface.get_account_info()
    print(f"初始账户信息: 总资产={account['total_assets']:.2f}, 可用现金={account['available_cash']:.2f}")
    
    # 更新市场数据
    if isinstance(interface.impl, SimulationInterface):
        interface.impl.update_market_data("000001.SZ", 100, 1000000)
        interface.impl.update_market_data("000002.SZ", 50, 500000)
    
    # 获取行情数据
    market_data = interface.get_market_data(["000001.SZ", "000002.SZ"])
    for symbol, data in market_data.items():
        print(f"{symbol}: 最新价={data['last_price']:.2f}")
    
    # 下单测试
    print("\n下单测试...")
    
    # 买入订单
    buy_order = interface.place_order(
        symbol="000001.SZ",
        side="buy",
        quantity=100,
        order_type="market"
    )
    
    print(f"买入订单: {buy_order}")
    
    # 获取持仓
    positions = interface.get_positions()
    print(f"\n持仓: {positions}")
    
    # 获取更新后的账户信息
    account = interface.get_account_info()
    print(f"交易后账户: 总资产={account['total_assets']:.2f}, 可用现金={account['available_cash']:.2f}")
    
    # 等待一段时间（模拟T+1）
    print("\n等待T+1...")
    import time
    time.sleep(1)
    
    # 卖出订单
    sell_order = interface.place_order(
        symbol="000001.SZ",
        side="sell",
        quantity=50,
        order_type="market"
    )
    
    print(f"卖出订单: {sell_order}")
    
    # 最终状态
    positions = interface.get_positions()
    account = interface.get_account_info()
    
    print(f"\n最终持仓: {positions}")
    print(f"最终账户: 总资产={account['total_assets']:.2f}, 总盈亏={account['total_pnl']:.2f}")
    
    # 断开连接
    interface.disconnect()
    print("\n测试完成")
    
    return interface

def test_order_manager():
    """测试订单管理器"""
    print("\n测试订单管理器...")
    
    # 创建接口
    config = {
        "account_id": "test_002",
        "initial_capital": 200000,
        "tplus1": False
    }
    
    interface = UnifiedTradingInterface("simulation", config)
    interface.connect()
    
    # 创建订单管理器
    order_manager = OrderManager(interface)
    
    # 定义回调函数
    def order_callback(order_id: str, status: OrderStatus):
        print(f"订单回调: {order_id} -> {status.value}")
    
    # 批量下单
    orders = [
        {
            "symbol": "000001.SZ",
            "side": "buy",
            "quantity": 100,
            "order_type": "limit",
            "price": 99,
            "callback": order_callback
        },
        {
            "symbol": "000002.SZ",
            "side": "buy",
            "quantity": 200,
            "order_type": "limit",
            "price": 48,
            "callback": order_callback
        }
    ]
    
    results = order_manager.place_batch_orders(orders)
    print(f"批量下单结果: {results}")
    
    # 启动订单监控
    order_manager.monitor_orders(interval=2)
    
    # 等待监控
    import time
    time.sleep(5)
    
    # 批量撤单
    order_ids = [result["order_id"] for result in results if "order_id" in result]
    if order_ids:
        cancel_results = order_manager.cancel_batch_orders(order_ids)
        print(f"批量撤单结果: {cancel_results}")
    
    # 断开连接
    interface.disconnect()
    print("订单管理器测试完成")

if __name__ == "__main__":
    # 测试交易接口
    test_trading_interface()
    
    # 测试订单管理器
    test_order_manager()