#!/usr/bin/env python3
"""
QuantAnalyzer 一键配置脚本
自动检测并配置AI模型API Key
"""

import os
import sys
import webbrowser
from pathlib import Path

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"

# AI模型配置
AI_MODELS_CONFIG = {
    "cerebras": {
        "name": "Cerebras (Llama 3.3 70B)",
        "env_key": "CEREBRAS_API_KEY",
        "url": "https://cloud.cerebras.ai/",
        "desc": "🔥 完全免费无限制! 70B大模型",
        "signup_url": "https://cloud.cerebras.ai/",
    },
    "zhipu": {
        "name": "智谱 GLM-4-Flash",
        "env_key": "ZHIPU_API_KEY",
        "url": "https://open.bigmodel.cn/",
        "desc": "⭐ 国产首选! 中文理解强",
        "signup_url": "https://open.bigmodel.cn/",
    },
    "groq": {
        "name": "Groq (Llama 3.3 70B)",
        "env_key": "GROQ_API_KEY",
        "url": "https://console.groq.com/keys",
        "desc": "⚡ 超快推理! 免费额度慷慨",
        "signup_url": "https://console.groq.com/",
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "env_key": "SILICONFLOW_API_KEY",
        "url": "https://cloud.siliconflow.cn/",
        "desc": "🇨🇳 国内首选! 多模型可选",
        "signup_url": "https://cloud.siliconflow.cn/",
    },
    "deepseek": {
        "name": "DeepSeek V3",
        "env_key": "DEEPSEEK_API_KEY",
        "url": "https://platform.deepseek.com/",
        "desc": "🧠 推理能力强! 新用户送额度",
        "signup_url": "https://platform.deepseek.com/",
    },
}

def print_banner():
    print("=" * 60)
    print("  🤖 QuantAnalyzer AI模型一键配置工具")
    print("=" * 60)
    print()

def check_existing_keys():
    """检查已配置的API Key"""
    print("📋 检查现有配置...\n")
    
    configured = []
    missing = []
    
    for model_id, config in AI_MODELS_CONFIG.items():
        key = os.getenv(config["env_key"], "")
        if key and len(key) > 5:
            configured.append((model_id, config["name"]))
            print(f"  ✅ {config['name']}: 已配置")
        else:
            missing.append((model_id, config))
            print(f"  ❌ {config['name']}: 未配置")
    
    return configured, missing

def load_existing_env():
    """加载现有.env文件"""
    existing = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    existing[key.strip()] = value.strip()
    return existing

def save_env(env_dict):
    """保存到.env文件"""
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("# QuantAnalyzer 环境配置\n")
        f.write("# AI模型API Keys\n\n")
        for key, value in sorted(env_dict.items()):
            if value:
                f.write(f"{key}={value}\n")

def open_signup_page(url):
    """打开注册页面"""
    try:
        webbrowser.open(url)
        return True
    except:
        return False

def interactive_configure():
    """交互式配置"""
    print("\n" + "=" * 60)
    print("  🎯 选择要配置的模型")
    print("=" * 60)
    
    # 检查现有配置
    configured, missing = check_existing_keys()
    
    if not missing:
        print("\n🎉 所有模型已配置完成!")
        return
    
    print("\n📝 未配置的模型:\n")
    for i, (model_id, config) in enumerate(missing, 1):
        print(f"  [{i}] {config['name']}")
        print(f"      {config['desc']}")
        print(f"      注册地址: {config['url']}\n")
    
    print("[0] 完成配置")
    print()
    
    while True:
        try:
            choice = input("请输入模型编号 (多选用逗号分隔, 如 1,3): ").strip()
            if choice == "0":
                break
            
            indices = [int(x.strip()) for x in choice.split(",")]
            
            for idx in indices:
                if 1 <= idx <= len(missing):
                    model_id, config = missing[idx - 1]
                    
                    # 询问是否打开注册页面
                    print(f"\n{'='*50}")
                    print(f"配置: {config['name']}")
                    print(f"{'='*50}")
                    print(f"描述: {config['desc']}")
                    print(f"注册: {config['signup_url']}")
                    
                    open_page = input("\n是否打开注册页面? (y/n): ").strip().lower()
                    if open_page == "y":
                        open_signup_page(config["signup_url"])
                    
                    # 输入API Key
                    api_key = input("请输入API Key (直接回车跳过): ").strip()
                    
                    if api_key:
                        # 更新环境变量
                        os.environ[config["env_key"]] = api_key
                        print(f"✅ 已保存 {config['name']} 的API Key")
                    else:
                        print(f"⏭️ 跳过 {config['name']}")
                else:
                    print(f"无效的编号: {idx}")
            
            # 重新检查配置状态
            print("\n📊 更新后的配置状态:")
            configured, missing = check_existing_keys()
            
            if not missing:
                break
                
            continue_conf = input("\n是否继续配置其他模型? (y/n): ").strip().lower()
            if continue_conf != "y":
                break
                
        except (ValueError, KeyboardInterrupt) as e:
            print("\n\n操作取消")
            break
    
    # 保存到.env文件
    env_dict = load_existing_env()
    for model_id, config in AI_MODELS_CONFIG.items():
        key = os.environ.get(config["env_key"], "")
        if key:
            env_dict[config["env_key"]] = key
    
    save_env(env_dict)
    print(f"\n✅ 配置已保存到 {ENV_FILE}")

