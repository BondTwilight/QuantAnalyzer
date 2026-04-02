"""
工具模块 — 报告生成、预警通知
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import REPORTS_DIR

logger = logging.getLogger(__name__)


def generate_daily_report(results: list, save_path=None) -> str:
    """生成每日HTML分析报告"""
    if not results:
        return "<p>无回测数据</p>"

    today = datetime.now().strftime("%Y-%m-%d")

    # 排序
    sorted_results = sorted(results, key=lambda x: x.get("annual_return", 0), reverse=True)

    # 构建HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>量化策略日报 - {today}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #58a6ff; margin-bottom: 10px; font-size: 24px; }}
        .date {{ color: #8b949e; margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        th {{ background: #161b22; color: #58a6ff; padding: 12px; text-align: left; font-size: 13px; border-bottom: 2px solid #30363d; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #21262d; font-size: 13px; }}
        tr:hover {{ background: #161b22; }}
        .positive {{ color: #3fb950; }}
        .negative {{ color: #f85149; }}
        .highlight {{ background: #1f6feb22; }}
        .score-a {{ color: #3fb950; font-weight: bold; }}
        .score-b {{ color: #d29922; font-weight: bold; }}
        .score-c {{ color: #f85149; font-weight: bold; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .kpi-card {{ background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; }}
        .kpi-label {{ font-size: 12px; color: #8b949e; margin-bottom: 5px; }}
        .kpi-value {{ font-size: 24px; font-weight: bold; }}
        .kpi-change {{ font-size: 12px; margin-top: 5px; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #58a6ff; margin-bottom: 15px; font-size: 18px; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
        .badge-green {{ background: #23863633; color: #3fb950; }}
        .badge-red {{ background: #da363333; color: #f85149; }}
        .badge-yellow {{ background: #9e6a0333; color: #d29922; }}
        .disclaimer {{ margin-top: 40px; padding: 15px; background: #161b22; border-radius: 8px; font-size: 11px; color: #8b949e; border-left: 3px solid #d29922; }}
        @media (max-width: 768px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 量化策略日报</h1>
        <div class="date">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 数据截止: {today}</div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">策略总数</div>
                <div class="kpi-value">{len(results)}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">最佳年化收益</div>
                <div class="kpi-value positive">{sorted_results[0].get('annual_return', 0):.1%}</div>
                <div class="kpi-change">{sorted_results[0].get('strategy_name', '')}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">平均夏普比率</div>
                <div class="kpi-value">{sum(r.get('sharpe_ratio', 0) for r in results) / len(results):.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">平均最大回撤</div>
                <div class="kpi-value negative">{abs(sum(r.get('max_drawdown', 0) for r in results) / len(results)):.1%}</div>
            </div>
        </div>

        <div class="section">
            <h2>📋 策略排名</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>策略</th>
                        <th>年化收益</th>
                        <th>最大回撤</th>
                        <th>夏普比率</th>
                        <th>Sortino</th>
                        <th>胜率</th>
                        <th>盈亏比</th>
                        <th>交易次数</th>
                        <th>Beta</th>
                    </tr>
                </thead>
                <tbody>"""

    for i, r in enumerate(sorted_results):
        ar = r.get("annual_return", 0)
        ar_class = "positive" if ar > 0 else "negative"
        mdd = abs(r.get("max_drawdown", 0))
        sr = r.get("sharpe_ratio", 0)
        sr_class = "score-a" if sr > 1.5 else ("score-b" if sr > 0.8 else "score-c")

        badge = '<span class="badge badge-green">TOP</span>' if i < 3 else ""
        if mdd > 0.3:
            badge += ' <span class="badge badge-red">高风险</span>'
        elif sr > 1.5:
            badge += ' <span class="badge badge-green">优秀</span>'

        html += f"""
                    <tr class="{'highlight' if i < 3 else ''}">
                        <td>{i + 1}</td>
                        <td>{r.get('strategy_name', '')} {badge}</td>
                        <td class="{ar_class}">{ar:.2%}</td>
                        <td class="negative">{mdd:.2%}</td>
                        <td class="{sr_class}">{sr:.2f}</td>
                        <td>{r.get('sortino_ratio', '-') or '-'}</td>
                        <td>{r.get('win_rate', 0):.1%}</td>
                        <td>{r.get('profit_loss_ratio', 0):.2f}</td>
                        <td>{r.get('total_trades', 0)}</td>
                        <td>{r.get('beta', '-') or '-'}</td>
                    </tr>"""

    html += """
                </tbody>
            </table>
        </div>

        <div class="disclaimer">
            ⚠️ 免责声明：本报告由量化策略回测系统自动生成，仅供学习研究参考，不构成任何投资建议。
            历史回测结果不代表未来收益，投资有风险，入市需谨慎。
        </div>
    </div>
</body>
</html>"""

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"日报已保存: {save_path}")

    return html


def check_alerts(results: list) -> list:
    """检测策略异常并生成预警"""
    alerts = []
    for r in results:
        name = r.get("strategy_name", "")

        # 大幅回撤预警
        if abs(r.get("max_drawdown", 0)) > 0.25:
            alerts.append({"type": "danger", "strategy": name, "msg": f"最大回撤 {abs(r.get('max_drawdown', 0)):.1%}，超过25%警戒线"})

        # 收益异常低
        if r.get("annual_return", 0) < -0.1:
            alerts.append({"type": "danger", "strategy": name, "msg": f"年化收益 {r.get('annual_return', 0):.1%}，策略可能失效"})

        # 夏普比率过低
        if r.get("sharpe_ratio", 0) < 0.5:
            alerts.append({"type": "warning", "strategy": name, "msg": f"夏普比率 {r.get('sharpe_ratio', 0):.2f}，风险调整收益不佳"})

        # 换手率过高
        if r.get("trade_frequency", 0) > 50:
            alerts.append({"type": "warning", "strategy": name, "msg": f"年换手 {r.get('trade_frequency', 0):.0f} 次，交易成本可能过高"})

        # 胜率过低
        if r.get("win_rate", 0) < 0.35:
            alerts.append({"type": "info", "strategy": name, "msg": f"胜率 {r.get('win_rate', 0):.1%}，需要关注"})

    return alerts
