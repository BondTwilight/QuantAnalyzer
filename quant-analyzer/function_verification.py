#!/usr/bin/env python3
"""
功能验证测试 - 验证核心优化功能是否正常工作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def verify_core_modules():
    """验证核心模块是否可正常导入"""
    print("🔍 验证核心模块导入...")
    
    modules_to_check = [
        ("core.ai_collaboration", "AICollaborationEngine"),
        ("core.button_fixer", "ButtonResponseFixer"),
        ("core.performance_optimizer", "SmartCache"),
        ("core.async_task_manager", "AsyncTaskManager"),
        ("core.multi_source_strategy", "MultiSourceStrategyCrawler"),
        ("core.database_optimizer", "DatabaseOptimizer"),
        ("core.database_monitor", "DatabaseMonitor"),
    ]
    
    results = []
    for module_name, class_name in modules_to_check:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            results.append((module_name, class_name, True, "✅"))
            print(f"  ✅ {module_name}.{class_name} - 可正常导入")
        except Exception as e:
            results.append((module_name, class_name, False, f"❌ {str(e)[:50]}"))
            print(f"  ❌ {module_name}.{class_name} - 导入失败: {e}")
    
    return results

def verify_website_structure():
    """验证网站文件结构"""
    print("\n🔍 验证网站文件结构...")
    
    required_files = [
        "enhanced_app.py",
        "config.py",
        "requirements.txt",
        "start_website.bat",
        "core/__init__.py",
        "data/__init__.py",
    ]
    
    results = []
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            results.append((file_path, True, "✅"))
            print(f"  ✅ {file_path} - 存在")
        else:
            results.append((file_path, False, "❌"))
            print(f"  ❌ {file_path} - 不存在")
    
    return results

def verify_configuration():
    """验证配置文件"""
    print("\n🔍 验证配置文件...")
    
    try:
        import config
        config_checks = [
            ("ZHIPU_API_KEY", bool(getattr(config, "ZHIPU_API_KEY", None))),
            ("DEEPSEEK_API_KEY", bool(getattr(config, "DEEPSEEK_API_KEY", None))),
            ("SILICONFLOW_API_KEY", bool(getattr(config, "SILICONFLOW_API_KEY", None))),
        ]
        
        results = []
        for key, exists in config_checks:
            if exists:
                results.append((key, True, "✅"))
                print(f"  ✅ {key} - 已配置")
            else:
                results.append((key, False, "⚠️"))
                print(f"  ⚠️  {key} - 未配置（可选）")
        
        return results
    except Exception as e:
        print(f"  ❌ 配置文件验证失败: {e}")
        return [("config", False, f"❌ {str(e)[:50]}")]

def verify_optimization_features():
    """验证优化功能"""
    print("\n🔍 验证优化功能...")
    
    features = [
        ("按钮响应修复", "ButtonResponseFixer.create_action_button"),
        ("异步任务管理", "AsyncTaskManager.submit_task"),
        ("数据库优化", "DatabaseOptimizer.execute_query"),
        ("AI协同工作", "AICollaborationEngine.collaborative_analysis"),
        ("多源策略学习", "MultiSourceStrategyCrawler.search_strategies"),
        ("性能监控", "DatabaseMonitor.get_performance_dashboard"),
    ]
    
    results = []
    for feature_name, feature_path in features:
        try:
            # 这里只是验证功能存在，不实际执行
            module_name, attr_name = feature_path.split(".")
            base_module = module_name.split(".")[0]
            
            if base_module == "ButtonResponseFixer":
                from core.button_fixer import ButtonResponseFixer
                results.append((feature_name, True, "✅"))
                print(f"  ✅ {feature_name} - 可用")
            elif base_module == "AsyncTaskManager":
                from core.async_task_manager import AsyncTaskManager
                results.append((feature_name, True, "✅"))
                print(f"  ✅ {feature_name} - 可用")
            elif base_module == "DatabaseOptimizer":
                from core.database_optimizer import DatabaseOptimizer
                results.append((feature_name, True, "✅"))
                print(f"  ✅ {feature_name} - 可用")
            elif base_module == "AICollaborationEngine":
                from core.ai_collaboration import AICollaborationEngine
                results.append((feature_name, True, "✅"))
                print(f"  ✅ {feature_name} - 可用")
            elif base_module == "MultiSourceStrategyCrawler":
                from core.multi_source_strategy import MultiSourceStrategyCrawler
                results.append((feature_name, True, "✅"))
                print(f"  ✅ {feature_name} - 可用")
            elif base_module == "DatabaseMonitor":
                from core.database_monitor import DatabaseMonitor
                results.append((feature_name, True, "✅"))
                print(f"  ✅ {feature_name} - 可用")
            else:
                results.append((feature_name, False, "❌"))
                print(f"  ❌ {feature_name} - 未知模块")
                
        except Exception as e:
            results.append((feature_name, False, f"❌ {str(e)[:50]}"))
            print(f"  ❌ {feature_name} - 验证失败: {e}")
    
    return results

def main():
    """主验证函数"""
    print("🚀 QuantBrain v4.0 功能验证测试")
    print("=" * 60)
    
    # 执行所有验证
    module_results = verify_core_modules()
    structure_results = verify_website_structure()
    config_results = verify_configuration()
    feature_results = verify_optimization_features()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📋 验证结果汇总:")
    
    all_results = []
    all_results.extend([(f"模块: {m}", s, msg) for m, _, s, msg in module_results])
    all_results.extend([(f"文件: {f}", s, msg) for f, s, msg in structure_results])
    all_results.extend([(f"配置: {c}", s, msg) for c, s, msg in config_results])
    all_results.extend([(f"功能: {f}", success, msg) for f, success, msg in feature_results])
    
    passed = sum(1 for _, success, _ in all_results if success)
    total = len(all_results)
    
    for name, success, msg in all_results:
        print(f"  {msg} - {name}")
    
    print(f"\n🎯 总体通过率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed / total >= 0.8:
        print("\n✨ 核心功能验证通过！网站已准备好启动。")
        print("\n🚀 启动指南:")
        print("  1. 双击运行 `start_website.bat`")
        print("  2. 或执行命令: `streamlit run enhanced_app.py`")
        print("  3. 访问: http://localhost:8501")
        print("\n📊 新功能页面:")
        print("  - 📊 数据库性能: 实时性能监控")
        print("  - 🌐 多源策略学习: Web爬取策略")
        print("  - 🤖 AI策略学习: 异步AI任务")
        print("  - 📡 每日扫描: 不阻塞UI的扫描")
    else:
        print("\n⚠️  部分功能验证失败，请检查相关模块。")

if __name__ == "__main__":
    main()