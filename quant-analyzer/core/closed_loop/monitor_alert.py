"""
监控报警模块
监控策略表现、检测异常、自动报警和健康检查
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import json
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import schedule

# 设置日志
logger = logging.getLogger(__name__)

# ==================== 基础数据结构 ====================

class AlertLevel(Enum):
    """报警级别"""
    INFO = "info"       # 信息
    WARNING = "warning" # 警告
    CRITICAL = "critical" # 严重

class AlertChannel(Enum):
    """报警渠道"""
    EMAIL = "email"
    WECHAT = "wechat"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    SMS = "sms"
    LOG = "log"  # 仅记录日志

@dataclass
class Alert:
    """报警信息"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    metric: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    strategy_id: Optional[str] = None
    symbol: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_time": self.acknowledged_time.isoformat() if self.acknowledged_time else None
        }

@dataclass
class StrategyPerformance:
    """策略表现"""
    strategy_id: str
    timestamp: datetime
    metrics: Dict[str, float]
    positions: List[Dict]
    trades_today: List[Dict]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "positions": self.positions,
            "trades_today": self.trades_today
        }

@dataclass
class SystemHealth:
    """系统健康状态"""
    timestamp: datetime
    components: Dict[str, Dict]  # 组件名称 -> 状态
    overall_status: str  # "healthy", "degraded", "unhealthy"
    issues: List[str]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "components": self.components,
            "overall_status": self.overall_status,
            "issues": self.issues
        }

# ==================== 报警渠道 ====================

class AlertChannelBase(ABC):
    """报警渠道基类"""
    
    @abstractmethod
    def send_alert(self, alert: Alert) -> bool:
        """发送报警"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接"""
        pass

