"""
增强版回测引擎
包含完整的交易成本模拟、市场限制模拟、资金曲线分析和绩效指标计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum

# 设置日志
logger = logging.getLogger(__name__)

# ==================== 基础数据结构 ====================

class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    order_time: datetime
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0
    filled_price: float = 0
    commission: float = 0
    slippage: float = 0
    
    def get_filled_value(self) -> float:
        """获取成交金额"""
        return self.filled_quantity * self.filled_price
    
    def get_total_cost(self) -> float:
        """获取总成本（成交金额 + 手续费 + 滑点）"""
        return self.get_filled_value() + self.commission + self.slippage


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 1000000.0  # 初始资金
    commission_rate: float = 0.0003  # 佣金率 0.03%
    stamp_tax: float = 0.001  # 印花税 0.1%
    transfer_fee: float = 0.00002  # 过户费 0.002%
    slippage_model: str = "fixed"  # 滑点模型: fixed/percentage/random
    slippage_value: float = 0.001  # 滑点值
    enable_market_impact: bool = False  # 是否启用市场冲击模型
    market_impact_factor: float = 0.0001  # 市场冲击因子
    enable_short_selling: bool = False  # 是否允许卖空
    enable_margin_trading: bool = False  # 是否允许融资融券
    margin_rate: float = 0.5  # 保证金率
    start_date: Optional[datetime] = None  # 回测开始日期
    end_date: Optional[datetime] = None  # 回测结束日期
    benchmark_symbol: Optional[str] = None  # 基准指数
    risk_free_rate: float = 0.03  # 无风险利率
    max_position_size: float = 0.1  # 最大仓位比例
    max_drawdown_limit: float = 0.2  # 最大回撤限制
    stop_loss_enabled: bool = True  # 是否启用止损
    take_profit_enabled: bool = True  # 是否启用止盈
    data_frequency: str = "daily"  # 数据频率: daily/hourly/minute
    output_dir: Optional[str] = None  # 输出目录


@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    trade_time: datetime
    commission: float
    slippage: float
    pnl: float = 0  # 平仓时的盈亏
    
    def get_trade_value(self) -> float:
        """获取交易金额"""
        return self.quantity * self.price
    
    def get_total_cost(self) -> float:
        """获取总成本"""
        return self.get_trade_value() + self.commission + self.slippage

@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_cost: float
    market_value: float = 0
    unrealized_pnl: float = 0
    realized_pnl: float = 0
    open_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None
    
    def update_market_value(self, current_price: float):
        """更新市值和未实现盈亏"""
        self.market_value = self.quantity * current_price
        self.unrealized_pnl = self.market_value - (self.quantity * self.avg_cost)
        self.last_update_time = datetime.now()

@dataclass
class Portfolio:
    """投资组合"""
    initial_capital: float
    available_cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    total_assets: float = 0
    market_value: float = 0
    total_pnl: float = 0
    daily_pnl: float = 0
    
    def __post_init__(self):
        self.total_assets = self.available_cash
        self.market_value = 0
    
    def update(self, trades: List[Trade], market_prices: Dict[str, float]):
        """更新投资组合状态"""
        # 处理交易
        for trade in trades:
            if trade.side == OrderSide.BUY:
                # 买入：减少现金，增加持仓
                cost = trade.get_total_cost()
                self.available_cash -= cost
                
                if trade.symbol not in self.positions:
                    self.positions[trade.symbol] = Position(
                        symbol=trade.symbol,
                        quantity=trade.quantity,
                        avg_cost=trade.price,
                        open_time=trade.trade_time
                    )
                else:
                    # 计算新的平均成本
                    pos = self.positions[trade.symbol]
                    total_qty = pos.quantity + trade.quantity
                    total_cost = (pos.quantity * pos.avg_cost + 
                                 trade.quantity * trade.price)
                    pos.quantity = total_qty
                    pos.avg_cost = total_cost / total_qty if total_qty > 0 else 0
                    
            elif trade.side == OrderSide.SELL:
                # 卖出：增加现金，减少持仓
                if trade.symbol in self.positions:
                    pos = self.positions[trade.symbol]
                    
                    # 计算盈亏
                    cost_basis = pos.avg_cost * trade.quantity
                    proceeds = trade.get_trade_value() - trade.commission - trade.slippage
                    pnl = proceeds - cost_basis
                    
                    # 更新持仓
                    pos.quantity -= trade.quantity
                    pos.realized_pnl += pnl
                    
                    # 如果持仓为0，移除该持仓
                    if pos.quantity <= 0:
                        del self.positions[trade.symbol]
                    
                    # 增加现金
                    self.available_cash += proceeds
        
        # 更新市值和总资产
        self.market_value = 0
        for symbol, pos in self.positions.items():
            if symbol in market_prices:
                pos.update_market_value(market_prices[symbol])
                self.market_value += pos.market_value
        
        self.total_assets = self.available_cash + self.market_value
        self.total_pnl = self.total_assets - self.initial_capital

@dataclass
class BacktestResult:
    """回测结果"""
    portfolio: Portfolio
    trades: List[Trade]
    equity_curve: pd.DataFrame
    performance_metrics: Dict[str, float]
    risk_metrics: Dict[str, float]
    trade_analysis: Dict[str, Any]

# ==================== 交易成本模型 ====================

class CommissionModel:
    """手续费模型"""
    
    def __init__(self, commission_rate: float = 0.0003,  # 佣金率 0.03%
                 stamp_tax: float = 0.001,  # 印花税 0.1%
                 transfer_fee: float = 0.00002):  # 过户费 0.002%
        self.commission_rate = commission_rate
        self.stamp_tax = stamp_tax
        self.transfer_fee = transfer_fee
    
    def calculate_commission(self, order: Order) -> float:
        """计算手续费"""
        # 佣金（双向收取）
        commission = order.filled_quantity * order.filled_price * self.commission_rate
        
        # 印花税（卖出时收取）
        if order.side == OrderSide.SELL:
            commission += order.filled_quantity * order.filled_price * self.stamp_tax
        
        # 过户费（双向收取）
        commission += order.filled_quantity * order.filled_price * self.transfer_fee
        
        return commission

class SlippageModel:
    """滑点模型"""
    
    def __init__(self, slippage_type: str = "fixed", slippage_value: float = 0.001):
        self.slippage_type = slippage_type
        self.slippage_value = slippage_value
    
    def apply_slippage(self, order: Order, market_data: Dict) -> float:
        """应用滑点"""
        if self.slippage_type == "fixed":
            # 固定滑点
            if order.side == OrderSide.BUY:
                return order.price * (1 + self.slippage_value)
            else:
                return order.price * (1 - self.slippage_value)
        
        elif self.slippage_type == "percentage":
            # 基于波动率的滑点
            volatility = market_data.get("volatility", 0.02)
            slippage = volatility * self.slippage_value
            
            if order.side == OrderSide.BUY:
                return order.price * (1 + slippage)
            else:
                return order.price * (1 - slippage)
        
        elif self.slippage_type == "random":
            # 随机滑点
            import random
            slippage = random.uniform(-self.slippage_value, self.slippage_value)
            return order.price * (1 + slippage)
        
        else:
            return order.price

# ==================== 市场限制模型 ====================

class MarketConstraints:
    """市场限制"""
    
    def __init__(self, tplus1: bool = True,  # T+1交易制度
                 price_limit: bool = True,  # 涨跌停限制
                 min_trade_units: int = 100,  # 最小交易单位
                 max_position_per_stock: float = 0.1):  # 单只股票最大持仓比例
        self.tplus1 = tplus1
        self.price_limit = price_limit
        self.min_trade_units = min_trade_units
        self.max_position_per_stock = max_position_per_stock
    
    def check_order_validity(self, order: Order, portfolio: Portfolio, 
                           market_data: Dict) -> Tuple[bool, str]:
        """检查订单有效性"""
        # 检查最小交易单位
        if order.quantity < self.min_trade_units:
            return False, f"交易数量{order.quantity}小于最小交易单位{self.min_trade_units}"
        
        # 检查资金是否足够（买入时）
        if order.side == OrderSide.BUY:
            estimated_cost = order.quantity * order.price * 1.001  # 包含预估手续费
            if estimated_cost > portfolio.available_cash:
                return False, f"资金不足，需要{estimated_cost:.2f}，可用{portfolio.available_cash:.2f}"
        
        # 检查持仓是否足够（卖出时）
        if order.side == OrderSide.SELL:
            if order.symbol not in portfolio.positions:
                return False, f"没有{symbol}的持仓"
            
            pos = portfolio.positions[order.symbol]
            if order.quantity > pos.quantity:
                return False, f"卖出数量{order.quantity}超过持仓数量{pos.quantity}"
        
        # 检查涨跌停限制
        if self.price_limit and "price_limit" in market_data:
            price_limits = market_data["price_limit"]
            if order.price < price_limits["lower"] or order.price > price_limits["upper"]:
                return False, f"价格{order.price}超出涨跌停范围[{price_limits['lower']}, {price_limits['upper']}]"
        
        # 检查持仓集中度
        if order.side == OrderSide.BUY:
            estimated_position_value = order.quantity * order.price
            if portfolio.total_assets > 0:
                position_ratio = estimated_position_value / portfolio.total_assets
                if position_ratio > self.max_position_per_stock:
                    return False, f"持仓集中度{position_ratio:.2%}超过限制{self.max_position_per_stock:.2%}"
        
        return True, "订单有效"

# ==================== 绩效分析器 ====================

class PerformanceAnalyzer:
    """绩效分析器"""
    
    def __init__(self):
        pass
    
    def calculate_metrics(self, equity_curve: pd.DataFrame, 
                         trades: List[Trade]) -> Dict[str, float]:
        """计算绩效指标"""
        if len(equity_curve) < 2:
            return {}
        
        # 提取净值曲线
        equity = equity_curve["total_assets"].values
        returns = np.diff(equity) / equity[:-1]
        
        # 基础指标
        total_return = (equity[-1] - equity[0]) / equity[0]
        annual_return = total_return * 252 / len(equity) if len(equity) > 1 else 0
        
        # 波动率
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0
        
        # 夏普比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        excess_returns = returns - risk_free_rate/252
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if len(excess_returns) > 1 and np.std(excess_returns) > 0 else 0
        
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown(equity)
        
        # 索提诺比率
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 1 else 0
        sortino_ratio = (annual_return - risk_free_rate) / downside_std if downside_std > 0 else 0
        
        # 卡玛比率
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        # 交易分析
        trade_analysis = self._analyze_trades(trades)
        
        metrics = {
            "total_return": total_return,
            "annual_return": annual_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "win_rate": trade_analysis.get("win_rate", 0),
            "profit_factor": trade_analysis.get("profit_factor", 0),
            "avg_win": trade_analysis.get("avg_win", 0),
            "avg_loss": trade_analysis.get("avg_loss", 0),
            "total_trades": trade_analysis.get("total_trades", 0),
            "profit_trades": trade_analysis.get("profit_trades", 0),
            "loss_trades": trade_analysis.get("loss_trades", 0)
        }
        
        return metrics
    
    def _calculate_max_drawdown(self, equity: np.ndarray) -> float:
        """计算最大回撤"""
        if len(equity) == 0:
            return 0
        
        peak = equity[0]
        max_dd = 0
        
        for value in equity:
            if value > peak:
                peak = value
            
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _analyze_trades(self, trades: List[Trade]) -> Dict[str, Any]:
        """分析交易"""
        if not trades:
            return {}
        
        # 分离盈利和亏损交易
        profit_trades = [t for t in trades if t.pnl > 0]
        loss_trades = [t for t in trades if t.pnl <= 0]
        
        total_trades = len(trades)
        profit_count = len(profit_trades)
        loss_count = len(loss_trades)
        
        # 胜率
        win_rate = profit_count / total_trades if total_trades > 0 else 0
        
        # 总盈利和总亏损
        total_profit = sum(t.pnl for t in profit_trades)
        total_loss = abs(sum(t.pnl for t in loss_trades))
        
        # 盈利因子
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 平均盈利和平均亏损
        avg_win = total_profit / profit_count if profit_count > 0 else 0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0
        
        # 盈亏比
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
        
        return {
            "total_trades": total_trades,
            "profit_trades": profit_count,
            "loss_trades": loss_count,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_loss_ratio": profit_loss_ratio
        }

# ==================== 增强版回测引擎 ====================

class EnhancedBacktester:
    """增强版回测引擎"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 交易成本模型
        self.commission_model = CommissionModel(
            commission_rate=config.get("commission", 0.0003),
            stamp_tax=config.get("stamp_tax", 0.001),
            transfer_fee=config.get("transfer_fee", 0.00002)
        )
        
        # 滑点模型
        self.slippage_model = SlippageModel(
            slippage_type=config.get("slippage_type", "fixed"),
            slippage_value=config.get("slippage", 0.001)
        )
        
        # 市场限制
        self.market_constraints = MarketConstraints(
            tplus1=config.get("tplus1", True),
            price_limit=config.get("price_limit", True),
            min_trade_units=config.get("min_trade_units", 100),
            max_position_per_stock=config.get("max_position_per_stock", 0.1)
        )
        
        # 绩效分析器
        self.performance_analyzer = PerformanceAnalyzer()
        
        # 仓位管理和风险控制（将在运行时注入）
        self.position_manager = None
        self.risk_manager = None
        
        # 状态
        self.current_date = None
        self.equity_curve = []
        self.trade_log = []
        
        logger.info("增强版回测引擎初始化完成")
    
    def set_position_manager(self, position_manager):
        """设置仓位管理器"""
        self.position_manager = position_manager
    
    def set_risk_manager(self, risk_manager):
        """设置风险控制器"""
        self.risk_manager = risk_manager
    
    def run_backtest(self, strategy, data: pd.DataFrame,
                    initial_capital: float = 100000) -> BacktestResult:
        """运行增强回测"""
        logger.info(f"开始回测，初始资金: {initial_capital:.2f}")
        
        # 初始化投资组合
        portfolio = Portfolio(
            initial_capital=initial_capital,
            available_cash=initial_capital
        )
        
        # 准备数据
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        # 按日期排序
        data = data.sort_index()
        
        # 回测主循环
        dates = data.index.unique()
        equity_records = []
        
        for i, date in enumerate(dates):
            self.current_date = date
            
            # 获取当日数据
            daily_data = data.loc[date]
            if isinstance(daily_data, pd.Series):
                daily_data = daily_data.to_frame().T
            
            # 生成交易信号
            signals = strategy.generate_signals(daily_data)
            
            # 如果没有仓位管理和风险控制，使用简单逻辑
            if self.position_manager is None or self.risk_manager is None:
                trades = self._simple_trading_logic(signals, portfolio, daily_data)
            else:
                # 完整的闭环逻辑
                trades = self._closed_loop_trading(signals, portfolio, daily_data)
            
            # 执行交易
            executed_trades = self._execute_trades(trades, portfolio, daily_data)
            
            # 更新投资组合
            market_prices = self._extract_market_prices(daily_data)
            portfolio.update(executed_trades, market_prices)
            
            # 记录净值
            equity_records.append({
                "date": date,
                "total_assets": portfolio.total_assets,
                "available_cash": portfolio.available_cash,
                "market_value": portfolio.market_value,
                "total_pnl": portfolio.total_pnl
            })
            
            # 记录交易
            self.trade_log.extend(executed_trades)
            
            # 进度显示
            if (i + 1) % 50 == 0 or i == len(dates) - 1:
                logger.info(f"进度: {i+1}/{len(dates)}，总资产: {portfolio.total_assets:.2f}")
        
        # 构建净值曲线
        equity_df = pd.DataFrame(equity_records)
        equity_df.set_index("date", inplace=True)
        
        # 计算绩效指标
        performance_metrics = self.performance_analyzer.calculate_metrics(
            equity_df, self.trade_log
        )
        
        # 计算风险指标
        risk_metrics = self._calculate_risk_metrics(equity_df)
        
        # 交易分析
        trade_analysis = self.performance_analyzer._analyze_trades(self.trade_log)
        
        # 构建回测结果
        result = BacktestResult(
            portfolio=portfolio,
            trades=self.trade_log,
            equity_curve=equity_df,
            performance_metrics=performance_metrics,
            risk_metrics=risk_metrics,
            trade_analysis=trade_analysis
        )
        
        logger.info(f"回测完成，最终资产: {portfolio.total_assets:.2f}，总收益率: {performance_metrics.get('total_return', 0):.2%}")
        
        return result
    
    def _simple_trading_logic(self, signals, portfolio, daily_data) -> List[Order]:
        """简单交易逻辑（用于测试）"""
        orders = []
        
        # 这里实现一个简单的交易逻辑
        # 实际使用时应该使用完整的仓位管理和风险控制
        
        return orders
    
    def _closed_loop_trading(self, signals, portfolio, daily_data) -> List[Order]:
        """闭环交易逻辑"""
        orders = []
        
        # 1. 使用仓位管理器计算具体仓位
        if self.position_manager:
            position_decisions = self.position_manager.calculate_positions(
                signals, portfolio, daily_data
            )
        else:
            position_decisions = []
        
        # 2. 使用风险控制器检查风险
        if self.risk_manager:
            for decision in position_decisions:
                risk_check = self.risk_manager.check_risk(
                    decision, portfolio, daily_data
                )
                
                # 如果风险检查通过，生成订单
                if risk_check.passed:
                    order = Order(
                        order_id=f"order_{len(orders)}_{self.current_date.strftime('%Y%m%d')}",
                        symbol=decision.symbol,
                        side=OrderSide.BUY if decision.action == "buy" else OrderSide.SELL,
                        quantity=decision.quantity,
                        price=decision.price,
                        order_time=self.current_date
                    )
                    orders.append(order)
        
        return orders
    
    def _execute_trades(self, orders: List[Order], portfolio: Portfolio,
                       daily_data: pd.DataFrame) -> List[Trade]:
        """执行交易（考虑成本、滑点、限制）"""
        executed_trades = []
        
        for order in orders:
            # 检查订单有效性
            market_data = self._prepare_market_data(order.symbol, daily_data)
            is_valid, message = self.market_constraints.check_order_validity(
                order, portfolio, market_data
            )
            
            if not is_valid:
                logger.warning(f"订单无效: {message}")
                order.status = OrderStatus.REJECTED
                continue
            
            # 应用滑点
            filled_price = self.slippage_model.apply_slippage(order, market_data)
            
            # 完全成交
            order.filled_quantity = order.quantity
            order.filled_price = filled_price
            
            # 计算手续费
            order.commission = self.commission_model.calculate_commission(order)
            
            # 计算滑点成本
            order.slippage = abs(filled_price - order.price) * order.quantity
            
            # 更新订单状态
            order.status = OrderStatus.FILLED
            
            # 创建交易记录
            trade = Trade(
                trade_id=f"trade_{len(executed_trades)}_{self.current_date.strftime('%Y%m%d')}",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.filled_quantity,
                price=order.filled_price,
                trade_time=self.current_date,
                commission=order.commission,
                slippage=order.slippage
            )
            
            executed_trades.append(trade)
        
        return executed_trades
    
    def _extract_market_prices(self, daily_data: pd.DataFrame) -> Dict[str, float]:
        """从日数据中提取市场价格"""
        prices = {}
        
        if isinstance(daily_data, pd.DataFrame):
            for symbol in daily_data.columns:
                if "close" in symbol.lower() or "price" in symbol.lower():
                    prices[symbol] = daily_data[symbol].iloc[0] if len(daily_data) > 0 else 0
        
        return prices
    
    def _prepare_market_data(self, symbol: str, daily_data: pd.DataFrame) -> Dict:
        """准备市场数据"""
        market_data = {}
        
        # 这里可以添加更多的市场数据，如波动率、涨跌停价格等
        # 实际使用时应该从数据源获取
        
        return market_data
    
    def _calculate_risk_metrics(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """计算风险指标"""
        if len(equity_curve) < 2:
            return {}
        
        equity = equity_curve["total_assets"].values
        returns = np.diff(equity) / equity[:-1]
        
        # VaR (Value at Risk)
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else 0
        var_99 = np.percentile(returns, 1) if len(returns) > 0 else 0
        
        # CVaR (Conditional VaR)
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else 0
        cvar_99 = returns[returns <= var_99].mean() if len(returns[returns <= var_99]) > 0 else 0
        
        # 下行波动率
        downside_returns = returns[returns < 0]
        downside_volatility = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 1 else 0
        
        # 最大单日亏损
        max_daily_loss = np.min(returns) if len(returns) > 0 else 0
        
        # 亏损日比例
        loss_days_ratio = len(downside_returns) / len(returns) if len(returns) > 0 else 0
        
        return {
            "var_95": var_95,
            "var_99": var_99,
            "cvar_95": cvar_95,
            "cvar_99": cvar_99,
            "downside_volatility": downside_volatility,
            "max_daily_loss": max_daily_loss,
            "loss_days_ratio": loss_days_ratio
        }

# ==================== 测试函数 ====================

def test_enhanced_backtester():
    """测试增强版回测引擎"""
    print("测试增强版回测引擎...")
    
    # 创建配置
    config = {
        "commission": 0.0003,
        "stamp_tax": 0.001,
        "transfer_fee": 0.00002,
        "slippage_type": "fixed",
        "slippage": 0.001,
        "tplus1": True,
        "price_limit": True,
        "min_trade_units": 100,
        "max_position_per_stock": 0.1
    }
    
    # 创建回测引擎
    backtester = EnhancedBacktester(config)
    
    # 创建测试数据
    dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
    n_days = len(dates)
    
    # 生成随机价格数据
    np.random.seed(42)
    price = 100 + np.cumsum(np.random.randn(n_days) * 2)
    
    data = pd.DataFrame({
        "close": price,
        "open": price * (1 + np.random.randn(n_days) * 0.01),
        "high": price * (1 + np.random.randn(n_days) * 0.02),
        "low": price * (1 + np.random.randn(n_days) * 0.02),
        "volume": np.random.randint(1000000, 10000000, n_days)
    }, index=dates)
    
    # 创建简单策略
    class SimpleStrategy:
        def generate_signals(self, data):
            # 简单策略：价格高于5日均线时买入，低于时卖出
            signals = []
            
            if isinstance(data, pd.DataFrame) and len(data) > 5:
                current_price = data["close"].iloc[-1]
                ma5 = data["close"].rolling(5).mean().iloc[-1]
                
                if current_price > ma5 * 1.02:
                    signals.append({
                        "symbol": "TEST",
                        "action": "buy",
                        "strength": 1.0
                    })
                elif current_price < ma5 * 0.98:
                    signals.append({
                        "symbol": "TEST",
                        "action": "sell",
                        "strength": 1.0
                    })
            
            return signals
    
    strategy = SimpleStrategy()
    
    # 运行回测
    result = backtester.run_backtest(strategy, data, initial_capital=100000)
    
    # 打印结果
    print("\n回测结果:")
    print(f"最终资产: {result.portfolio.total_assets:.2f}")
    print(f"总收益率: {result.performance_metrics.get('total_return', 0):.2%}")
    print(f"年化收益率: {result.performance_metrics.get('annual_return', 0):.2%}")
    print(f"夏普比率: {result.performance_metrics.get('sharpe_ratio', 0):.2f}")
    print(f"最大回撤: {result.performance_metrics.get('max_drawdown', 0):.2%}")
    print(f"总交易次数: {result.performance_metrics.get('total_trades', 0)}")
    print(f"胜率: {result.performance_metrics.get('win_rate', 0):.2%}")
    
    return result

if __name__ == "__main__":
    test_enhanced_backtester()