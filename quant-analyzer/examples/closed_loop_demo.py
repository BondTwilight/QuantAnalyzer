"""
闭环量化交易系统演示脚本
展示系统的完整工作流程
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.closed_loop.closed_loop_system import ClosedLoopSystem, TradingSignal
from core.closed_loop.position_manager import PositionDecision
from core.closed_loop.risk_manager import AccountInfo, MarketData


def create_sample_data():
    """创建样本数据"""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
    n_days = len(dates)
    
    # 创建样本数据
    data = pd.DataFrame({
        'date': dates,
        'open': np.random.normal(100, 10, n_days),
        'high': np.random.normal(105, 10, n_days),
        'low': np.random.normal(95, 10, n_days),
        'close': np.random.normal(100, 10, n_days),
        'volume': np.random.randint(1000000, 10000000, n_days),
        'returns': np.random.normal(0.0005, 0.02, n_days)
    })
    
    # 计算技术指标
    data['sma_20'] = data['close'].rolling(window=20).mean()
    data['sma_50'] = data['close'].rolling(window=50).mean()
    data['rsi'] = 50 + np.random.normal(0, 10, n_days)  # 简化RSI
    
    return data


def create_sample_strategy_config():
    """创建样本策略配置"""
    return {
        "name": "双均线策略",
        "type": "trend_following",
        "description": "简单的双均线趋势跟踪策略",
        "params": {
            "fast_period": 20,
            "slow_period": 50,
            "entry_threshold": 0.01,
            "exit_threshold": -0.01
        },
        "signal_generation": {
            "buy_signal": "fast_ma > slow_ma and price > fast_ma * (1 + entry_threshold)",
            "sell_signal": "fast_ma < slow_ma or price < entry_price * (1 - exit_threshold)"
        },
        "position_sizing": "fixed",
        "risk_management": {
            "stop_loss": 0.08,
            "take_profit": 0.2,
            "max_position_size": 0.1
        }
    }


def create_param_space():
    """创建参数空间"""
    return {
        "fast_period": [10, 15, 20, 25, 30],
        "slow_period": [40, 45, 50, 55, 60],
        "entry_threshold": [0.005, 0.01, 0.015, 0.02],
        "exit_threshold": [-0.005, -0.01, -0.015, -0.02]
    }


def demo_full_workflow():
    """演示完整工作流程"""
    print("=" * 60)
    print("闭环量化交易系统完整工作流程演示")
    print("=" * 60)
    
    # 1. 创建系统
    print("\n1. 创建闭环量化交易系统...")
    system = ClosedLoopSystem()
    print("✓ 系统创建完成")
    
    # 2. 启动系统
    print("\n2. 启动系统...")
    system.start()
    print("✓ 系统启动完成")
    
    # 3. 获取系统状态
    print("\n3. 获取系统状态...")
    status = system.get_system_status()
    print(f"   运行状态: {'运行中' if status['is_running'] else '已停止'}")
    print(f"   模块状态: {len(status['modules'])}个模块已加载")
    print("✓ 系统状态获取完成")
    
    # 4. 创建样本数据
    print("\n4. 创建样本数据...")
    sample_data = create_sample_data()
    print(f"   数据范围: {sample_data['date'].iloc[0].date()} 到 {sample_data['date'].iloc[-1].date()}")
    print(f"   数据行数: {len(sample_data)}")
    print("✓ 样本数据创建完成")
    
    # 5. 创建策略配置
    print("\n5. 创建策略配置...")
    strategy_config = create_sample_strategy_config()
    print(f"   策略名称: {strategy_config['name']}")
    print(f"   策略类型: {strategy_config['type']}")
    print("✓ 策略配置创建完成")
    
    # 6. 运行回测
    print("\n6. 运行回测...")
    backtest_result = system.run_backtest(strategy_config, sample_data)
    print(f"   总收益: {backtest_result.performance_metrics.get('total_return', 0):.2%}")
    print(f"   年化收益: {backtest_result.performance_metrics.get('annual_return', 0):.2%}")
    print(f"   夏普比率: {backtest_result.performance_metrics.get('sharpe_ratio', 0):.2f}")
    print(f"   最大回撤: {backtest_result.performance_metrics.get('max_drawdown', 0):.2%}")
    print("✓ 回测完成")
    
    # 7. 优化策略参数
    print("\n7. 优化策略参数...")
    param_space = create_param_space()
    optimization_result = system.optimize_strategy(strategy_config, param_space, sample_data)
    print(f"   最佳参数: {optimization_result['best_params']}")
    print(f"   最佳分数: {optimization_result['best_score']:.4f}")
    print(f"   优化耗时: {optimization_result['optimization_time']:.2f}秒")
    print("✓ 策略优化完成")
    
    # 8. 使用优化后的参数运行回测
    print("\n8. 使用优化后的参数运行回测...")
    optimized_config = strategy_config.copy()
    optimized_config["params"] = optimization_result["best_params"]
    optimized_backtest = system.run_backtest(optimized_config, sample_data)
    print(f"   优化后总收益: {optimized_backtest.performance_metrics.get('total_return', 0):.2%}")
    print(f"   优化后夏普比率: {optimized_backtest.performance_metrics.get('sharpe_ratio', 0):.2f}")
    
    # 计算优化效果
    improvement = (
        optimized_backtest.performance_metrics.get('sharpe_ratio', 0) - 
        backtest_result.performance_metrics.get('sharpe_ratio', 0)
    )
    print(f"   夏普比率提升: {improvement:.4f}")
    print("✓ 优化后回测完成")
    
    # 9. 处理交易信号
    print("\n9. 处理交易信号...")
    
    # 创建多个交易信号
    test_signals = [
        TradingSignal(
            symbol="000001.SZ",
            direction="buy",
            strength=0.8,
            reason="双均线金叉",
            timestamp=datetime.now(),
            source="strategy"
        ),
        TradingSignal(
            symbol="000002.SZ",
            direction="sell",
            strength=0.6,
            reason="达到止盈点",
            timestamp=datetime.now(),
            source="strategy"
        ),
        TradingSignal(
            symbol="000003.SZ",
            direction="hold",
            strength=0.3,
            reason="趋势不明",
            timestamp=datetime.now(),
            source="strategy"
        )
    ]
    
    decisions = []
    for i, signal in enumerate(test_signals):
        print(f"   处理信号 {i+1}: {signal.symbol} {signal.direction}")
        decision = system.process_trading_signal(signal)
        if decision:
            decisions.append(decision)
            print(f"     → 决策: {decision.action} {decision.quantity}股 @ {decision.price:.2f}")
        else:
            print(f"     → 被风控拒绝")
    
    print(f"   成功处理 {len(decisions)}/{len(test_signals)} 个信号")
    print("✓ 交易信号处理完成")
    
    # 10. 生成报告
    print("\n10. 生成系统报告...")
    report = system.generate_report("demo")
    print(f"   报告类型: {report['report_type']}")
    print(f"   交易统计: {report['trading_summary']['total_trades']} 笔交易")
    print(f"   绩效统计: {len(report['performance_summary']['recent_performance'])} 个策略记录")
    print("✓ 报告生成完成")
    
    # 11. 保存系统状态
    print("\n11. 保存系统状态...")
    system.save_state("demo_system_state.json")
    print("✓ 系统状态已保存到 demo_system_state.json")
    
    # 12. 停止系统
    print("\n12. 停止系统...")
    system.stop()
    print("✓ 系统停止完成")
    
    # 总结
    print("\n" + "=" * 60)
    print("演示总结")
    print("=" * 60)
    print(f"1. 系统创建: 成功")
    print(f"2. 模块初始化: {len(status['modules'])} 个模块")
    print(f"3. 回测运行: 原始策略夏普比率 {backtest_result.performance_metrics.get('sharpe_ratio', 0):.2f}")
    print(f"4. 策略优化: 提升 {improvement:.4f} 夏普比率")
    print(f"5. 交易处理: {len(decisions)} 个成功决策")
    print(f"6. 报告生成: {report['report_type']} 报告")
    print(f"7. 状态保存: 已保存到文件")
    print("\n✓ 闭环量化交易系统演示完成！")


def demo_individual_modules():
    """演示单个模块功能"""
    print("\n" + "=" * 60)
    print("单个模块功能演示")
    print("=" * 60)
    
    # 创建系统但不启动
    system = ClosedLoopSystem()
    
    # 演示仓位管理模块
    print("\n1. 仓位管理模块演示")
    print("-" * 40)
    
    # 创建测试信号
    test_signal = TradingSignal(
        symbol="000001.SZ",
        direction="buy",
        strength=0.75,
        reason="测试信号",
        timestamp=datetime.now(),
        source="demo"
    )
    
    # 创建测试账户信息
    test_account = AccountInfo(
        total_assets=1000000,
        available_cash=500000,
        total_positions_value=500000,
        total_market_value=1000000,
        total_pnl=50000,
        today_pnl=1000
    )
    
    # 创建测试市场数据
    test_market = MarketData(
        symbol="000001.SZ",
        current_price=50.0,
        high_price=52.0,
        low_price=48.0,
        volume=1000000,
        market_cap=10000000000,
        volatility=0.25,
        trend_strength=0.6
    )
    
    # 使用仓位管理模块
    position_decision = system.position_manager.decide_position(
        signal=test_signal,
        account_info=test_account,
        market_data=test_market
    )
    
    print(f"   信号: {test_signal.symbol} {test_signal.direction}")
    print(f"   仓位决策: {position_decision.action}")
    print(f"   数量: {position_decision.quantity}")
    print(f"   价值: {position_decision.value:.2f}")
    print(f"   方法: {position_decision.method}")
    print("✓ 仓位管理演示完成")
    
    # 演示风险管理模块
    print("\n2. 风险管理模块演示")
    print("-" * 40)
    
    risk_assessment = system.risk_manager.assess_risk(
        decision=position_decision,
        account_info=test_account,
        market_data=test_market,
        signal=test_signal
    )
    
    print(f"   风险评估: {'通过' if risk_assessment.is_approved else '拒绝'}")
    print(f"   风险分数: {risk_assessment.risk_score:.4f}")
    print(f"   止损价格: {risk_assessment.stop_loss_price:.2f}")
    print(f"   止盈价格: {risk_assessment.take_profit_price:.2f}")
    
    if not risk_assessment.is_approved:
        print(f"   拒绝原因: {risk_assessment.rejection_reason}")
    
    print("✓ 风险管理演示完成")
    
    # 演示自动优化模块
    print("\n3. 自动优化模块演示")
    print("-" * 40)
    
    # 简单的目标函数
    def demo_objective(params):
        x = params.get("x", 0)
        y = params.get("y", 0)
        return -(x-0.5)**2 - (y-0.5)**2
    
    param_space = {
        "x": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
        "y": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    }
    
    optimization_result = system.auto_optimizer.optimize_parameters(
        param_space=param_space,
        objective_function=demo_objective
    )
    
    print(f"   优化方法: {optimization_result.method.value}")
    print(f"   最佳参数: {optimization_result.best_params}")
    print(f"   最佳分数: {optimization_result.best_score:.4f}")
    print(f"   优化耗时: {optimization_result.optimization_time:.2f}秒")
    print("✓ 自动优化演示完成")
    
    # 演示监控报警模块
    print("\n4. 监控报警模块演示")
    print("-" * 40)
    
    from core.closed_loop.monitor_alert import Alert, AlertLevel
    
    # 发送测试报警
    test_alert = Alert(
        level=AlertLevel.INFO,
        title="演示报警",
        message="这是一个测试报警消息",
        source="demo",
        timestamp=datetime.now()
    )
    
    system.monitor_alert.send_alert(test_alert)
    
    # 获取报警统计
    alert_stats = system.monitor_alert.get_alert_stats()
    print(f"   报警统计: {alert_stats}")
    print("✓ 监控报警演示完成")
    
    print("\n✓ 所有模块演示完成！")


def main():
    """主函数"""
    print("闭环量化交易系统演示")
    print("=" * 60)
    
    try:
        # 演示完整工作流程
        demo_full_workflow()
        
        # 演示单个模块功能
        demo_individual_modules()
        
        print("\n" + "=" * 60)
        print("演示成功完成！")
        print("=" * 60)
        print("\n生成的文件:")
        print("  - demo_system_state.json: 系统状态文件")
        print("  - auto_optimizer_state.pkl: 优化器状态文件")
        print("\n下一步:")
        print("  1. 修改 config/closed_loop_config.yaml 配置实际参数")
        print("  2. 使用真实数据运行系统")
        print("  3. 连接实盘交易接口")
        print("  4. 配置监控报警渠道")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()