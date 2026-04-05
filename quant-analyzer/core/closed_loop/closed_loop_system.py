"""
闭环量化交易系统集成模块
将所有核心模块整合到一个完整的系统中
"""

import logging
import json
import yaml
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np

# 导入核心模块
from .position_manager import PositionManager, PositionDecision, TradingSignal
from .risk_manager import RiskManager, RiskAssessment, AccountInfo, MarketData
from .enhanced_backtester import EnhancedBacktester, BacktestConfig, BacktestResult
from .trading_interface import UnifiedTradingInterface, TradingInterfaceType, Order, OrderStatus
from .monitor_alert import MonitorAlert, Alert, AlertChannel, AlertLevel
from .auto_optimizer import AutoOptimizer, OptimizationMethod, ModelType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """系统配置数据类"""
    # 仓位管理配置
    position_config: Dict[str, Any]
    
    # 风险管理配置
    risk_config: Dict[str, Any]
    
    # 回测配置
    backtest_config: Dict[str, Any]
    
    # 交易接口配置
    trading_config: Dict[str, Any]
    
    # 监控报警配置
    monitor_config: Dict[str, Any]
    
    # 自动优化配置
    optimization_config: Dict[str, Any]
    
    # 系统通用配置
    system_config: Dict[str, Any]


@dataclass
class TradingDecision:
    """交易决策数据类"""
    timestamp: datetime
    symbol: str
    action: str  # buy/sell/hold
    quantity: float
    price: float
    value: float
    reason: str
    confidence: float
    risk_score: float
    position_method: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class SystemStatus:
    """系统状态数据类"""
    timestamp: datetime
    is_running: bool
    active_strategies: List[str]
    total_trades_today: int
    total_pnl_today: float
    total_positions: int
    system_health: Dict[str, float]  # CPU, memory, disk usage
    alerts_count: Dict[str, int]  # 各等级报警数量
    optimization_status: str