class EmailAlertChannel(AlertChannelBase):
    """邮件报警渠道"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.smtp_server = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_email = config.get("from_email", "")
        self.to_emails = config.get("to_emails", [])
        
        # 邮件模板
        self.templates = {
            AlertLevel.INFO: {
                "subject_prefix": "[INFO] ",
                "color": "#3498db"
            },
            AlertLevel.WARNING: {
                "subject_prefix": "[WARNING] ",
                "color": "#f39c12"
            },
            AlertLevel.CRITICAL: {
                "subject_prefix": "[CRITICAL] ",
                "color": "#e74c3c"
            }
        }
    
    def send_alert(self, alert: Alert) -> bool:
        """发送邮件报警"""
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            
            # 设置邮件头
            template = self.templates[alert.level]
            subject = f"{template['subject_prefix']}{alert.title}"
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # 创建HTML内容
            html = self._create_html_content(alert, template)
            
            # 添加HTML部分
            msg.attach(MIMEText(html, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"邮件报警发送成功: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"邮件报警发送失败: {e}")
            return False
    
    def test_connection(self) -> bool:
        """测试邮件服务器连接"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
            
            logger.info("邮件服务器连接测试成功")
            return True
            
        except Exception as e:
            logger.error(f"邮件服务器连接测试失败: {e}")
            return False
    
    def _create_html_content(self, alert: Alert, template: Dict) -> str:
        """创建HTML邮件内容"""
        color = template["color"]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .alert {{ border-left: 4px solid {color}; padding: 10px 20px; margin: 20px 0; background-color: #f9f9f9; }}
                .metric {{ font-weight: bold; color: {color}; }}
                .timestamp {{ color: #777; font-size: 0.9em; }}
                .details {{ margin-top: 10px; padding: 10px; background-color: #fff; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="alert">
                <h2>{alert.title}</h2>
                <p>{alert.message}</p>
                
                <div class="details">
                    <p><span class="metric">监控指标:</span> {alert.metric}</p>
                    <p><span class="metric">当前值:</span> {alert.value:.4f}</p>
                    <p><span class="metric">阈值:</span> {alert.threshold:.4f}</p>
                    <p><span class="metric">策略ID:</span> {alert.strategy_id or 'N/A'}</p>
                    <p><span class="metric">标的:</span> {alert.symbol or 'N/A'}</p>
                </div>
                
                <p class="timestamp">报警时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <p>此邮件由量化交易监控系统自动发送，请勿直接回复。</p>
        </body>
        </html>
        """
        
        return html

class WeChatAlertChannel(AlertChannelBase):
    """微信报警渠道（通过企业微信）"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.corp_id = config.get("corp_id", "")
        self.corp_secret = config.get("corp_secret", "")
        self.agent_id = config.get("agent_id", "")
        self.access_token = None
        self.token_expire_time = None
    
    def send_alert(self, alert: Alert) -> bool:
        """发送微信报警"""
        try:
            # 获取access token
            if not self._ensure_access_token():
                return False
            
            # 创建消息
            message = self._create_message(alert)
            
            # 发送消息
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self.access_token}"
            response = requests.post(url, json=message)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"微信报警发送成功: {alert.alert_id}")
                return True
            else:
                logger.error(f"微信报警发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"微信报警发送失败: {e}")
            return False
    
    def test_connection(self) -> bool:
        """测试微信连接"""
        return self._ensure_access_token()
    
    def _ensure_access_token(self) -> bool:
        """确保有有效的access token"""
        now = datetime.now()
        
        if self.access_token and self.token_expire_time and now < self.token_expire_time:
            return True
        
        try:
            url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
            params = {
                "corpid": self.corp_id,
                "corpsecret": self.corp_secret
            }
            
            response = requests.get(url, params=params)
            result = response.json()
            
            if result.get("errcode") == 0:
                self.access_token = result["access_token"]
                self.token_expire_time = now + timedelta(seconds=result["expires_in"] - 300)  # 提前5分钟过期
                return True
            else:
                logger.error(f"获取微信access token失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"获取微信access token失败: {e}")
            return False
    
    def _create_message(self, alert: Alert) -> Dict:
        """创建微信消息"""
        # 根据报警级别设置颜色
        if alert.level == AlertLevel.CRITICAL:
            color = "warning"
        elif alert.level == AlertLevel.WARNING:
            color = "info"
        else:
            color = "comment"
        
        # 创建消息内容
        content = f"""【{alert.title}】
        
{alert.message}

监控指标: {alert.metric}
当前值: {alert.value:.4f}
阈值: {alert.threshold:.4f}
策略ID: {alert.strategy_id or 'N/A'}
标的: {alert.symbol or 'N/A'}
时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"""
        
        message = {
            "touser": "@all",
            "msgtype": "textcard",
            "agentid": self.agent_id,
            "textcard": {
                "title": alert.title,
                "description": content,
                "url": "URL_TO_DASHBOARD",  # 可以链接到监控面板
                "btntxt": "查看详情"
            }
        }
        
        return message

class LogAlertChannel(AlertChannelBase):
    """日志报警渠道（仅记录日志）"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def send_alert(self, alert: Alert) -> bool:
        """记录日志报警"""
        level_map = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.CRITICAL: logging.ERROR
        }
        
        log_level = level_map.get(alert.level, logging.INFO)
        logger.log(log_level, f"报警: {alert.title} - {alert.message}")
        return True
    
    def test_connection(self) -> bool:
        """测试日志连接（总是成功）"""
        return True

# ==================== 监控规则 ====================

class MonitoringRule:
    """监控规则"""
    
    def __init__(self, rule_id: str, metric: str, condition: str, 
                 threshold: float, level: AlertLevel, 
                 channels: List[AlertChannel], description: str = ""):
        self.rule_id = rule_id
        self.metric = metric
        self.condition = condition  # "gt", "lt", "eq", "change_gt", "change_lt"
        self.threshold = threshold
        self.level = level
        self.channels = channels
        self.description = description
    
    def check(self, current_value: float, previous_value: Optional[float] = None) -> Tuple[bool, float]:
        """检查规则是否触发"""
        if self.condition == "gt":
            triggered = current_value > self.threshold
            actual_value = current_value
            
        elif self.condition == "lt":
            triggered = current_value < self.threshold
            actual_value = current_value
            
        elif self.condition == "eq":
            triggered = abs(current_value - self.threshold) < 1e-6
            actual_value = current_value
            
        elif self.condition == "change_gt" and previous_value is not None:
            change = (current_value - previous_value) / abs(previous_value) if abs(previous_value) > 1e-6 else 0
            triggered = change > self.threshold
            actual_value = change
            
        elif self.condition == "change_lt" and previous_value is not None:
            change = (current_value - previous_value) / abs(previous_value) if abs(previous_value) > 1e-6 else 0
            triggered = change < self.threshold
            actual_value = change
            
        else:
            triggered = False
            actual_value = current_value
        
        return triggered, actual_value

# ==================== 监控报警系统 ====================

class MonitorAlert:
    """监控报警系统"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 报警渠道
        self.channels: Dict[AlertChannel, AlertChannelBase] = {}
        self._init_channels()
        
        # 监控规则
        self.rules: Dict[str, MonitoringRule] = {}
        self._init_default_rules()
        
        # 报警历史
        self.alert_history: List[Alert] = []
        self.max_history_size = config.get("max_history_size", 1000)
        
        # 策略表现历史
        self.performance_history: Dict[str, List[StrategyPerformance]] = {}
        
        # 系统健康状态
        self.system_health = SystemHealth(
            timestamp=datetime.now(),
            components={},
            overall_status="healthy",
            issues=[]
        )
        
        # 报警抑制（避免重复报警）
        self.alert_suppression: Dict[str, datetime] = {}
        self.suppression_duration = timedelta(minutes=config.get("suppression_minutes", 30))
        
        # 监控线程
        self.monitor_thread = None
        self.running = False
        self.check_interval = config.get("check_interval", 300)  # 默认5分钟
        
        logger.info("监控报警系统初始化完成")
    
    def _init_channels(self):
        """初始化报警渠道"""
        channel_configs = self.config.get("channels", {})
        
        # 邮件渠道
        if "email" in channel_configs:
            try:
                email_channel = EmailAlertChannel(channel_configs["email"])
                if email_channel.test_connection():
                    self.channels[AlertChannel.EMAIL] = email_channel
                    logger.info("邮件报警渠道初始化成功")
                else:
                    logger.warning("邮件报警渠道连接测试失败")
            except Exception as e:
                logger.error(f"邮件报警渠道初始化失败: {e}")
        
        # 微信渠道
        if "wechat" in channel_configs:
            try:
                wechat_channel = WeChatAlertChannel(channel_configs["wechat"])
                if wechat_channel.test_connection():
                    self.channels[AlertChannel.WECHAT] = wechat_channel
                    logger.info("微信报警渠道初始化成功")
                else:
                    logger.warning("微信报警渠道连接测试失败")
            except Exception as e:
                logger.error(f"微信报警渠道初始化失败: {e}")
        
        # 日志渠道（总是可用）
        self.channels[AlertChannel.LOG] = LogAlertChannel({})
        logger.info("日志报警渠道初始化成功")
    
    def _init_default_rules(self):
        """初始化默认监控规则"""
        default_rules = [
            # 绩效指标规则
            MonitoringRule(
                rule_id="sharpe_low",
                metric="sharpe_ratio",
                condition="lt",
                threshold=0.5,
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                description="夏普比率过低"
            ),
            MonitoringRule(
                rule_id="max_dd_high",
                metric="max_drawdown",
                condition="gt",
                threshold=0.2,
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.WECHAT],
                description="最大回撤过高"
            ),
            MonitoringRule(
                rule_id="win_rate_low",
                metric="win_rate",
                condition="lt",
                threshold=0.4,
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                description="胜率过低"
            ),
            MonitoringRule(
                rule_id="daily_loss_high",
                metric="daily_pnl",
                condition="lt",
                threshold=-0.05,
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.WECHAT],
                description="单日亏损过大"
            ),
            
            # 风险指标规则
            MonitoringRule(
                rule_id="var_95_breach",
                metric="var_95",
                condition="lt",
                threshold=-0.03,
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                description="95% VaR突破"
            ),
            MonitoringRule(
                rule_id="position_concentration",
                metric="position_concentration",
                condition="gt",
                threshold=0.3,
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                description="持仓集中度过高"
            ),
            
            # 系统指标规则
            MonitoringRule(
                rule_id="cpu_high",
                metric="cpu_usage",
                condition="gt",
                threshold=0.8,
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                description="CPU使用率过高"
            ),
            MonitoringRule(
                rule_id="memory_high",
                metric="memory_usage",
                condition="gt",
                threshold=0.8,
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL],
                description="内存使用率过高"
            ),
            MonitoringRule(
                rule_id="disk_low",
                metric="disk_usage",
                condition="gt",
                threshold=0.9,
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.WECHAT],
                description="磁盘空间不足"
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
        
        logger.info(f"初始化了 {len(default_rules)} 个默认监控规则")
    
    def add_rule(self, rule: MonitoringRule):
        """添加监控规则"""
        self.rules[rule.rule_id] = rule
        logger.info(f"添加监控规则: {rule.rule_id}")
    
    def remove_rule(self, rule_id: str):
        """移除监控规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"移除监控规则: {rule_id}")
    
    def update_strategy_performance(self, performance: StrategyPerformance):
        """更新策略表现"""
        strategy_id = performance.strategy_id
        
        if strategy_id not in self.performance_history:
            self.performance_history[strategy_id] = []
        
        # 添加新数据
        self.performance_history[strategy_id].append(performance)
        
        # 保持历史数据大小
        if len(self.performance_history[strategy_id]) > 100:  # 保留最近100条
            self.performance_history[strategy_id] = self.performance_history[strategy_id][-100:]
        
        # 检查监控规则
        self._check_strategy_rules(performance)
    
    def _check_strategy_rules(self, performance: StrategyPerformance):
        """检查策略监控规则"""
        strategy_id = performance.strategy_id
        metrics = performance.metrics
        
        # 获取历史数据用于变化检测
        history = self.performance_history.get(strategy_id, [])
        previous_metrics = history[-2].metrics if len(history) >= 2 else None
        
        # 检查所有规则
        for rule_id, rule in self.rules.items():
            # 只检查该策略相关的指标
            if rule.metric in metrics:
                current_value = metrics[rule.metric]
                previous_value = previous_metrics.get(rule.metric) if previous_metrics else None
                
                # 检查规则
                triggered, actual_value = rule.check(current_value, previous_value)
                
                if triggered:
                    # 检查报警抑制
                    suppression_key = f"{strategy_id}_{rule_id}"
                    if self._is_suppressed(suppression_key):
                        continue
                    
                    # 创建报警
                    alert = Alert(
                        alert_id=f"alert_{len(self.alert_history)}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        level=rule.level,
                        title=rule.description,
                        message=f"策略 {strategy_id} 的指标 {rule.metric} 触发报警规则 {rule_id}",
                        metric=rule.metric,
                        value=actual_value,
                        threshold=rule.threshold,
                        strategy_id=strategy_id
                    )
                    
                    # 发送报警
                    self._send_alert(alert, rule.channels)
                    
                    # 记录报警
                    self.alert_history.append(alert)
                    if len(self.alert_history) > self.max_history_size:
                        self.alert_history = self.alert_history[-self.max_history_size:]
                    
                    # 设置报警抑制
                    self.alert_suppression[suppression_key] = datetime.now()
    
    def _is_suppressed(self, suppression_key: str) -> bool:
        """检查是否被抑制"""
        if suppression_key in self.alert_suppression:
            suppression_time = self.alert_suppression[suppression_key]
            if datetime.now() - suppression_time < self.suppression_duration:
                return True
        
        return False
    
    def _send_alert(self, alert: Alert, channels: List[AlertChannel]):
        """发送报警到指定渠道"""
        for channel in channels:
            if channel in self.channels:
                try:
                    success = self.channels[channel].send_alert(alert)
                    if success:
                        logger.info(f"报警 {alert.alert_id} 通过渠道 {channel.value} 发送成功")
                    else:
                        logger.warning(f"报警 {alert.alert_id} 通过渠道 {channel.value} 发送失败")
                except Exception as e:
                    logger.error(f"报警发送异常 {channel.value}: {e}")
    
    def update_system_health(self, component: str, status: Dict):
        """更新系统健康状态"""
        self.system_health.components[component] = status
        self.system_health.timestamp = datetime.now()
        
        # 重新计算整体状态
        self._recalculate_system_health()
        
        # 检查系统健康规则
        self._check_system_rules()
    
    def _recalculate_system_health(self):
        """重新计算系统整体健康状态"""
        issues = []
        
        for component, status in self.system_health.components.items():
            if status.get("status") == "unhealthy":
                issues.append(f"组件 {component} 不健康: {status.get('message', '')}")
            elif status.get("status") == "degraded":
                issues.append(f"组件 {component} 降级: {status.get('message', '')}")
        
        if issues:
            self.system_health.issues = issues
            if any("不健康" in issue for issue in issues):
                self.system_health.overall_status = "unhealthy"
            else:
                self.system_health.overall_status = "degraded"
        else:
            self.system_health.issues = []
            self.system_health.overall_status = "healthy"
    
    def _check_system_rules(self):
        """检查系统监控规则"""
        # 检查系统组件状态
        for component, status in self.system_health.components.items():
            if status.get("status") == "unhealthy":
                # 创建系统报警
                alert = Alert(
                    alert_id=f"system_alert_{len(self.alert_history)}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    level=AlertLevel.CRITICAL,
                    title=f"系统组件 {component} 不健康",
                    message=f"系统组件 {component} 报告不健康状态: {status.get('message', '未知错误')}",
                    metric="system_health",
                    value=0,
                    threshold=1,
                    strategy_id="system"
                )
                
                # 发送报警
                self._send_alert(alert, [AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.WECHAT])
                
                # 记录报警
                self.alert_history.append(alert)
    
    def start_monitoring(self, strategy_id: str = None):
        """开始监控"""
        if self.running:
            logger.warning("监控已经在运行中")
            return
        
        self.running = True
        
        def monitor_loop():
            while self.running:
                try:
                    # 执行监控检查
                    self._monitor_check()
                    
                    # 清理过期的报警抑制
                    self._cleanup_suppression()
                    
                except Exception as e:
                    logger.error(f"监控检查错误: {e}")
                
                # 等待下次检查
                time.sleep(self.check_interval)
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"监控已启动，检查间隔: {self.check_interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("监控已停止")
    
    def _monitor_check(self):
        """执行监控检查"""
        # 这里可以添加自定义的监控检查逻辑
        # 例如：检查数据库连接、检查API可用性、检查磁盘空间等
        
        # 示例：检查系统资源
        self._check_system_resources()
        
        # 示例：检查策略表现（如果有策略在运行）
        self._check_running_strategies()
    
    def _check_system_resources(self):
        """检查系统资源"""
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 更新系统健康状态
            self.update_system_health("cpu", {
                "status": "healthy" if cpu_percent < 80 else "degraded" if cpu_percent < 95 else "unhealthy",
                "usage": cpu_percent,
                "message": f"CPU使用率: {cpu_percent:.1f}%"
            })
            
            self.update_system_health("memory", {
                "status": "healthy" if memory_percent < 80 else "degraded" if memory_percent < 95 else "unhealthy",
                "usage": memory_percent,
                "message": f"内存使用率: {memory_percent:.1f}%"
            })
            
            self.update_system_health("disk", {
                "status": "healthy" if disk_percent < 85 else "degraded" if disk_percent < 95 else "unhealthy",
                "usage": disk_percent,
                "message": f"磁盘使用率: {disk_percent:.1f}%"
            })
            
        except ImportError:
            logger.warning("psutil未安装，无法检查系统资源")
        except Exception as e:
            logger.error(f"检查系统资源失败: {e}")
    
    def _check_running_strategies(self):
        """检查运行中的策略"""
        # 这里应该从策略管理器获取运行中的策略状态
        # 目前是空实现
        
        pass
    
    def _cleanup_suppression(self):
        """清理过期的报警抑制"""
        now = datetime.now()
        expired_keys = []
        
        for key, suppression_time in self.alert_suppression.items():
            if now - suppression_time > self.suppression_duration:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.alert_suppression[key]
    
    def get_alerts(self, start_time: Optional[datetime] = None, 
                  end_time: Optional[datetime] = None,
                  level: Optional[AlertLevel] = None,
                  strategy_id: Optional[str] = None) -> List[Alert]:
        """获取报警历史"""
        filtered = self.alert_history
        
        if start_time:
            filtered = [a for a in filtered if a.timestamp >= start_time]
        
        if end_time:
            filtered = [a for a in filtered if a.timestamp <= end_time]
        
        if level:
            filtered = [a for a in filtered if a.level == level]
        
        if strategy_id:
            filtered = [a for a in filtered if a.strategy_id == strategy_id]
        
        return filtered
    
    def acknowledge_alert(self, alert_id: str, user: str = "system"):
        """确认报警"""
        for alert in self.alert_history:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = user
                alert.acknowledged_time = datetime.now()
                logger.info(f"报警 {alert_id} 已被 {user} 确认")
                return True
        
        return False
    
    def get_system_health(self) -> SystemHealth:
        """获取系统健康状态"""
        return self.system_health
    
    def get_performance_history(self, strategy_id: str, limit: int = 100) -> List[StrategyPerformance]:
        """获取策略表现历史"""
        if strategy_id in self.performance_history:
            return self.performance_history[strategy_id][-limit:]
        return []

# ==================== 测试函数 ====================

def test_monitor_alert():
    """测试监控报警系统"""
    print("测试监控报警系统...")
    
    # 创建配置
    config = {
        "check_interval": 10,  # 测试用，10秒检查一次
        "suppression_minutes": 1,  # 测试用，1分钟抑制
        "max_history_size": 100,
        "channels": {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "test@example.com",
                "password": "password",
                "from_email": "test@example.com",
                "to_emails": ["admin@example.com"]
            },
            "wechat": {
                "corp_id": "your_corp_id",
                "corp_secret": "your_corp_secret",
                "agent_id": "your_agent_id"
            }
        }
    }
    
    # 创建监控报警系统
    monitor = MonitorAlert(config)
    
    # 添加自定义规则
    custom_rule = MonitoringRule(
        rule_id="custom_profit_low",
        metric="total_return",
        condition="lt",
        threshold=-0.1,
        level=AlertLevel.WARNING,
        channels=[AlertChannel.LOG],
        description="总收益率过低"
    )
    monitor.add_rule(custom_rule)
    
    # 模拟策略表现数据
    performance = StrategyPerformance(
        strategy_id="test_strategy_001",
        timestamp=datetime.now(),
        metrics={
            "sharpe_ratio": 0.3,  # 触发夏普比率过低报警
            "max_drawdown": 0.15,
            "win_rate": 0.45,
            "daily_pnl": -0.02,
            "total_return": -0.05,
            "var_95": -0.025,
            "position_concentration": 0.25
        },
        positions=[],
        trades_today=[]
    )
    
    # 更新策略表现（触发报警）
    print("更新策略表现（触发报警）...")
    monitor.update_strategy_performance(performance)
    
    # 获取报警
    alerts = monitor.get_alerts()
    print(f"当前报警数量: {len(alerts)}")
    
    for alert in alerts[-3:]:  # 显示最近3个报警
        print(f"报警: {alert.title} - 级别: {alert.level.value}")
    
    # 获取系统健康状态
    health = monitor.get_system_health()
    print(f"\n系统健康状态: {health.overall_status}")
    
    # 启动监控
    print("\n启动监控...")
    monitor.start_monitoring()
    
    # 等待一段时间
    print("等待15秒让监控运行...")
    import time
    time.sleep(15)
    
    # 停止监控
    monitor.stop_monitoring()
    print("监控已停止")
    
    # 获取最终报警数量
    final_alerts = monitor.get_alerts()
    print(f"最终报警数量: {len(final_alerts)}")
    
    return monitor

if __name__ == "__main__":
    test_monitor_alert()