def auto_setup_cerebras():
    """自动设置Cerebras (最推荐的免费模型)"""
    print("\n" + "=" * 60)
    print("  🔥 自动设置 Cerebras (推荐)")
    print("=" * 60)
    print("\nCerebras 提供完全免费、无限制的 Llama 3.3 70B 模型!")
    print("这是目前最佳的免费AI模型选择。\n")
    
    api_key = input("请输入 Cerebras API Key (从 https://cloud.cerebras.ai/ 获取): ").strip()
    
    if api_key:
        os.environ["CEREBRAS_API_KEY"] = api_key
        
        # 保存到.env
        env_dict = load_existing_env()
        env_dict["CEREBRAS_API_KEY"] = api_key
        save_env(env_dict)
        
        print("\n✅ Cerebras 配置完成!")
        print("   现在您可以免费使用 Llama 3.3 70B 模型进行量化分析!")
    else:
        print("\n⏭️ 跳过, 您可以稍后手动配置")

def test_ai_connection():
    """测试AI连接"""
    print("\n" + "=" * 60)
    print("  🧪 测试AI连接")
    print("=" * 60)
    
    import subprocess
    
    test_script = '''
import sys
sys.path.insert(0, ".")
from core.ai_analyzer import analyze_strategy

result = analyze_strategy("# 测试策略", "ma_cross")
print("✅ AI分析功能正常!" if result else "❌ AI分析失败")
'''
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=SCRIPT_DIR,
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print(f"测试失败: {e}")

def main():
    print_banner()
    
    while True:
        print("\n请选择操作:")
        print("  [1] 🔥 一键配置 Cerebras (推荐)")
        print("  [2] 📝 交互式配置所有模型")
        print("  [3] 🧪 测试AI连接")
        print("  [4] 📖 查看配置说明")
        print("  [0] 退出")
        print()
        
        choice = input("请输入选项: ").strip()
        
        if choice == "1":
            auto_setup_cerebras()
        elif choice == "2":
            interactive_configure()
        elif choice == "3":
            test_ai_connection()
        elif choice == "4":
            show_help()
        elif choice == "0":
            print("\n👋 再见!")
            break
        else:
            print("无效选项")

def show_help():
    """显示帮助信息"""
    print("""
📖 QuantAnalyzer AI模型配置指南
=================================

【免费模型推荐】(按推荐程度排序)

1. 🔥 Cerebras (强烈推荐!)
   - 完全免费、无限制
   - Llama 3.3 70B 大模型
   - 注册: https://cloud.cerebras.ai/
   
2. ⭐ 智谱 GLM-4-Flash (国产首选)
   - 免费额度
   - 中文理解强
   - 注册: https://open.bigmodel.cn/
   
3. ⚡ Groq
   - 超快推理速度
   - 免费额度慷慨
   - 注册: https://console.groq.com/

【配置方法】
1. 运行本脚本选择配置方式
2. 按提示获取API Key并粘贴
3. 重启 QuantAnalyzer 应用

【故障排除】
- 如果API Key无效, 请检查是否正确复制
- 如果网络超时, 可能是代理/VPN问题
- 查看日志获取详细错误信息
""")

if __name__ == "__main__":
    main()
