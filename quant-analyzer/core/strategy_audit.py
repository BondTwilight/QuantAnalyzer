"""
量化策略逻辑审查模块
基于【全维量化逻辑审查专家】方法论

审查维度：
1. 程序逻辑审查 ("把事情做对")
2. 策略逻辑审查 ("做正确的事")
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class IssueSeverity(Enum):
    """问题严重等级"""
    CRITICAL = "🔴 致命"
    WARNING = "🟡 警告"
    INFO = "🔵 提示"
    OK = "🟢 正常"


@dataclass
class LogicIssue:
    """逻辑问题"""
    dimension: str  # 维度：程序/策略
    category: str   # 分类
    severity: IssueSeverity
    title: str
    description: str
    location: str   # 代码位置
    consequence: str  # 灾难后果
    fix_diff: str    # Diff修复方案
    extreme_scenario: str  # 极限推演


class StrategyAuditor:
    """量化策略逻辑审查器"""
    
    def __init__(self, strategy_code: str = ""):
        self.strategy_code = strategy_code
        self.issues: List[LogicIssue] = []
        
    def run_full_audit(self) -> Dict[str, Any]:
        """执行全盘审查"""
        self.issues = []
        
        # 维度一：程序逻辑审查
        self._check_t1_restriction()
        self._check_limit_up_down()
        self._check_suspension_status()
        self._check_future_function()
        self._check_state_machine()
        
        # 维度二：策略逻辑审查
        self._check_indicator_appropriateness()
        self._check_parameter_sensitivity()
        self._check_benchmark_normalization()
        self._check_overfitting_risk()
        
        return self._generate_report()
    
    def _check_t1_restriction(self):
        """检查 T+1 铁律"""
        # 检测是否有当日买卖同一股票
        t1_patterns = [
            ("当日重复买入", r"buy.*buy|order.*order.*same.*day"),
            ("缺少持仓检查", r"buy.*without.*position"),
            ("卖出时无持仓验证", r"sell.*without.*check"),
        ]
        
        # 示例检测逻辑
        if "buy" in self.strategy_code.lower():
            if "sell" in self.strategy_code.lower():
                # 检查是否有T+1处理
                if "can_trade" not in self.strategy_code.lower():
                    self.issues.append(LogicIssue(
                        dimension="程序逻辑",
                        category="T+1铁律",
                        severity=IssueSeverity.CRITICAL,
                        title="疑似违反 A 股 T+1 交易制度",
                        description="检测到买入和卖出逻辑，但未发现持仓可交易状态检查",
                        location="交易执行函数",
                        consequence="当日买入的股票在卖出时会触发持仓不足错误，导致策略中断",
                        fix_diff="""```diff
- if should_buy(context, stock):
+ if should_buy(context, stock) and can_trade_today(context, stock):
      order_target_percent(stock, 0.1)
```""",
                        extreme_scenario="在千股跌停日，策略尝试止损但因T+1限制无法卖出，只能眼睁睁看着仓位继续亏损"
                    ))
    
    def _check_limit_up_down(self):
        """检查涨跌停状态"""
        limit_patterns = [
            ("涨跌停买入检测", r"buy.*limit.*up|追涨停"),
            ("涨跌停卖出检测", r"sell.*limit.*down|跌停卖"),
        ]
        
        # 检测涨跌停状态下的是否有保护
        if "order" in self.strategy_code.lower():
            if "limit_up" not in self.strategy_code.lower() and "limit_down" not in self.strategy_code.lower():
                self.issues.append(LogicIssue(
                    dimension="程序逻辑",
                    category="涨跌停保护",
                    severity=IssueSeverity.WARNING,
                    title="缺少涨跌停状态检测",
                    description="交易逻辑中未检测股票涨跌停状态",
                    location="下单函数附近",
                    consequence="在涨跌停时挂单会因无法成交而浪费交易机会或暴露交易意图",
                    fix_diff="""```diff
+ # 获取涨跌停状态
+ limit_up = is_limit_up(stock, context.now)
+ limit_down = is_limit_down(stock, context.now)
+ 
+ if should_sell and not limit_down:
      order_target_percent(stock, 0)
```""",
                    extreme_scenario="连续涨停股无法买入，策略踏空行情；跌停股无法止损，亏损持续扩大"
                ))
    
    def _check_suspension_status(self):
        """检查停牌状态"""
        if "order" in self.strategy_code.lower():
            if "suspended" not in self.strategy_code.lower() and "停牌" not in self.strategy_code:
                self.issues.append(LogicIssue(
                    dimension="程序逻辑",
                    category="停牌保护",
                    severity=IssueSeverity.WARNING,
                    title="缺少停牌股票过滤",
                    description="下单前未检查股票是否处于停牌状态",
                    location="选股或下单逻辑",
                    consequence="对停牌股票下单会导致订单失败或资金占用",
                    fix_diff="""```diff
+ # 过滤停牌股票
+ tradable_stocks = [s for s in candidates 
+                    if not is_suspended(s, context.now)]
```""",
                    extreme_scenario="重组或重大事项停牌期间资金被锁定，无法灵活调整仓位"
                ))
    
    def _check_future_function(self):
        """检查未来函数"""
        future_patterns = [
            ("当日收盘价预用", r"close\[0\].*上午|日内.*收盘价"),
            ("使用未来数据", r"shift.*-1|future.*data"),
            ("收盘价决策", r"if.*close.*>|收盘.*买入"),
        ]
        
        # 示例检测
        if "close[0]" in self.strategy_code or "close(0)" in self.strategy_code:
            self.issues.append(LogicIssue(
                dimension="程序逻辑",
                category="未来函数",
                severity=IssueSeverity.CRITICAL,
                title="疑似使用当日收盘价进行盘中决策",
                description="代码中使用了 close[0] 或 close(0)，这在盘中是未知数据",
                location="信号生成函数",
                consequence="回测结果虚高，实盘中无法执行，导致严重的幸存者偏差",
                fix_diff="""```diff
- signal = close[0] > ma5  # 错误：使用当根K线收盘价
+ signal = close[-1] > ma5  # 使用前一根K线数据
```""",
                extreme_scenario="在V型反转行情中，盘中追高信号完美命中收盘价，但实盘永远无法执行"
            ))
    
    def _check_state_machine(self):
        """检查状态机死锁"""
        state_patterns = [
            ("状态重置检查", r"reset.*state|状态.*重置"),
            ("状态切换逻辑", r"state.*transition|状态.*切换"),
        ]
        
        # 示例：如果有买入信号但无平仓条件
        has_buy = "buy" in self.strategy_code.lower()
        has_sell = "sell" in self.strategy_code.lower()
        has_state = "state" in self.strategy_code.lower()
        
        if has_buy and has_sell and not has_state:
            self.issues.append(LogicIssue(
                dimension="程序逻辑",
                category="状态机完整性",
                severity=IssueSeverity.INFO,
                title="缺少显式状态管理",
                description="策略有买入和卖出逻辑，但未发现明确的状态机定义",
                location="主循环/调度函数",
                consequence="复杂行情下可能发生状态混乱，如重复开仓或错过平仓时机",
                fix_diff="""```diff
+ # 状态定义
+ POSITION_OPEN = "open"
+ POSITION_HOLD = "hold"  
+ POSITION_CLOSED = "closed"
+ 
+ def handle_signal(context, signal, current_state):
+     if current_state == POSITION_CLOSED and signal == "BUY":
+         return POSITION_OPEN
+     elif current_state == POSITION_OPEN and signal == "FILLED":
+         return POSITION_HOLD
+     # ...
```""",
                extreme_scenario="在高波动行情中，状态混乱导致策略在开平仓之间反复横跳"
            ))
    
    def _check_indicator_appropriateness(self):
        """检查指标适用性"""
        # RSI 在震荡市 vs 趋势市
        if "RSI" in self.strategy_code or "rsi" in self.strategy_code.lower():
            if "trend" not in self.strategy_code.lower():
                self.issues.append(LogicIssue(
                    dimension="策略逻辑",
                    category="指标适用性",
                    severity=IssueSeverity.WARNING,
                    title="RSI 指标在趋势行情中可能失效",
                    description="RSI 是超买超卖指标，在趋势行情中会长期处于极端值",
                    location="指标计算/信号函数",
                    consequence="在趋势行情中 RSI 持续发出错误信号，导致频繁止损",
                    fix_diff="""```diff
+ # 结合趋势过滤器使用 RSI
+ def get_signal(stock):
+     trend = get_trend(stock)  # 判断趋势方向
+     rsi_value = calculate_rsi(stock)
+     
+     if trend == "UPTREND" and rsi_value < 30:
+         return "BUY"  # 趋势向上 + 超卖 = 买入
+     elif trend == "DOWNTREND" and rsi_value > 70:
+         return "SELL"  # 趋势向下 + 超买 = 卖出
```""",
                    extreme_scenario="2015年牛市顶部，RSI 长期在80以上钝化，策略不断卖出踏空"
                ))
        
        # 短期均线在震荡市
        if "MA5" in self.strategy_code or "ma5" in self.strategy_code.lower():
            self.issues.append(LogicIssue(
                dimension="策略逻辑",
                category="指标适用性",
                severity=IssueSeverity.INFO,
                title="短期均线在震荡市中信号频繁",
                description="MA5 对价格变化敏感，在震荡市会产生大量假信号",
                location="均线交叉/信号函数",
                consequence="交易成本增加，收益被手续费侵蚀",
                fix_diff="""```diff
- ma_cross = close > MA5 and close > MA10
+ # 加入波动率过滤
+ volatility = calculate_volatility(stock, window=20)
+ if volatility > high_vol_threshold:
+     ma_cross = close > MA20 and close > MA60  # 高波动用长周期
+ else:
+     ma_cross = close > MA5 and close > MA10
```""",
                extreme_scenario="震荡市中频繁开平仓，手续费成为主要亏损来源"
            ))
    
    def _check_parameter_sensitivity(self):
        """检查参数敏感性"""
        # 检测硬编码阈值
        hardcoded_thresholds = []
        
        if "30%" in self.strategy_code or ">30" in self.strategy_code:
            hardcoded_thresholds.append("30% (溢价率/波动率阈值)")
        if "3%" in self.strategy_code or ">3" in self.strategy_code:
            hardcoded_thresholds.append("3% (涨跌/回撤阈值)")
        if "5%" in self.strategy_code or ">5" in self.strategy_code:
            hardcoded_thresholds.append("5% (止损/止盈阈值)")
        
        if hardcoded_thresholds:
            self.issues.append(LogicIssue(
                dimension="策略逻辑",
                category="参数敏感性",
                severity=IssueSeverity.WARNING,
                title="存在硬编码阈值参数",
                description=f"检测到硬编码阈值: {', '.join(hardcoded_thresholds)}",
                location="多个信号/风控函数",
                consequence="参数可能过度拟合历史行情，在新行情中表现急剧下降",
                fix_diff="""```diff
# 硬编码
- if return < -0.03:  # 硬编码止损
-     sell()

# 参数化
+ def set_stop_loss(threshold=None):
+     threshold = threshold or get_default("stop_loss", -0.05)
+     if return < threshold:
+         sell()
+ 
+ # 或使用滚动优化
+ optimal_threshold = optimize_parameter(
+     "stop_loss", 
+     range(-0.02, -0.10, -0.01)
+ )
```""",
                extreme_scenario="2020年新冠疫情导致波动率骤增，固定3%止损被频繁触发，策略在底部被洗出"
            ))
    
    def _check_benchmark_normalization(self):
        """检查基准标准化"""
        # 多品种策略缺少标准化
        if any(x in self.strategy_code for x in ["stock", "future", "commodity"]):
            if "normalize" not in self.strategy_code.lower():
                self.issues.append(LogicIssue(
                    dimension="策略逻辑",
                    category="基准谬误",
                    severity=IssueSeverity.WARNING,
                    title="跨品种策略缺少收益标准化",
                    description="不同品种波动率差异巨大，直接比较收益率会导致系统性偏差",
                    location="多品种轮动/配置函数",
                    consequence="策略会系统性偏好高波动品种，导致风险暴露失衡",
                    fix_diff="""```diff
+ # 收益标准化
+ def normalize_returns(returns_dict):
+     normalized = {}
+     for asset, ret in returns_dict.items():
+         # 使用收益率的波动率标准化
+         vol = calculate_rolling_vol(ret, window=20)
+         normalized[asset] = ret / vol if vol > 0 else 0
+     return normalized
```""",
                    extreme_scenario="商品牛市时策略大量配置商品期货，波动率远超股票，导致净值大幅回撤"
                ))
    
    def _check_overfitting_risk(self):
        """检查过拟合风险"""
        overfitting_signals = []
        
        # 过多参数
        param_count = self.strategy_code.count("=")
        if param_count > 10:
            overfitting_signals.append(f"参数数量: {param_count} (>10)")
        
        # 复杂条件
        if self.strategy_code.count(" and ") > 10:
            overfitting_signals.append("过多 AND 条件组合")
        
        # 极短回测周期
        if "days" in self.strategy_code.lower() and "365" not in self.strategy_code:
            overfitting_signals.append("回测周期可能不足一年")
        
        if overfitting_signals:
            self.issues.append(LogicIssue(
                dimension="策略逻辑",
                category="过拟合风险",
                severity=IssueSeverity.INFO,
                title="策略可能存在过拟合",
                description="检测到以下过拟合信号:\n" + "\n".join(f"- {s}" for s in overfitting_signals),
                location="整体策略结构",
                consequence="策略在历史回测中表现优异，但实盘收益锐减",
                fix_diff="""```diff
# 建议改进：
1. 减少参数数量，合并相似参数
- params = {
-     "ma_short": 5,
-     "ma_medium": 10,
-     "ma_long": 20,
- }
+ # 使用相对参数
+ params = {
+     "ma_ratio": 2,  # medium/short ratio
+     "ma_long_ratio": 2,  # long/medium ratio
+ }

2. 增加样本外测试
+ def walk_forward_validate(strategy, start, end, test_window=60):
+     results = []
+     for train_end in range(start + test_window, end, test_window):
+         train_data = get_data(start, train_end)
+         test_data = get_data(train_end, train_end + test_window)
+         # 优化参数
+         optimal = optimize(train_data)
+         # 样本外测试
+         result = backtest(strategy, optimal, test_data)
+         results.append(result)
+     return aggregate(results)
```""",
                extreme_scenario="2015年股灾后的反弹行情与回测期行情特征完全不同，策略完全失效"
            ))
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成审查报告"""
        # 按维度分类
        program_issues = [i for i in self.issues if i.dimension == "程序逻辑"]
        strategy_issues = [i for i in self.issues if i.dimension == "策略逻辑"]
        
        # 按严重程度统计
        critical = sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)
        warning = sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)
        info = sum(1 for i in self.issues if i.severity == IssueSeverity.INFO)
        
        return {
            "summary": {
                "total_issues": len(self.issues),
                "critical": critical,
                "warning": warning,
                "info": info,
                "score": max(0, 100 - critical * 30 - warning * 10 - info * 2),
                "grade": self._get_grade(critical, warning),
            },
            "program_issues": [self._issue_to_dict(i) for i in program_issues],
            "strategy_issues": [self._issue_to_dict(i) for i in strategy_issues],
            "recommendations": self._generate_recommendations(program_issues, strategy_issues),
        }
    
    def _get_grade(self, critical: int, warning: int) -> str:
        """获取评级"""
        if critical >= 3:
            return "F - 禁止实盘"
        elif critical >= 1:
            return "D - 需紧急修复"
        elif warning >= 3:
            return "C - 建议优化"
        elif warning >= 1:
            return "B - 可接受"
        else:
            return "A - 优秀"
    
    def _issue_to_dict(self, issue: LogicIssue) -> Dict[str, str]:
        """转换问题为字典"""
        return {
            "severity": issue.severity.value,
            "category": issue.category,
            "title": issue.title,
            "description": issue.description,
            "location": issue.location,
            "consequence": issue.consequence,
            "fix_diff": issue.fix_diff,
            "extreme_scenario": issue.extreme_scenario,
        }
    
    def _generate_recommendations(self, program: List, strategy: List) -> List[str]:
        """生成综合建议"""
        recs = []
        
        if any(i.severity == IssueSeverity.CRITICAL for i in program):
            recs.append("🔴 存在致命程序逻辑问题，必须修复后再进行回测")
        
        if any(i.severity == IssueSeverity.WARNING for i in program):
            recs.append("🟡 建议增加交易机制保护（涨跌停、T+1、停牌检测）")
        
        if any("参数敏感性" in i.category for i in strategy):
            recs.append("📊 建议使用参数优化或敏感性分析验证阈值合理性")
        
        if any("过拟合" in i.category for i in strategy):
            recs.append("📈 建议增加样本外测试和蒙特卡洛模拟")
        
        if not program and not strategy:
            recs.append("🟢 策略逻辑审查通过，建议进行样本外验证")
        
        return recs


