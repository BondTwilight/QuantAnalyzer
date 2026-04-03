"""
GitHub Storage — 通过 GitHub API 将状态文件持久化到仓库
用于 HuggingFace Spaces 等无持久存储的云平台

工作原理：
1. 读取本地 JSON → 优先从 GitHub API 加载
2. 写入本地 JSON → 同步推送到 GitHub API
3. 使用 GitHub Contents API (Base64 编码)
"""
import json
import base64
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class GitHubStorage:
    """通过 GitHub API 实现跨会话状态持久化"""

    def __init__(
        self,
        repo: str = "",
        token: str = "",
        branch: str = "main",
        data_path: str = "cloud_data",
    ):
        self.repo = repo or os.getenv("GITHUB_STORAGE_REPO", "")
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.branch = branch
        self.data_path = data_path
        self.api_base = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

        self._cache: Dict[str, Dict[str, Any]] = {}
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        """检查 GitHub 存储是否可用"""
        if self._available is not None:
            return self._available
        if not self.repo or not self.token:
            self._available = False
            logger.info("GitHub Storage: 未配置 repo 或 token，使用本地存储")
            return False
        try:
            resp = requests.get(
                f"{self.api_base}/repos/{self.repo}",
                headers=self.headers,
                timeout=10,
            )
            self._available = resp.status_code == 200
            if self._available:
                logger.info(f"GitHub Storage: 已连接 {self.repo}")
            else:
                logger.warning(f"GitHub Storage: 无法访问仓库 (HTTP {resp.status_code})")
        except Exception as e:
            self._available = False
            logger.warning(f"GitHub Storage: 连接失败 - {e}")
        return self._available

    def _api_get(self, path: str) -> Optional[Dict]:
        """GET GitHub API"""
        try:
            resp = requests.get(
                f"{self.api_base}/repos/{self.repo}/contents/{path}",
                headers=self.headers,
                params={"ref": self.branch},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return None
            else:
                logger.warning(f"GitHub API GET {path}: HTTP {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"GitHub API GET {path}: {e}")
            return None

    def _api_put(self, path: str, content: bytes, message: str, sha: Optional[str] = None) -> bool:
        """PUT GitHub API (创建/更新文件)"""
        data = {
            "message": message,
            "content": base64.b64encode(content).decode("utf-8"),
            "branch": self.branch,
        }
        if sha:
            data["sha"] = sha
        try:
            resp = requests.put(
                f"{self.api_base}/repos/{self.repo}/contents/{path}",
                headers=self.headers,
                json=data,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                return True
            else:
                logger.warning(f"GitHub API PUT {path}: HTTP {resp.status_code} - {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"GitHub API PUT {path}: {e}")
            return False

    def load_json(self, filename: str) -> Optional[Dict]:
        """从 GitHub 加载 JSON 文件"""
        if not self.available:
            return None

        # 使用内存缓存
        if filename in self._cache:
            return self._cache[filename]

        remote_path = f"{self.data_path}/{filename}"
        result = self._api_get(remote_path)

        if result and "content" in result:
            try:
                content = base64.b64decode(result["content"])
                data = json.loads(content)
                self._cache[filename] = data
                logger.debug(f"从 GitHub 加载: {filename} ({len(content)} bytes)")
                return data
            except Exception as e:
                logger.error(f"解析 GitHub 文件 {filename} 失败: {e}")

        return None

    def save_json(self, filename: str, data: Dict) -> bool:
        """保存 JSON 到 GitHub"""
        if not self.available:
            return False

        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        remote_path = f"{self.data_path}/{filename}"

        # 获取当前 SHA（用于更新）
        sha = None
        existing = self._api_get(remote_path)
        if existing and "sha" in existing:
            sha = existing["sha"]

        # 检查内容是否有变化
        if existing and "content" in existing:
            existing_content = base64.b64decode(existing["content"])
            if existing_content == content:
                self._cache[filename] = data
                return True  # 没变化，跳过

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[QuantBrain] Update {filename} - {timestamp}"

        success = self._api_put(remote_path, content, message, sha)
        if success:
            self._cache[filename] = data
            logger.info(f"已同步到 GitHub: {filename}")
        return success

    def init_cloud_data(self, local_data_dir: str = "data") -> None:
        """初始化云数据：将本地 JSON 文件同步到 GitHub（仅首次）"""
        if not self.available:
            return

        data_dir = Path(local_data_dir)
        if not data_dir.exists():
            return

        for json_file in data_dir.glob("*.json"):
            # 检查远端是否已存在
            remote_path = f"{self.data_path}/{json_file.name}"
            existing = self._api_get(remote_path)
            if existing:
                logger.info(f"云数据已存在，跳过: {json_file.name}")
                continue

            # 上传本地文件
            try:
                content = json_file.read_bytes()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"[QuantBrain] Init cloud data: {json_file.name} - {timestamp}"
                self._api_put(remote_path, content, message)
                logger.info(f"初始化云数据: {json_file.name}")
            except Exception as e:
                logger.error(f"初始化云数据失败 {json_file.name}: {e}")


# 全局单例
_storage: Optional[GitHubStorage] = None


def get_storage() -> GitHubStorage:
    """获取全局 GitHubStorage 实例"""
    global _storage
    if _storage is None:
        _storage = GitHubStorage()
    return _storage


def load_state(filename: str, local_dir: str = "data") -> Dict:
    """
    加载状态文件 — 优先从 GitHub 加载，失败则从本地加载
    用于替代直接 json.load(file)
    """
    storage = get_storage()

    # 尝试从 GitHub 加载
    cloud_data = storage.load_json(filename)
    if cloud_data is not None:
        return cloud_data

    # 回退到本地文件
    local_path = Path(local_dir) / filename
    if local_path.exists():
        try:
            return json.loads(local_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    return {}


def save_state(filename: str, data: Dict, local_dir: str = "data") -> bool:
    """
    保存状态文件 — 同时保存到本地和 GitHub
    用于替代直接 json.dump(data, file)
    """
    # 保存到本地
    local_path = Path(local_dir) / filename
    local_path.parent.mkdir(exist_ok=True)
    try:
        local_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error(f"保存本地文件失败 {filename}: {e}")

    # 同步到 GitHub
    storage = get_storage()
    return storage.save_json(filename, data)


def init_cloud_sync() -> None:
    """
    应用启动时调用 — 初始化云数据同步
    在 enhanced_app.py 开头调用此函数
    """
    storage = get_storage()
    if storage.available:
        storage.init_cloud_data()
