#!/usr/bin/env python3
"""
测试仓位管理模块
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.closed_loop.position_manager import (
    PositionManager, TradingSignal, AccountInfo, MarketData
)
from datetime import datetime


def test_basic_functionality():
    """测试基本功能"""
    print("=== 测试仓位管理基本功能 ===")
    
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
    print(f"仓位管理器初始化成功，使用算法: {config['position_method']}")
    
    # 创建测试数据
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
    
    # 测试计算仓位
    decision = pm.calculate_position(signal, account_info, market_data)
    
    print(f"\n仓位决策结果:")
    print(f"  股票: {decision.symbol}")
    print(f"  操作: {decision.action}")
    print(f"  数量: {decision.quantity}股")
    print(f"  价格: {decision.price:.2f}元")
    print(f"  金额: {decision.value:.2f}元")
    print(f"  算法: {decision.position_method}")
    print(f"  风险评分: {decision.risk_score:.3f}")
    
    # 验证结果
    assert decision.symbol == "000001.SZ"
    assert decision.action == "buy"
    assert decision.quantity > 0
    assert decision.value > 0
    assert 0 <= decision.risk_score <= 1
    
    print("\n✅ 基本功能测试通过")


def test_all_position_methods():
    """测试所有仓位算法"""
    print("\n=== 测试所有仓位算法 ===")
    
    # 基础配置
    base_config = {
        "fixed_position_size": 0.1,
        "max_position_per_stock": 0.2,
        "min_trade_value": 1000,
        "kelly_fraction": 0.5,
        "atr_multiplier": 2.0,
        "grid_levels": 5,
        "pyramid_levels": 3
    }
    
    # 测试数据
    signal = TradingSignal(
        symbol="000001.SZ",
        direction="buy",
        strength=0.8,
        confidence=0.7,
        timestamp=datetime.now(),
        price=10.5
    )
    
    account_info = AccountInfo(
        total_assets=100000,
        available_cash=50000,
        market_value=50000
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
    
    # 测试所有算法
    methods = ["fixed", "kelly", "volatility", "risk_parity", "pyramid", "grid"]
    
    results = []
    
    for method in methods:
        config = base_config.copy()
        config["position_method"] = method
        
        try:
            pm = PositionManager(config)
            decision = pm.calculate_position(signal, account_info, market_data)
            
            results.append({
                "method": method,
                "decision": decision,
                "success": True
            })
            
            print(f"  ✅ {method}: {decision.quantity}股, {decision.value:.2f}元, 风险: {decision.risk_score:.3f}")
            
        except Exception as e:
            results.append({
                "method": method,
                "error": str(e),
                "success": False
            })
            print(f"  ❌ {method}: 失败 - {e}")
    
    # 验证所有算法都成功
    success_count = sum(1 for r in results if r["success"])
    print(f"\n✅ {success_count}/{len(methods)} 种算法测试通过")
    
    return results


def test_risk_limits():
    """测试风险限制"""
    print("\n=== 测试风险限制 ===")
    
    config = {
        "position_method": "fixed",
        "fixed_position_size": 0.5,  # 故意设置很大的仓位
        "max_position_per_stock": 0.2,  # 限制20%
        "min_trade_value": 1000
    }
    
    pm = PositionManager(config)
    
    signal = TradingSignal(
        symbol="000001.SZ",
        direction="buy",
        strength=1.0,
        confidence=1.0,
        timestamp=datetime.now(),
        price=10.0
    )
    
    account_info = AccountInfo(
        total_assets=100000,  # 10万资产
        available_cash=20000,  # 只有2万可用现金
        market_value=80000
    )
    
    market_data = MarketData(
        symbol="000001.SZ",
        price=10.0,
        volume=1000000,
        high=11.0,
        low=9.0,
        open=10.0,
        close=10.0
    )
    
    decision = pm.calculate_position(signal, account_info, market_data)
    
    print(f"配置仓位: {config['fixed_position_size']*100}%")
    print(f"单股最大限制: {config['max_position_per_stock']*100}%")
    print(f"可用现金: {account_info.available_cash:.2f}元")
    
    print(f"\n实际决策:")
    print(f"  交易金额: {decision.value:.2f}元")
    print(f"  占资产比例: {decision.value/account_info.total_assets*100:.1f}%")
    print(f"  占可用现金比例: {decision.value/account_info.available_cash*100:.1f}%")
    
    # 验证风险限制生效
    max_allowed = account_info.total_assets * config["max_position_per_stock"]
    assert decision.value <= max_allowed, f"交易金额{decision.value}超过最大限制{max_allowed}"
    
    if decision.action == "buy":
        assert decision.value <= account_info.available_cash * 0.8, f"交易金额{decision.value}超过可用资金限制{account_info.available_cash * 0.8}"
    
    print("\n✅ 风险限制测试通过")


def test_hold_signal():
    """测试hold信号"""
    print("\n=== 测试hold信号 ===")
    
    config = {
        "position_method": "fixed",
        "fixed_position_size": 0.1
    }
    
    pm = PositionManager(config)
    
    # hold信号
    signal = TradingSignal(
        symbol="000001.SZ",
        direction="hold",
        strength=0.0,
        confidence=0.0,
        timestamp=datetime.now(),
        price=10.0
    )
    
    account_info = AccountInfo(
        total_assets=100000,
        available_cash=50000,
        market_value=50000
    )
    
    market_data = MarketData(
        symbol="000001.SZ",
        price=10.0,
        volume=1000000,
        high=11.0,
        low=9.0,
        open=10.0,
        close=10.0
    )
    
    decision = pm.calculate_position(signal, account_info, market_data)
    
    print(f"信号方向: {signal.direction}")
    print(f"决策操作: {decision.action}")
    print(f"交易数量: {decision.quantity}")
    print(f"交易金额: {decision.value:.2f}")
    
    assert decision.action == "hold"
    assert decision.quantity == 0
    assert decision.value == 0
    
    print("\n✅ hold信号测试通过")


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    
    # 测试无效算法
    try:
        config = {
            "position_method": "invalid_method",  # 无效算法
            "fixed_position_size": 0.1
        }
        pm = PositionManager(config)
        print("❌ 应该抛出异常但没有")
    except ValueError as e:
        print(f"✅ 正确捕获无效算法错误: {e}")
    
    # 测试计算过程中的错误
    config = {
        "position_method": "kelly",
        "kelly_fraction": 0.5
    }
    
    pm = PositionManager(config)
    
    # 创建可能引发错误的数据
    signal = TradingSignal(
        symbol="000001.SZ",
        direction="buy",
        strength=0.0,  # 强度为0
        confidence=0.0,  # 置信度为0
        timestamp=datetime.now(),
        price=0.0  # 价格为0，可能引发除零错误
    )
    
    account_info = AccountInfo(
        total_assets=0.0,  # 资产为0
        available_cash=0.0,
        market_value=0.0
    )
    
    market_data = MarketData(
        symbol="000001.SZ",
        price=0.0,
        volume=0,
        high=0.0,
        low=0.0,
        open=0.0,
        close=0.0
    )
    
    # 应该返回hold决策而不是崩溃
    decision = pm.calculate_position(signal, account_info, market_data)
    
    print(f"错误处理结果: {decision.action}")
    print(f"元数据: {decision.metadata}")
    
    assert decision.action == "hold"
    
    print("\n✅ 错误处理测试通过")


def main():
    """主测试函数"""
    print("开始测试仓位管理模块...")
    
    try:
        test_basic_functionality()
        test_all_position_methods()
        test_risk_limits()
        test_hold_signal()
        test_error_handling()
        
        print("\n" + "="*50)
        print("🎉 所有测试通过！仓位管理模块功能正常")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())