def audit_strategy_code(code: str) -> Dict[str, Any]:
    """快速审查策略代码"""
    auditor = StrategyAuditor(code)
    return auditor.run_full_audit()


def audit_backtest_result(result: Dict) -> Dict[str, Any]:
    """基于回测结果进行事后审查"""
    issues = []
    
    # 检查最大回撤
    if result.get("max_drawdown", 0) > 0.2:
        issues.append({
            "type": "风险控制",
            "detail": f"最大回撤 {result['max_drawdown']:.1%}，超过20%警戒线"
        })
    
    # 检查胜率
    if result.get("win_rate", 0) < 0.4:
        issues.append({
            "type": "盈利模式",
            "detail": f"胜率 {result['win_rate']:.1%}，低于40%，需验证盈亏比"
        })
    
    # 检查交易频率
    if result.get("trade_count", 0) / result.get("days", 1) > 0.5:
        issues.append({
            "type": "交易成本",
            "detail": "日均交易超过0.5次，高频交易需注意手续费影响"
        })
    
    return {
        "backtest_issues": issues,
        "needs_attention": len(issues) > 0,
    }


# ============ 辅助函数 ============

def is_limit_up(stock: str, date: pd.Timestamp, threshold: float = 0.1) -> bool:
    """判断是否涨停"""
    # 实际实现需要数据源
    return False


def is_limit_down(stock: str, date: pd.Timestamp, threshold: float = 0.1) -> bool:
    """判断是否跌停"""
    return False


def is_suspended(stock: str, date: pd.Timestamp) -> bool:
    """判断是否停牌"""
    return False


def can_trade_today(context, stock: str) -> bool:
    """判断股票当日是否可以交易（T+1检查）"""
    # 实际实现需要持仓数据
    return True