class ClosedLoopSystem:
    """闭环量化交易系统"""
    
    def __init__(self, config_file: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        初始化闭环系统
        
        Args:
            config_file: 配置文件路径（YAML或JSON）
            config_dict: 配置字典（如果提供了config_file，则忽略此参数）
        """
        # 加载配置
        if config_file:
            self.config = self._load_config_from_file(config_file)
        elif config_dict:
            self.config = SystemConfig(**config_dict)
        else:
            # 使用默认配置
            self.config = self._create_default_config()
        
        logger.info("开始初始化闭环量化交易系统...")
        
        # 初始化核心模块
        self._init_modules()
        
        # 系统状态
        self.status = SystemStatus(
            timestamp=datetime.now(),
            is_running=False,
            active_strategies=[],
            total_trades_today=0,
            total_pnl_today=0.0,
            total_positions=0,
            system_health={},
            alerts_count={"info": 0, "warning": 0, "error": 0},
            optimization_status="idle"
        )
        
        # 交易历史
        self.trading_history: List[TradingDecision] = []
        self.performance_history: List[Dict[str, float]] = []
        
        logger.info("闭环量化交易系统初始化完成")
    
    def _load_config_from_file(self, config_file: str) -> SystemConfig:
        """从文件加载配置"""
        try:
            if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f)
            elif config_file.endswith('.json'):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {config_file}")
            
            return SystemConfig(**config_dict)
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            logger.info("使用默认配置")
            return self._create_default_config()
    
    def _create_default_config(self) -> SystemConfig:
        """创建默认配置"""
        return SystemConfig(
            position_config={
                "default_method": "fixed",
                "fixed_position_size": 0.1,  # 10%仓位
                "max_position_per_stock": 0.2,  # 单只股票最大仓位20%
                "max_total_position": 0.8,  # 总仓位最大80%
                "position_methods": ["fixed", "kelly", "volatility"]
            },
            risk_config={
                "max_drawdown_limit": 0.15,  # 最大回撤限制15%
                "daily_loss_limit": 0.05,  # 单日亏损限制5%
                "position_risk_limit": 0.02,  # 单笔交易风险限制2%
                "var_confidence": 0.95,  # VaR置信度
                "stop_loss_methods": ["fixed", "trailing", "atr"]
            },
            backtest_config={
                "initial_capital": 1000000,
                "commission_rate": 0.0003,  # 万三
                "slippage_rate": 0.0001,  # 万分之一滑点
                "benchmark": "000300.SH",  # 沪深300
                "start_date": "2023-01-01",
                "end_date": "2024-12-31"
            },
            trading_config={
                "interface_type": "simulation",  # 模拟交易
                "simulation_config": {
                    "initial_capital": 1000000,
                    "commission_rate": 0.0003,
                    "slippage_rate": 0.0001
                },
                "qmt_config": {
                    "account": "",
                    "password": "",
                    "server": "127.0.0.1"
                }
            },
            monitor_config={
                "alert_channels": ["log", "email"],
                "email_config": {
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "recipients": []
                },
                "monitoring_rules": {
                    "daily_loss_threshold": 0.03,
                    "drawdown_threshold": 0.1,
                    "sharpe_threshold": 1.0,
                    "position_concentration_threshold": 0.3
                },
                "check_interval_minutes": 5
            },
            optimization_config={
                "optimization_frequency": "weekly",
                "optimization_method": "random_search",
                "max_iterations": 100,
                "performance_threshold": 0.05,
                "model_update_frequency": "monthly"
            },
            system_config={
                "data_update_frequency": "daily",
                "trading_frequency": "daily",
                "report_frequency": "daily",
                "max_concurrent_strategies": 10,
                "system_check_interval_hours": 1
            }
        )
    
    def _init_modules(self):
        """初始化所有核心模块"""
        logger.info("初始化核心模块...")
        
        # 1. 仓位管理模块
        self.position_manager = PositionManager(self.config.position_config)
        logger.info("仓位管理模块初始化完成")
        
        # 2. 风险管理模块
        self.risk_manager = RiskManager(self.config.risk_config)
        logger.info("风险管理模块初始化完成")
        
        # 3. 回测增强模块
        self.backtester = EnhancedBacktester(self.config.backtest_config)
        logger.info("回测增强模块初始化完成")
        
        # 4. 交易接口模块
        self.trading_interface = UnifiedTradingInterface(
            interface_type=self.config.trading_config["interface_type"],
            config=self.config.trading_config
        )
        logger.info("交易接口模块初始化完成")
        
        # 5. 监控报警模块
        self.monitor_alert = MonitorAlert(self.config.monitor_config)
        logger.info("监控报警模块初始化完成")
        
        # 6. 自动优化模块
        self.auto_optimizer = AutoOptimizer(self.config.optimization_config)
        logger.info("自动优化模块初始化完成")
        
        logger.info("所有核心模块初始化完成")
    
    def start(self):
        """启动系统"""
        if self.status.is_running:
            logger.warning("系统已经在运行中")
            return
        
        logger.info("启动闭环量化交易系统...")
        
        # 更新系统状态
        self.status.is_running = True
        self.status.timestamp = datetime.now()
        
        # 启动监控
        self.monitor_alert.start_monitoring()
        
        # 发送系统启动报警
        self.monitor_alert.send_alert(
            Alert(
                level=AlertLevel.INFO,
                title="系统启动",
                message="闭环量化交易系统已启动",
                source="system",
                timestamp=datetime.now()
            )
        )
        
        logger.info("系统启动完成")
    
    def stop(self):
        """停止系统"""
        if not self.status.is_running:
            logger.warning("系统未在运行中")
            return
        
        logger.info("停止闭环量化交易系统...")
        
        # 更新系统状态
        self.status.is_running = False
        self.status.timestamp = datetime.now()
        
        # 停止监控
        self.monitor_alert.stop_monitoring()
        
        # 发送系统停止报警
        self.monitor_alert.send_alert(
            Alert(
                level=AlertLevel.INFO,
                title="系统停止",
                message="闭环量化交易系统已停止",
                source="system",
                timestamp=datetime.now()
            )
        )
        
        logger.info("系统停止完成")
    
    def process_trading_signal(self, signal: TradingSignal) -> Optional[TradingDecision]:
        """
        处理交易信号
        
        Args:
            signal: 交易信号
            
        Returns:
            TradingDecision: 交易决策，如果被风控拒绝则返回None
        """
        if not self.status.is_running:
            logger.warning("系统未运行，无法处理交易信号")
            return None
        
        logger.info(f"处理交易信号: {signal.symbol}, 方向: {signal.direction}, 强度: {signal.strength}")
        
        # 1. 获取账户信息
        account_info = self.trading_interface.get_account_info()
        
        # 2. 获取市场数据
        market_data = self._get_market_data(signal.symbol)
        
        # 3. 仓位决策
        position_decision = self.position_manager.decide_position(
            signal=signal,
            account_info=account_info,
            market_data=market_data
        )
        
        # 4. 风险评估
        risk_assessment = self.risk_manager.assess_risk(
            decision=position_decision,
            account_info=account_info,
            market_data=market_data,
            signal=signal
        )
        
        # 5. 检查风险限制
        if not risk_assessment.is_approved:
            logger.warning(f"交易被风控拒绝: {risk_assessment.rejection_reason}")
            
            # 发送风控拒绝报警
            self.monitor_alert.send_alert(
                Alert(
                    level=AlertLevel.WARNING,
                    title="交易被风控拒绝",
                    message=f"{signal.symbol}: {risk_assessment.rejection_reason}",
                    source="risk_manager",
                    timestamp=datetime.now()
                )
            )
            
            return None
        
        # 6. 创建交易决策
        trading_decision = TradingDecision(
            timestamp=datetime.now(),
            symbol=signal.symbol,
            action=position_decision.action,
            quantity=position_decision.quantity,
            price=market_data.current_price,
            value=position_decision.value,
            reason=signal.reason,
            confidence=signal.strength,
            risk_score=risk_assessment.risk_score,
            position_method=position_decision.method,
            stop_loss=risk_assessment.stop_loss_price,
            take_profit=risk_assessment.take_profit_price
        )
        
        # 7. 执行交易
        order_result = self.trading_interface.place_order(
            symbol=signal.symbol,
            action=trading_decision.action,
            quantity=trading_decision.quantity,
            price=trading_decision.price,
            order_type="limit"
        )
        
        if order_result.status == OrderStatus.FILLED:
            # 交易成功
            logger.info(f"交易执行成功: {signal.symbol}, 数量: {trading_decision.quantity}, 价格: {trading_decision.price}")
            
            # 更新系统状态
            self.status.total_trades_today += 1
            self.status.total_positions = len(self.trading_interface.get_positions())
            
            # 添加到交易历史
            self.trading_history.append(trading_decision)
            
            # 发送交易成功报警
            self.monitor_alert.send_alert(
                Alert(
                    level=AlertLevel.INFO,
                    title="交易执行成功",
                    message=f"{signal.symbol} {trading_decision.action} {trading_decision.quantity}股 @ {trading_decision.price}",
                    source="trading_interface",
                    timestamp=datetime.now()
                )
            )
            
            return trading_decision
            
        else:
            # 交易失败
            logger.error(f"交易执行失败: {order_result.error_message}")
            
            # 发送交易失败报警
            self.monitor_alert.send_alert(
                Alert(
                    level=AlertLevel.ERROR,
                    title="交易执行失败",
                    message=f"{signal.symbol}: {order_result.error_message}",
                    source="trading_interface",
                    timestamp=datetime.now()
                )
            )
            
            return None
    
    def run_backtest(self, strategy_config: Dict[str, Any], 
                    data: pd.DataFrame) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy_config: 策略配置
            data: 回测数据
            
        Returns:
            BacktestResult: 回测结果
        """
        logger.info(f"运行回测，策略: {strategy_config.get('name', 'unknown')}")
        
        # 创建回测配置
        backtest_config = BacktestConfig(
            strategy_config=strategy_config,
            data=data,
            **self.config.backtest_config
        )
        
        # 运行回测
        result = self.backtester.run_backtest(backtest_config)
        
        # 记录回测结果
        self.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "strategy_name": strategy_config.get("name", "unknown"),
            "total_return": result.performance_metrics.get("total_return", 0),
            "annual_return": result.performance_metrics.get("annual_return", 0),
            "sharpe_ratio": result.performance_metrics.get("sharpe_ratio", 0),
            "max_drawdown": result.performance_metrics.get("max_drawdown", 0),
            "win_rate": result.performance_metrics.get("win_rate", 0)
        })
        
        # 检查回测性能
        self._check_backtest_performance(result)
        
        logger.info(f"回测完成，总收益: {result.performance_metrics.get('total_return', 0):.2%}")
        
        return result
    
    def optimize_strategy(self, strategy_config: Dict[str, Any],
                         param_space: Dict[str, List[Any]],
                         data: pd.DataFrame) -> Dict[str, Any]:
        """
        优化策略参数
        
        Args:
            strategy_config: 策略配置
            param_space: 参数空间
            data: 优化数据
            
        Returns:
            Dict: 优化结果
        """
        logger.info(f"优化策略: {strategy_config.get('name', 'unknown')}")
        
        # 定义目标函数
        def objective_function(params: Dict[str, Any]) -> float:
            # 更新策略配置
            updated_config = strategy_config.copy()
            updated_config["params"] = params
            
            # 运行回测
            result = self.run_backtest(updated_config, data)
            
            # 使用夏普比率作为优化目标
            sharpe_ratio = result.performance_metrics.get("sharpe_ratio", 0)
            
            return sharpe_ratio
        
        # 运行优化
        optimization_result = self.auto_optimizer.optimize_parameters(
            param_space=param_space,
            objective_function=objective_function,
            method=OptimizationMethod(self.config.optimization_config["optimization_method"])
        )
        
        # 更新系统状态
        self.status.optimization_status = "completed"
        
        # 发送优化完成报警
        self.monitor_alert.send_alert(
            Alert(
                level=AlertLevel.INFO,
                title="策略优化完成",
                message=f"{strategy_config.get('name', 'unknown')}: 最佳夏普比率={optimization_result.best_score:.4f}",
                source="auto_optimizer",
                timestamp=datetime.now()
            )
        )
        
        return {
            "best_params": optimization_result.best_params,
            "best_score": optimization_result.best_score,
            "optimization_time": optimization_result.optimization_time
        }
    
    def _get_market_data(self, symbol: str) -> MarketData:
        """获取市场数据（简化版）"""
        # 这里应该从数据源获取实时数据
        # 简化实现：返回模拟数据
        return MarketData(
            symbol=symbol,
            current_price=100.0,  # 模拟价格
            high_price=105.0,
            low_price=95.0,
            volume=1000000,
            market_cap=1000000000,
            volatility=0.2,
            trend_strength=0.5
        )
    
    def _check_backtest_performance(self, result: BacktestResult):
        """检查回测性能，触发报警"""
        metrics = result.performance_metrics
        
        # 检查最大回撤
        max_drawdown = metrics.get("max_drawdown", 0)
        drawdown_threshold = self.config.monitor_config["monitoring_rules"]["drawdown_threshold"]
        
        if max_drawdown > drawdown_threshold:
            self.monitor_alert.send_alert(
                Alert(
                    level=AlertLevel.WARNING,
                    title="回测最大回撤过高",
                    message=f"最大回撤: {max_drawdown:.2%} > 阈值: {drawdown_threshold:.2%}",
                    source="backtester",
                    timestamp=datetime.now()
                )
            )
        
        # 检查夏普比率
        sharpe_ratio = metrics.get("sharpe_ratio", 0)
        sharpe_threshold = self.config.monitor_config["monitoring_rules"]["sharpe_threshold"]
        
        if sharpe_ratio < sharpe_threshold:
            self.monitor_alert.send_alert(
                Alert(
                    level=AlertLevel.WARNING,
                    title="回测夏普比率过低",
                    message=f"夏普比率: {sharpe_ratio:.2f} < 阈值: {sharpe_threshold:.2f}",
                    source="backtester",
                    timestamp=datetime.now()
                )
            )
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        # 更新系统健康状态
        self._update_system_health()
        
        # 更新报警计数
        self._update_alert_counts()
        
        # 转换为字典
        status_dict = asdict(self.status)
        status_dict["timestamp"] = self.status.timestamp.isoformat()
        
        # 添加模块状态
        status_dict["modules"] = {
            "position_manager": "active",
            "risk_manager": "active",
            "backtester": "active",
            "trading_interface": self.trading_interface.get_status(),
            "monitor_alert": self.monitor_alert.get_status(),
            "auto_optimizer": self.auto_optimizer.get_summary()
        }
        
        # 添加交易统计
        status_dict["trading_stats"] = {
            "total_trades": len(self.trading_history),
            "today_trades": self.status.total_trades_today,
            "total_positions": self.status.total_positions,
            "today_pnl": self.status.total_pnl_today
        }
        
        return status_dict
    
    def _update_system_health(self):
        """更新系统健康状态"""
        # 简化实现：模拟系统健康数据
        import psutil
        import os
        
        try:
            self.status.system_health = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
                "process_count": len(psutil.pids())
            }
        except Exception as e:
            logger.warning(f"获取系统健康状态失败: {e}")
            self.status.system_health = {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0,
                "process_count": 0
            }
    
    def _update_alert_counts(self):
        """更新报警计数"""
        # 从监控模块获取报警统计
        alert_stats = self.monitor_alert.get_alert_stats()
        
        self.status.alerts_count = {
            "info": alert_stats.get("info", 0),
            "warning": alert_stats.get("warning", 0),
            "error": alert_stats.get("error", 0)
        }
    
    def generate_report(self, report_type: str = "daily") -> Dict[str, Any]:
        """生成报告"""
        logger.info(f"生成{report_type}报告")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "report_type": report_type,
            "system_status": self.get_system_status(),
            "trading_summary": {
                "total_trades": len(self.trading_history),
                "recent_trades": [
                    {
                        "time": trade.timestamp.isoformat(),
                        "symbol": trade.symbol,
                        "action": trade.action,
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "value": trade.value
                    }
                    for trade in self.trading_history[-10:]  # 最近10笔交易
                ]
            },
            "performance_summary": {
                "total_strategies": len(self.performance_history),
                "recent_performance": self.performance_history[-5:] if self.performance_history else []
            },
            "risk_summary": self.risk_manager.get_risk_summary(),
            "optimization_summary": self.auto_optimizer.get_summary()
        }
        
        return report
    
    def save_state(self, filepath: str):
        """保存系统状态"""
        state = {
            "config": asdict(self.config),
            "trading_history": [
                asdict(trade) for trade in self.trading_history
            ],
            "performance_history": self.performance_history,
            "system_status": self.get_system_status(),
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存各模块状态
        state["modules"] = {
            "auto_optimizer": "auto_optimizer_state.pkl"
        }
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        # 保存优化器状态
        self.auto_optimizer.save_state("auto_optimizer_state.pkl")
        
        logger.info(f"系统状态已保存到 {filepath}")
    
    def load_state(self, filepath: str):
        """加载系统状态"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # 加载交易历史
            self.trading_history = []
            for trade_dict in state.get("trading_history", []):
                trade_dict["timestamp"] = datetime.fromisoformat(trade_dict["timestamp"])
                self.trading_history.append(TradingDecision(**trade_dict))
            
            # 加载性能历史
            self.performance_history = state.get("performance_history", [])
            
            # 加载优化器状态
            self.auto_optimizer.load_state("auto_optimizer_state.pkl")
            
            logger.info(f"系统状态已从 {filepath} 加载")
            
        except Exception as e:
            logger.error(f"加载系统状态失败: {e}")


def test_closed_loop_system():
    """测试闭环系统"""
    print("测试闭环量化交易系统...")
    
    # 创建系统
    system = ClosedLoopSystem()
    
    # 启动系统
    system.start()
    
    # 创建测试交易信号
    test_signal = TradingSignal(
        symbol="000001.SZ",
        direction="buy",
        strength=0.8,
        reason="测试信号",
        timestamp=datetime.now(),
        source="test"
    )
    
    # 处理交易信号
    decision = system.process_trading_signal(test_signal)
    
    if decision:
        print(f"交易决策: {decision.symbol} {decision.action} {decision.quantity}股")
    else:
        print("交易被风控拒绝")
    
    # 获取系统状态
    status = system.get_system_status()
    print(f"系统状态: 运行中={status['is_running']}, 今日交易数={status['trading_stats']['today_trades']}")
    
    # 生成报告
    report = system.generate_report("test")
    print(f"报告生成完成，类型: {report['report_type']}")
    
    # 停止系统
    system.stop()
    
    print("闭环系统测试完成！")


if __name__ == "__main__":
    test_closed_loop_system()