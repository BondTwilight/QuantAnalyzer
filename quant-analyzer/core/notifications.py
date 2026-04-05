"""
🔔 通知模块 — 多渠道消息推送框架

支持渠道（预留接口）：
- 飞书 (FeiShu/Lark Webhook)
- 微信 (WeChat Server酱/企业微信机器人)
- 邮件 (SMTP)
- 系统日志 (logging)
- 自定义回调

设计原则：
1. 统一接口: send() 方法统一调用
2. 优先级: 不同级别走不同渠道
3. 幂等性: 同一内容不重复发送
4. 可靠性: 发送失败自动降级到日志

参考易涨EasyUp的"飞书推送"模块设计。
"""

import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import os
from typing import Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 消息类型与优先级
# ═══════════════════════════════════════════════

class NotificationPriority(Enum):
    """通知优先级"""
    DEBUG = "debug"       # 调试信息 → 仅日志
    INFO = "info"         # 一般信息 → 日志
    SUCCESS = "success"   # 成功事件 → 日志 + 可选推送
    WARNING = "warning"   # 警告信息 → 日志 + 推送
    ERROR = "error"       # 错误信息 → 全渠道推送
    CRITICAL = "critical" # 严重告警 → 全渠道推送（最高优先）


class NotificationChannel(Enum):
    """通知渠道"""
    LOG = "log"           # 系统日志
    FEISHU = "feishu"     # 飞书 Webhook
    WECHAT = "wechat"     # 微信 (Server酱/企微)
    EMAIL = "email"       # 邮件
    CALLBACK = "callback" # 自定义回调


@dataclass
class NotificationMessage:
    """通知消息"""
    title: str                    # 标题
    content: str                  # 内容正文
    priority: NotificationPriority = NotificationPriority.INFO
    channel: Optional[NotificationChannel] = None  # None=自动选择
    extra: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content,
            "priority": self.priority.value,
            "channel": self.channel.value if self.channel else None,
            "timestamp": self.timestamp,
            **self.extra,
        }


# ═══════════════════════════════════════════════
# 抽象通知器基类
# ═══════════════════════════════════════════════

class BaseNotifier(ABC):
    """通知器抽象基类"""

    name: str = "base"
    enabled: bool = False

    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        """发送消息，返回是否成功"""
        ...

    @abstractmethod
    def check_available(self) -> bool:
        """检查当前环境是否可用此通知器"""
        ...

    def format_message(self, message: NotificationMessage, template: str = "default") -> str:
        """格式化消息为特定渠道格式"""
        return f"[{message.priority.value.upper()}] {message.title}\n\n{message.content}"


# ═══════════════════════════════════════════════
# 具体通知器实现
# ═══════════════════════════════════════════════

class LogNotifier(BaseNotifier):
    """系统日志通知器 — 始终可用，作为降级兜底"""

    name = "系统日志"
    enabled = True

    LEVEL_MAP = {
        NotificationPriority.DEBUG: logging.DEBUG,
        NotificationPriority.INFO: logging.INFO,
        NotificationPriority.SUCCESS: logging.INFO,  # 成功用INFO级别
        NotificationPriority.WARNING: logging.WARNING,
        NotificationPriority.ERROR: logging.ERROR,
        NotificationPriority.CRITICAL: logging.CRITICAL,
    }

    def check_available(self) -> bool:
        return True

    def send(self, message: NotificationMessage) -> bool:
        level = self.LEVEL_MAP.get(message.priority, logging.INFO)
        log_msg = f"[通知] {message.title} | {message.content[:200]}"
        logger.log(level, log_msg)
        return True


