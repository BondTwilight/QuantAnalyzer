"""
📚 策略知识库页面 — 量化策略研究与因子提取

核心功能：
1. 展示从"安达量化"等来源提取的策略体系
2. 策略分类与可行性评级
3. 因子库可视化
4. 策略与AlphaForge的集成状态
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# ═══════════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════════
st.set_page_config(
    page_title="策略知识库 | QuantBrain",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 样式
st.markdown("""<style>
.kb-header {
    background: linear-gradient(135deg, #1a1f35, #141929);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid #1e293b;
    margin-bottom: 20px;
}
.kb-title {
    font-size: 28px; font-weight: 800;
    background: linear-gradient(90deg, #3b82f6, #a855f7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.kb-sub { color: #94a3b8; font-size: 13px; margin-top: 4px; }

.kb-strategy-card {
    background: linear-gradient(135deg, #1a1f35, #141929);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    transition: all 0.2s;
}
.kb-strategy-card:hover { border-color: #3b82f6; }
.kb-strategy-name { font-size: 18px; font-weight: 700; color: #f8fafc; }
.kb-strategy-desc { font-size: 13px; color: #94a3b8; margin-top: 6px; line-height: 1.6; }
.kb-badge {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 11px; font-weight: 700; margin-right: 6px;
}
.kb-badge-green { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.kb-badge-blue { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
.kb-badge-yellow { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.kb-badge-red { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
.kb-badge-purple { background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }

.kb-factor-chip {
    display: inline-block; background: #111827; border: 1px solid #1e293b;
    border-radius: 8px; padding: 4px 10px; margin: 3px;
    font-size: 11px; color: #93c5fd; font-family: 'Courier New', monospace;
}
.kb-rating {
    display: inline-flex; gap: 4px;
}
.kb-star { color: #fbbf24; font-size: 14px; }
.kb-star.empty { color: #334155; }

.kb-section-title {
    font-size: 18px; font-weight: 700; color: #e2e8f0;
    margin: 24px 0 16px; display: flex; align-items: center; gap: 8px;
}
.kb-section-title::before {
    content: ''; width: 4px; height: 22px;
    background: linear-gradient(180deg, #3b82f6, #8b5cf6);
    border-radius: 2px;
}

.kb-table { width: 100%; border-collapse: collapse; margin: 12px 0; }
.kb-table th {
    background: #111827; color: #94a3b8; font-size: 12px; font-weight: 600;
    padding: 10px 14px; text-align: left; border-bottom: 2px solid #1e293b;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.kb-table td {
    color: #cbd5e1; font-size: 13px; padding: 10px 14px;
    border-bottom: 1px solid #1e293b;
}
.kb-table tr:hover { background: rgba(59,130,246,0.05); }

.kb-integration-status {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 6px;
}
.kb-integration-status.done { background: #10b981; box-shadow: 0 0 6px #10b981; }
.kb-integration-status.partial { background: #fbbf24; box-shadow: 0 0 6px #fbbf24; }
.kb-integration-status.pending { background: #64748b; }
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 页面标题
# ═══════════════════════════════════════════════
st.markdown("""
<div class="kb-header">
    <div class="kb-title">📚 策略知识库</div>
    <div class="kb-sub">从实战量化博主的策略体系中提取因子、评估可行性、集成到 AlphaForge 自动进化系统</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 策略来源概览
# ═══════════════════════════════════════════════
st.markdown('<div class="kb-section-title">📊 策略来源</div>', unsafe_allow_html=True)

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
col_s1.markdown(f"""<div class="kb-strategy-card" style="text-align:center;padding:16px;">
    <div style="font-size:28px;">📝</div>
    <div style="font-size:24px;font-weight:800;color:#f8fafc;">32</div>
    <div style="font-size:11px;color:#94a3b8;">安达量化笔记</div>
</div>""", unsafe_allow_html=True)

col_s2.markdown(f"""<div class="kb-strategy-card" style="text-align:center;padding:16px;">
    <div style="font-size:28px;">🎯</div>
    <div style="font-size:24px;font-weight:800;color:#f8fafc;">6</div>
    <div style="font-size:11px;color:#94a3b8;">独立策略</div>
</div>""", unsafe_allow_html=True)

col_s3.markdown(f"""<div class="kb-strategy-card" style="text-align:center;padding:16px;">
    <div style="font-size:28px;">🧪</div>
    <div style="font-size:24px;font-weight:800;color:#f8fafc;">48</div>
    <div style="font-size:11px;color:#94a3b8;">种子因子</div>
</div>""", unsafe_allow_html=True)

col_s4.markdown(f"""<div class="kb-strategy-card" style="text-align:center;padding:16px;">
    <div style="font-size:28px;">✅</div>
    <div style="font-size:24px;font-weight:800;color:#f8fafc;">31</div>
    <div style="font-size:11px;color:#94a3b8;">已集成因子</div>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 策略详情
# ═══════════════════════════════════════════════
st.markdown('<div class="kb-section-title">🔬 策略深度解析</div>', unsafe_allow_html=True)

strategies = [
    {
        "name": "🛡️ ETF 超跌抄底 V1 — LightGBM",
        "source": "安达量化 · ETF抄底策略揭秘",
        "rating": 3,
        "claim_return": "年化 45%",
        "feasibility": "中等",
        "feasibility_cls": "yellow",
        "badges": [("机器学习", "purple"), ("ETF", "blue"), ("分类模型", "blue")],
        "desc": "用 LightGBM 分类模型识别 ETF 超跌后反弹概率。80个特征覆盖宏观/中观/微观三层。阈值≥0.80 时胜率 84.62%，平均反弹 9.18%。AUC=0.67。",
        "factors": 11,
        "factors_list": ["-ts_zscore(close,10)", "-rsi(close,5)/100", "ts_std(returns,5)*(-1)",
                        "ts_sum(min(returns,0),5)/ts_sum(abs(returns),5)"],
        "risk": "AUC偏低、无卖出规则、无仓位管理、高阈值样本不足(仅13个)",
        "integration": "done",
    },
    {
        "name": "🚀 ETF 超跌抄底 V2 — 极致优化",
        "source": "安达量化 · 年化65%的抄底模型，极致优化",
        "rating": 3,
        "claim_return": "年化 65%",
        "feasibility": "待验证",
        "feasibility_cls": "red",
        "badges": [("机器学习", "purple"), ("集成学习", "blue"), ("动态仓位", "green")],
        "desc": "在 V1 基础上的极致优化版本。可能增加了：多模型集成(LightGBM+XGBoost)、动态阈值、卖出规则、Kelly仓位管理。",
        "factors": 0,
        "factors_list": ["推测: 更多微观结构特征", "预测: 多时间框架融合"],
        "risk": "过拟合风险更高、年化65%需样本外验证、具体规则未公开",
        "integration": "partial",
    },
    {
        "name": "⚡ 动量轮动策略",
        "source": "安达量化 · 别再瞎买ETF了！顶级机构的动量轮动策略",
        "rating": 4,
        "claim_return": "业界年化 15-30%",
        "feasibility": "较高",
        "feasibility_cls": "green",
        "badges": [("动量", "green"), ("轮动", "blue"), ("ETF", "blue")],
        "desc": "基于「强者恒强」效应，选择近期表现强势的 ETF 持有。计算 N 日动量，排名后买入前 K 个。业界经典策略，学术和实盘均有大量验证。",
        "factors": 4,
        "factors_list": ["ts_delta(close,10)/close", "ts_delta(close,20)/close", 
                        "ts_rank(ts_delta(close,20),60)", "ts_delta(close,10)-ts_delta(close,20)"],
        "risk": "熊市/反转时失效、需要合理的标的池、调仓成本",
        "integration": "done",
    },
    {
        "name": "📈 双均线策略",
        "source": "安达量化 · 只靠两条均线，轻松年化27%",
        "rating": 3,
        "claim_return": "年化 27%",
        "feasibility": "中等",
        "feasibility_cls": "yellow",
        "badges": [("均线", "blue"), ("趋势跟踪", "green"), ("简单有效", "green")],
        "desc": "基于快慢均线交叉的经典趋势跟踪策略。年化27%说明可能使用了非标准周期+趋势强度过滤+成交量确认等增强手段。",
        "factors": 4,
        "factors_list": ["sma(close,5)/sma(close,60)-1", "ema(close,12)/ema(close,26)-1",
                        "(sma(close,5)>sma(close,20))*1.0", "(sma(close,10)-sma(close,5))/sma(close,5)"],
        "risk": "震荡市频繁假信号、趋势结束后滞后性亏损",
        "integration": "done",
    },
    {
        "name": "🌊 小波分析趋势反转",
        "source": "安达量化 · 股票趋势反转的小波分析",
        "rating": 2,
        "claim_return": "未知",
        "feasibility": "较低",
        "feasibility_cls": "red",
        "badges": [("小波变换", "purple"), ("信号处理", "blue"), ("趋势识别", "green")],
        "desc": "用小波变换(Wavelet Transform)分解价格序列，提取低频趋势分量和高频噪声分量。当低频分量方向改变时产生趋势反转信号。",
        "factors": 2,
        "factors_list": ["ts_skewness(returns,20)", "ts_skewness(returns,20)*(-1)"],
        "risk": "计算复杂、小波参数选择敏感、容易过拟合、信号滞后",
        "integration": "partial",
    },
    {
        "name": "🧩 低相关组合策略",
        "source": "安达量化 · 今天收益最高的是低相关组合策略",
        "rating": 4,
        "claim_return": "整体降低回撤",
        "feasibility": "高",
        "feasibility_cls": "green",
        "badges": [("组合优化", "purple"), ("风险分散", "green"), ("核心思想", "blue")],
        "desc": "同时运行 4 条低相关性策略，利用策略间的不相关性降低整体组合回撤。'大盘跌量化全涨'说明具有择时对冲效果。这是投资组合理论的核心思想。",
        "factors": 0,
        "factors_list": ["思想集成: StrategyEnsemble 多因子融合",
                        "实现: IC加权 + 风险控制 + Kelly仓位"],
        "risk": "策略相关性可能随市场环境漂移、需要持续监控",
        "integration": "done",
    },
]

for s in strategies:
    stars = "★" * s["rating"] + "☆" * (5 - s["rating"])
    int_status = {"done": "✅ 已集成", "partial": "🟡 部分集成", "pending": "⏳ 待集成"}[s["integration"]]
    int_cls = {"done": "kb-integration-status done", "partial": "kb-integration-status partial", 
               "pending": "kb-integration-status pending"}[s["integration"]]
    
    badges_html = "".join(f'<span class="kb-badge kb-badge-{bc}">{bt}</span>' for bt, bc in s["badges"])
    factors_html = "".join(f'<span class="kb-factor-chip">{f}</span>' for f in s["factors_list"])
    
    st.markdown(f"""
    <div class="kb-strategy-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
                <div class="kb-strategy-name">{s['name']}</div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">{s['source']}</div>
            </div>
            <div style="text-align:right;">
                <div class="kb-rating kb-star">{stars}</div>
                <div style="font-size:12px;color:#94a3b8;">声称: {s['claim_return']}</div>
                <div><span class="kb-badge kb-badge-{s['feasibility_cls']}">可行性: {s['feasibility']}</span></div>
            </div>
        </div>
        <div style="margin-top:8px;">{badges_html}</div>
        <div class="kb-strategy-desc">{s['desc']}</div>
        
        <div style="margin-top:12px;display:flex;gap:16px;flex-wrap:wrap;">
            <div>
                <span style="font-size:11px;color:#64748b;font-weight:600;">⚠️ 核心风险:</span>
                <span style="font-size:12px;color:#fbbf24;">{s['risk']}</span>
            </div>
        </div>
        
        <div style="margin-top:10px;">
            <span style="font-size:11px;color:#64748b;font-weight:600;">🧪 AlphaForge 集成因子 ({s['factors']}个):</span>
            <span class="{int_cls}"></span><span style="font-size:11px;color:#94a3b8;">{int_status}</span>
            <div style="margin-top:6px;">{factors_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 因子分类汇总
# ═══════════════════════════════════════════════
st.markdown('<div class="kb-section-title">🧪 因子分类汇总</div>', unsafe_allow_html=True)

with st.expander("📋 全部 48 个种子因子（按类别分组）", expanded=False):
    factor_groups = {
        "📊 动量类": [
            "ts_delta(close, 5) / ts_std(close, 20)",
            "ts_mean(close, 5) / ts_mean(close, 20) - 1",
            "momentum(close, 10)", "roc(close, 5)",
            "ts_delta(close, 10) / close",
            "ts_delta(close, 20) / close",
            "ts_rank(ts_delta(close, 20), 60)",
            "ts_delta(close, 10) - ts_delta(close, 20)",
        ],
        "📈 均线类": [
            "sma(close, 5) / sma(close, 20) - 1",
            "ema(close, 5) / ema(close, 20) - 1",
            "close / sma(close, 10) - 1",
            "sma(close, 5) / sma(close, 60) - 1",
            "ema(close, 12) / ema(close, 26) - 1",
            "(sma(close, 5) > sma(close, 20)) * 1.0",
            "(sma(close, 10) - sma(close, 5)) / sma(close, 5)",
        ],
        "📉 超跌反弹类": [
            "-ts_zscore(close, 10)", "-ts_zscore(close, 5)",
            "ts_min(low, 5) / sma(close, 20)",
            "ts_min(low, 10) / sma(close, 60)",
            "(close - sma(close, 5)) / sma(close, 5)",
            "-rsi(close, 5) / 100",
            "ts_std(returns, 5) * (-1)",
            "ts_sum(min(returns, 0), 5) / ts_sum(abs(returns), 5)",
            "ts_rank(close, 5) / 5 * (-1)",
            "ts_delta(close, 3) / ts_std(close, 20) * (-1)",
            "ts_corr(close, volume, 5) * (-1)",
            "(ts_min(close, 10) - close) / close",
        ],
        "🌊 波动率类": [
            "ts_std(close, 5) / ts_std(close, 20)",
            "ts_std(close, 10) / ts_std(close, 30)",
            "-ts_std(returns, 10)",
            "ts_std(returns, 5) / ts_std(returns, 20)",
            "-ts_std(returns, 20) / ts_std(returns, 60)",
            "ts_zscore(ts_std(returns, 10), 60)",
        ],
        "📦 成交量类": [
            "ts_mean(volume, 5) / ts_mean(volume, 20)",
            "volume / ts_mean(volume, 10)",
            "ts_rank(volume, 10)",
            "volume / ts_max(volume, 20)",
            "ts_corr(returns, volume, 10) * (-1)",
            "ts_std(volume, 10) / ts_mean(volume, 10)",
        ],
        "🎯 趋势强度类": [
            "rsi(close, 14)", "ts_zscore(close, 20)",
            "ts_rank(close, 10)",
            "ts_max(high, 10) - ts_min(low, 10)",
            "(ts_max(high, 20) - ts_min(low, 20)) / sma(close, 20)",
            "ts_argmax(high, 20) / 20",
            "ts_argmin(low, 20) / 20",
        ],
        "🔄 统计特征类": [
            "ts_skewness(returns, 20)",
            "ts_skewness(returns, 20) * (-1)",
        ],
        "🧩 复合类": [
            "ts_corr(close, volume, 10)",
            "ts_delta(close, 5) * ts_rank(volume, 10)",
            "ts_mean(close, 5) / ts_std(close, 10)",
            "(close - ts_min(close, 10)) / (ts_max(close, 10) - ts_min(close, 10))",
        ],
    }
    
    total = 0
    for group_name, factors in factor_groups.items():
        total += len(factors)
        factors_html = "".join(f'<span class="kb-factor-chip">{f}</span>' for f in factors)
        st.markdown(f"""
        <div style="margin:12px 0;">
            <span style="font-size:14px;font-weight:600;color:#e2e8f0;">{group_name}</span>
            <span style="font-size:11px;color:#64748b;margin-left:8px;">({len(factors)}个因子)</span>
            <div style="margin-top:6px;">{factors_html}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"<div style='text-align:right;color:#64748b;font-size:12px;padding:8px;'>共 {total} 个种子因子</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 集成状态总览
# ═══════════════════════════════════════════════
st.markdown('<div class="kb-section-title">🔗 AlphaForge 集成状态</div>', unsafe_allow_html=True)

st.markdown("""
<table class="kb-table">
    <thead>
        <tr>
            <th>策略</th>
            <th>因子数</th>
            <th>集成状态</th>
            <th>AlphaForge 中的角色</th>
            <th>优先级</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>ETF 超跌抄底 V1</td>
            <td>11</td>
            <td><span class="kb-integration-status done"></span>✅ 已集成</td>
            <td>超跌反弹类种子因子</td>
            <td><span class="kb-badge kb-badge-green">高</span></td>
        </tr>
        <tr>
            <td>动量轮动策略</td>
            <td>4</td>
            <td><span class="kb-integration-status done"></span>✅ 已集成</td>
            <td>动量增强类种子因子</td>
            <td><span class="kb-badge kb-badge-green">高</span></td>
        </tr>
        <tr>
            <td>双均线策略</td>
            <td>4</td>
            <td><span class="kb-integration-status done"></span>✅ 已集成</td>
            <td>均线增强类种子因子</td>
            <td><span class="kb-badge kb-badge-green">高</span></td>
        </tr>
        <tr>
            <td>小波分析</td>
            <td>2</td>
            <td><span class="kb-integration-status partial"></span>🟡 部分集成</td>
            <td>统计特征类因子(简化)</td>
            <td><span class="kb-badge kb-badge-yellow">中</span></td>
        </tr>
        <tr>
            <td>低相关组合</td>
            <td>-</td>
            <td><span class="kb-integration-status done"></span>✅ 已集成</td>
            <td>StrategyEnsemble 核心思想</td>
            <td><span class="kb-badge kb-badge-green">高</span></td>
        </tr>
        <tr>
            <td>ETF 抄底 V2</td>
            <td>0</td>
            <td><span class="kb-integration-status pending"></span>⏳ 待集成</td>
            <td>需获取详细规则后集成</td>
            <td><span class="kb-badge kb-badge-yellow">中</span></td>
        </tr>
        <tr>
            <td>AI 数据重构</td>
            <td>0</td>
            <td><span class="kb-integration-status pending"></span>⏳ 待集成</td>
            <td>数据预处理模块</td>
            <td><span class="kb-badge kb-badge-red">低</span></td>
        </tr>
    </tbody>
</table>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 底部
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#334155;font-size:11px;padding:8px;'>
    📚 策略知识库 v1.0 — 数据来源: 安达量化(小红书) | 
    因子提取: 48个种子因子 → AlphaForge 自动进化 | 
    仅供学习研究，不构成投资建议
</div>""", unsafe_allow_html=True)
