"""
QuantBrain 一键部署到 HuggingFace Spaces
==========================================
用法: python deploy_to_hf.py

Token 从 ~/.huggingface/token 自动读取（已持久化）
无需手动输入任何内容，直接运行即可。
"""

import sys
import time
from pathlib import Path
from datetime import datetime


def check_token():
    """检查 HF Token 是否存在且有效"""
    from huggingface_hub import HfApi

    token_file = Path.home() / ".huggingface" / "token"
    if not token_file.exists():
        print("[ERROR] Token 文件不存在:", token_file)
        print("        请先运行: huggingface-cli login")
        return False

    try:
        api = HfApi()
        info = api.whoami()
        print(f"[OK] Token 有效, 用户: {info['name']}")
        return True
    except Exception as e:
        print(f"[ERROR] Token 无效或已过期: {e}")
        print("        请重新获取 Token 后运行:")
        print("        python -c \"from pathlib import Path; Path.home().joinpath('.huggingface','token').write_text('你的新Token')\"")
        return False


def deploy():
    """一键部署到 HuggingFace Spaces"""
    from huggingface_hub import HfApi

    repo_id = "BondTwilight/quantbrain"
    project_dir = Path(__file__).parent

    # 要忽略的目录/文件
    ignore_patterns = {
        ".git", "__pycache__", ".pytest_cache", "*.pyc",
        "cache/", "logs/", "reports/", "*.db",
        "strategy_library/",
    }

    print(f"\n{'='*50}")
    print(f"  QuantBrain HF 部署")
    print(f"  目标: {repo_id}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    # 检查 token
    if not check_token():
        sys.exit(1)

    api = HfApi()

    # 检查 repo 是否存在
    try:
        repo_info = api.repo_info(repo_id=repo_id, repo_type="space")
        print(f"[OK] Space 存在: {repo_info.url}")
    except Exception:
        print(f"[INFO] Space 不存在，正在创建...")
        try:
            api.create_repo(
                repo_id=repo_id,
                repo_type="space",
                space_sdk="docker",
                exist_ok=True,
                private=False,
            )
            print("[OK] Space 创建成功")
        except Exception as e:
            print(f"[ERROR] 创建 Space 失败: {e}")
            sys.exit(1)

    print(f"\n[INFO] 开始上传文件...")

    # 上传整个文件夹
    try:
        result = api.upload_folder(
            folder_path=str(project_dir),
            repo_id=repo_id,
            repo_type="space",
            commit_message=f"Deploy: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )
        print(f"[OK] 上传完成!")
        print(f"     Commit: {result}")
    except Exception as e:
        print(f"[ERROR] 上传失败: {e}")
        sys.exit(1)

    # 等待构建
    print(f"\n[INFO] 等待 HuggingFace 构建启动...")
    time.sleep(5)

    # 检查构建状态
    try:
        status = api.space_info(repo_id=repo_id)
        stage = getattr(status, 'runtime', None)
        if stage:
            print(f"[INFO] 构建状态: {stage}")
        else:
            print(f"[INFO] Space 状态已更新，请访问查看")
    except Exception:
        print(f"[INFO] 无法获取构建状态，请手动访问查看")

    print(f"\n{'='*50}")
    print(f"  部署完成!")
    print(f"  访问: https://bondtwilight-quantbrain.hf.space")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    deploy()