class FeishuNotifier(BaseNotifier):
    """飞书 Webhook 机器人通知器
    
    配置方法：
    1. 在飞书群添加自定义机器人
    2. 获取 Webhook URL
    3. 设置环境变量 FEISHU_WEBHOOK_URL
    
    易涨EasyUp的核心推荐方案。
    """
    name = "飞书"
    _webhook_url: Optional[str] = None

    @classmethod
    def configure(cls, webhook_url: str = None):
        """配置飞书Webhook"""
        cls._webhook_url = webhook_url or os.environ.get("FEISHU_WEBHOOK_URL")
        cls.enabled = bool(cls._webhook_url)

    def check_available(self) -> bool:
        return bool(self._webhook_url)

    def send(self, message: NotificationMessage) -> bool:
        if not self.check_available():
            logger.debug("飞书通知未配置，跳过")
            return False
        
        try:
            import urllib.request
            
            # 根据优先级选择颜色
            color_map = {
                NotificationPriority.DEBUG: "#999999",
                NotificationPriority.INFO: "#1890ff",
                NotificationPriority.SUCCESS: "#52c41a",
                NotificationPriority.WARNING: "#faad14",
                NotificationPriority.ERROR: "#f5222d",
                NotificationPriority.CRITICAL: "#cf1322",
            }
            
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": f"🔔 QuantBrain - {message.title}"},
                        "template": color_map.get(message.priority, "#1890ff"),
                    },
                    "elements": [
                        {"tag": "markdown", "content": self._format_content(message)},
                        {"tag": "note", "elements": [{
                            "tag": "plain_text", 
                            "content": f"{message.timestamp}"
                        }]},
                    ],
                },
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self._webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get("code") == 0

        except Exception as e:
            logger.warning(f"飞书发送失败: {e}")
            return False

    def _format_content(self, msg: NotificationMessage) -> str:
        """格式化飞书 Markdown 内容"""
        lines = [f"**{msg.content}**"]
        
        # 额外字段
        for k, v in msg.extra.items():
            if isinstance(v, float):
                v = round(v, 4)
            lines.append(f"- **{k}:** {v}")
        
        return "\n".join(lines)


class WechatNotifier(BaseNotifier):
    """微信通知器（Server酱 / 企业微信）
    
    配置方式二选一：
    A. Server酱: 设置环境变量 WECHAT_SENDKEY
    B. 企业微信: 设置环境变量 WECHAT_WEBHOOK_URL
    """
    name = "微信"
    _sendkey: Optional[str] = None
    _webhook_url: Optional[str] = None

    @classmethod
    def configure(cls, sendkey: str = None, webhook_url: str = None):
        cls._sendkey = sendkey or os.environ.get("WECHAT_SENDKEY")
        cls._webhook_url = webhook_url or os.environ.get("WECHAT_WEBHOOK_URL")
        cls.enabled = bool(cls._sendkey or cls._webhook_url)

    def check_available(self) -> bool:
        return bool(self._sendkey or self._webhook_url)

    def send(self, message: NotificationMessage) -> bool:
        if not self.check_available():
            return False

        try:
            import urllib.request
            import urllib.parse

            if self._webhook_url:
                # 企业微信 Webhook
                payload = {
                    "msgtype": "text",
                    "text": {"content": f"[QuantBrain]\n{message.title}\n{message.content}"}
                }
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    self._webhook_url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode())
                    return result.get("errcode") == 0

            elif self._sendkey:
                # Server酱
                params = urllib.parse.urlencode({
                    "title": f"QuantBrain: {message.title}",
                    "desp": message.content,
                })
                url = f"https://sctapi.ftqq.com/{self._sendkey}.send?{params}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode())
                    return result.get("code") == 0

        except Exception as e:
            logger.warning(f"微信发送失败: {e}")
            return False


class EmailNotifier(BaseNotifier):
    """邮件通知器
    
    配置方式（环境变量）：
    - SMTP_HOST: SMTP服务器地址 (如 smtp.qq.com)
    - SMTP_PORT: SMTP端口 (如 587)
    - SMTP_USER: 发件邮箱
    - SMTP_PASS: 邮箱授权码/密码
    - NOTIFY_EMAILS: 收件邮箱列表（逗号分隔）
    """
    name = "邮件"
    _config: Dict[str, str] = {}

    @classmethod
    def configure(cls, host=None, port=None, user=None, password=None, recipients=None):
        cls._config = {
            "host": host or os.environ.get("SMTP_HOST", ""),
            "port": int(port or os.environ.get("SMTP_PORT", "587")),
            "user": user or os.environ.get("SMTP_USER", ""),
            "password": password or os.environ.get("SMTP_PASS", ""),
            "recipients": recipients or os.environ.get("NOTIFY_EMAILS", "").split(","),
        }
        cls.enabled = all([cls._config["host"], cls._config["user"], cls._config["password"]])

    def check_available(self) -> bool:
        return self.enabled

    def send(self, message: NotificationMessage) -> bool:
        if not self.check_available():
            return False

        try:
            cfg = self._config
            recipients = [r.strip() for r in cfg["recipients"] if r.strip()]
            if not recipients:
                return False

            # 构建邮件
            mime = MIMEMultipart()
            mime["From"] = cfg["user"]
            mime["To"] = ", ".join(recipients)
            mime["Subject"] = f"[QuantBrain] {message.title}"

            body = f"""
<h2>{message.title}</h2>
<p><strong>时间:</strong> {message.timestamp}</p>
<p><strong>优先级:</strong> {message.priority.value.upper()}</p>
<hr>
<pre>{message.content}</pre>

<p style="color:#666; font-size:12px;">— QuantBrain 自动进化量化策略系统</p>
            """
            mime.attach(MIMEText(body, "html"))

            # 发送
            server = smtplib.SMTP(cfg["host"], cfg["port"])
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], recipients, mime.as_string())
            server.quit()

            return True

        except Exception as e:
            logger.warning(f"邮件发送失败: {e}")
            return False


# ═══════════════════════════════════════════════
# 通知管理器（统一入口）
# ═══════════════════════════════════════════════

class NotificationManager:
    """
    多渠道通知管理器
    
    使用方式：
    ```python
    from core.notifications import notify, init_notifications
    
    # 初始化（可选配置）
    init_notifications(
        feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    )
    
    # 发送通知（自动根据优先级选择渠道）
    notify.send("进化完成", "发现3个有效因子，最佳适应度0.72", 
               priority="success", extra={"fitness": 0.72})
    
    # 或使用便捷方法
    notify.success("回测完成", "年化收益32%，最大回撤8%")
    notify.error("数据源异常", "AkShare连接超时，已切换BaoStock")
    ```
    """

    _instance = None
    _notifiers: Dict[str, BaseNotifier] = {}
    _callbacks: List[Callable] = []
    _sent_cache: set = set()  # 去重缓存

    # ── 单例模式 ──
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_default_notifiers()
        return cls._instance

    def _init_default_notifiers(self):
        """初始化默认通知器（日志始终启用）"""
        self._notifiers = {
            NotificationChannel.LOG.value: LogNotifier(),
        }

    # ── 注册与配置 ──

    def register_notifier(self, notifier: BaseNotifier):
        """注册通知器"""
        if notifier.name and notifier.check_available():
            self._notifiers[notifier.name] = notifier
            logger.info(f"注册通知器: {notifier.name}")

    def register_callback(self, callback: Callable[[NotificationMessage], None]):
        """注册自定义回调函数"""
        self._callbacks.append(callback)

    # ── 快捷配置方法 ──

    @classmethod
    def init_all(
        cls,
        feishu_webhook: str = None,
        wechat_sendkey: str = None,
        wechat_webhook: str = None,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_pass: str = None,
        notify_emails: str = None,
    ):
        """一键初始化所有通知渠道
        
        Args:
            feishu_webhook: 飞书机器人 Webhook URL
            wechat_sendkey: Server酱 SendKey
            wechat_webhook: 企业微信 Webhook URL
            smtp_*: 邮件SMTP配置
            notify_emails: 收件邮箱（逗号分隔）
        """
        instance = cls()

        # 飞书
        if feishu_webhook:
            fn = FeishuNotifier()
            FeishuNotifier.configure(webhook_url=feishu_webhook)
            instance.register_notifier(fn)

        # 微信
        if wechat_sendkey or wechat_webhook:
            wn = WechatNotifier()
            WechatNotifier.configure(sendkey=wechat_sendkey, webhook_url=wechat_webhook)
            instance.register_notifier(wn)

        # 邮件
        if smtp_host:
            en = EmailNotifier()
            EmailNotifier.configure(
                host=smtp_host, port=smtp_port,
                user=smtp_user, password=smtp_pass,
                recipients=notify_emails,
            )
            instance.register_notifier(en)

        return instance

    # ── 发送核心逻辑 ──

    def send(
        self,
        title: str,
        content: str,
        priority: Union[NotificationPriority, str] = NotificationPriority.INFO,
        channel: Optional[NotificationChannel] = None,
        dedup_key: str = None,
        **extra,
    ) -> Dict[str, bool]:
        """
        发送通知（统一入口）

        Args:
            title: 消息标题
            content: 消息内容
            priority: 优先级 (枚举或字符串)
            channel: 指定渠道 (None=自动选择)
            dedup_key: 去重键（相同键不重复发送）
            **extra: 额外数据字段
        
        Returns:
            各渠道发送结果 {"日志": True, "飞书": False, ...}
        """
        # 规范化优先级
        if isinstance(priority, str):
            try:
                priority = NotificationPriority(priority.lower())
            except ValueError:
                priority = NotificationPriority.INFO

        # 构建消息对象
        message = NotificationMessage(
            title=title, content=content,
            priority=priority, channel=channel, extra=extra,
        )

        # 去重检查
        if dedup_key:
            cache_key = f"{dedup_key}:{title}:{content[:50]}"
            if cache_key in self._sent_cache:
                logger.debug(f"通知去重跳过: {dedup_key}")
                return {"deduplicated": True}
            self._sent_cache.add(cache_key)
            # 缓存大小限制
            if len(self._sent_cache) > 1000:
                self._sent_cache = set(list(self._sent_cache)[-500:])

        results = {}

        # 1. 日志始终发送
        log_result = self._notifiers.get(NotificationChannel.LOG.value, LogNotifier()).send(message)
        results["日志"] = log_result

        # 2. 根据优先级决定其他渠道
        if channel:
            channels_to_try = [channel]
        else:
            channels_to_try = self._select_channels_by_priority(priority)

        for ch in channels_to_try:
            ch_name = ch.value if isinstance(ch, NotificationChannel) else ch
            notifier = self._notifiers.get(ch_name)
            if notifier and notifier.check_available():
                try:
                    success = notifier.send(message)
                    results[ch_name] = success
                except Exception as e:
                    logger.warning(f"通知器 [{ch_name}] 异常: {e}")
                    results[ch_name] = False

        # 3. 回调函数
        for cb in self._callbacks:
            try:
                cb(message)
            except Exception as e:
                logger.debug(f"通知回调异常: {e}")

        return results

    def _select_channels_by_priority(self, priority: NotificationPriority) -> List[NotificationChannel]:
        """根据优先级选择通知渠道"""
        if priority == NotificationPriority.DEBUG:
            return []  # 仅日志
        elif priority == NotificationPriority.INFO:
            return []
        elif priority == NotificationPriority.SUCCESS:
            return [c for c in [NotificationChannel.FEISHU, NotificationChannel.WECHAT]
                    if c.value in self._notifiers]
        elif priority == NotificationPriority.WARNING:
            return [c for c in [NotificationChannel.FEISHU, NotificationChannel.WECHAT]
                    if c.value in self._notifiers]
        else:
            # ERROR / CRITICAL: 所有可用渠道
            return [NotificationChannel(c) for c in self._notifiers.keys()
                    if c != NotificationChannel.LOG.value]

    # ── 便捷方法 ──

    def info(self, title: str, content: str, **kwargs):
        return self.send(title, content, priority=NotificationPriority.INFO, **kwargs)

    def success(self, title: str, content: str, **kwargs):
        return self.send(title, content, priority=NotificationPriority.SUCCESS, **kwargs)

    def warning(self, title: str, content: str, **kwargs):
        return self.send(title, content, priority=NotificationPriority.WARNING, **kwargs)

    def error(self, title: str, content: str, **kwargs):
        return self.send(title, content, priority=NotificationPriority.ERROR, **kwargs)

    def critical(self, title: str, content: str, **kwargs):
        return self.send(title, content, priority=NotificationPriority.CRITICAL, **kwargs)

    def debug(self, title: str, content: str, **kwargs):
        return self.send(title, content, priority=NotificationPriority.DEBUG, **kwargs)

    # ── 专用快捷方法（量化场景）──

    def evolution_complete(self, n_factors: int, best_fitness: float, time_cost: str):
        """进化完成通知"""
        return self.success(
            "🧬 因子进化完成",
            f"发现 {n_factors} 个有效因子\n最佳适应度: {best_fitness:.4f}\n耗时: {time_cost}",
            dedup_key=f"evol:{datetime.now().strftime('%H%M')}",
            n_factors=n_factors, best_fitness=round(best_fitness, 4),
        )

    def strategy_update(self, strategy_name: str, score: float, action: str):
        """策略更新通知"""
        return self.info(
            "📊 策略更新",
            f"策略 [{strategy_name}] 已{action}\n组合评分: {score:.1f}",
            strategy=strategy_name, score=round(score, 1),
        )

    def alert_data_source_failover(self, primary: str, backup: str):
        """数据源切换警告"""
        return self.warning(
            "⚠️ 数据源切换",
            f"主数据源 [{primary}] 不可用\n已自动切换至 [{backup}]",
            source_from=primary, source_to=backup,
        )

    def alert_error(self, module: str, error_msg: str):
        """错误告警"""
        return self.error(
            "❌ 系统异常",
            f"模块 [{module}] 发生错误:\n{error_msg}",
            module=module,
        )


# ═══════════════════════════════════════════════
# 全局单例实例
# ═══════════════════════════════════════════════

notify: NotificationManager = NotificationManager()


def init_notifications(**kwargs) -> NotificationManager:
    """初始化通知系统的快捷函数"""
    return NotificationManager.init_all(**kwargs)


def get_notification_status() -> Dict:
    """获取所有通知器的状态"""
    status = {}
    for name, notifier in notify._notifiers.items():
        status[name] = {
            "enabled": notifier.enabled,
            "available": notifier.check_available(),
        }
    return status
