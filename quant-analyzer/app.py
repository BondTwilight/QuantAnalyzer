"""
QuantAnalyzer v3.0 — 专业量化策略分析平台
基于全景指南全面升级：专业UI、K线图、市场看板、收益热力图、交易明细、风险仪表盘
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging

# ── 项目路径 ──
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from config import PAGE_CONFIG, AI_PROVIDERS, THEME_COLORS, REPORTS_DIR

# ── 页面配置 ──
st.set_page_config(**PAGE_CONFIG)

# ── 专业金融仪表盘主题 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── 全局 ── */
.stApp {
    background: #0a0e17;
    font-family: 'Inter', -apple-system, 'Microsoft YaHei', sans-serif;
}
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: rgba(10,14,23,0.9); backdrop-filter: blur(20px); }

/* ── 侧边栏 ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1320 0%, #0a0e17 100%);
    border-right: 1px solid #1a2235;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(59,130,246,0.1);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 12px;
}

/* ── KPI卡片 ── */
.kpi-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin: 16px 0;
}
.kpi-card {
    background: linear-gradient(135deg, #111827 0%, #1a2235 100%);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px 20px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.kpi-card.green::before { background: linear-gradient(90deg, #10b981, #34d399); }
.kpi-card.blue::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.kpi-card.orange::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.kpi-card.red::before { background: linear-gradient(90deg, #ef4444, #f87171); }
.kpi-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.kpi-label {
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}
.kpi-value {
    color: #f1f5f9;
    font-size: 24px;
    font-weight: 800;
    line-height: 1.2;
}
.kpi-sub {
    color: #475569;
    font-size: 11px;
    margin-top: 4px;
}
.kpi-change-up { color: #10b981; font-size: 12px; font-weight: 600; }
.kpi-change-down { color: #ef4444; font-size: 12px; font-weight: 600; }

/* ── 表格 ── */
.dataframe th {
    background: #111827 !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    border-bottom: 2px solid #1e293b !important;
}
.dataframe td {
    color: #cbd5e1 !important;
    font-size: 13px !important;
    border-bottom: 1px solid #1e293b !important;
}
.dataframe tr:hover { background: rgba(59,130,246,0.05) !important; }

/* ── Badge ── */
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 0.3px; }
.badge-green { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.badge-red { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
.badge-yellow { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.badge-blue { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
.badge-purple { background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }

/* ── Alert ── */
.alert-box {
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 12px;
    font-size: 13px;
    border-left: 4px solid;
}
.alert-danger { background: rgba(239,68,68,0.08); border-color: #ef4444; color: #fca5a5; }
.alert-warning { background: rgba(245,158,11,0.08); border-color: #f59e0b; color: #fcd34d; }
.alert-info { background: rgba(59,130,246,0.08); border-color: #3b82f6; color: #93c5fd; }
.alert-success { background: rgba(16,185,129,0.08); border-color: #10b981; color: #6ee7b7; }

/* ── Section Title ── */
.section-title {
    font-size: 16px;
    font-weight: 700;
    color: #e2e8f0;
    margin: 24px 0 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title::before {
    content: '';
    width: 4px;
    height: 20px;
    background: linear-gradient(180deg, #3b82f6, #8b5cf6);
    border-radius: 2px;
}

/* ── Tab ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #111827;
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-size: 13px;
    font-weight: 500;
    color: #64748b;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    color: white !important;
}

/* ── Metric ── */
[data-testid="stMetricValue"] {
    font-size: 22px !important;
    font-weight: 800 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Glass Card ── */
.glass-card {
    background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(30,41,59,0.6));
    backdrop-filter: blur(10px);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 20px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a0e17; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #334155; }

/* ── Button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #60a5fa, #3b82f6);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59,130,246,0.3);
}

/* ── Chart Container ── */
.chart-container {
    background: linear-gradient(135deg, #111827, #1a2235);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# Session State
# ═══════════════════════════════════════════
if "db" not in st.session_state:
    from data.fetcher import db as _db
    st.session_state.db = _db
if "ai_provider" not in st.session_state:
    st.session_state.ai_provider = "zhipu"
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = "暂无数据"


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════
def get_rating(score):
    if score >= 80: return '<span class="badge badge-green">S</span>'
    elif score >= 65: return '<span class="badge badge-green">A</span>'
    elif score >= 50: return '<span class="badge badge-blue">B</span>'
    elif score >= 35: return '<span class="badge badge-yellow">C</span>'
    else: return '<span class="badge badge-red">D</span>'

def compute_score(r):
    ar = r.get("annual_return", 0)
    mdd = abs(r.get("max_drawdown", 0))
    sr = r.get("sharpe_ratio", 0)
    wr = r.get("win_rate", 0)
    plr = r.get("profit_loss_ratio", 0)
    return min(30, max(0, ar*200)) + max(0, 20-mdd*100) + min(20, max(0, sr*10)) + wr*15 + min(15, max(0, plr*5))

def fmt_pct(v, signed=False):
    if pd.isna(v) or v is None: return "N/A"
    prefix = "+" if signed and v >= 0 else ""
    return f"{prefix}{v:.2%}"

def fmt_num(v, decimals=2):
    if pd.isna(v) or v is None: return "N/A"
    return f"{v:.{decimals}f}"

def render_kpi_card(label, value, sub="", color="blue", change=None):
    ch = ""
    if change is not None:
        cls = "kpi-change-up" if change >= 0 else "kpi-change-down"
        ch = f'<div class="{cls}">{"↑" if change>=0 else "↓"} {abs(change):.2%}</div>'
    return f'''<div class="kpi-card {color}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>{ch}
    </div>'''

def render_alerts(alerts):
    for a in alerts:
        cls = f"alert-{a['type']}"
        icons = {"danger":"🔴","warning":"🟡","info":"🔵","success":"🟢"}
        st.markdown(f'<div class="{cls}"><strong>{icons.get(a["type"],"ℹ️")} {a["strategy"]}</strong> — {a["msg"]}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # Logo区域
        st.markdown("""
        <div style="text-align:center;padding:12px 0 8px;">
            <div style="font-size:28px;font-weight:900;background:linear-gradient(135deg,#3b82f6,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                QuantAnalyzer
            </div>
            <div style="color:#475569;font-size:11px;letter-spacing:1px;">专业量化策略分析平台 v2.0</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # 导航
        pages = [
            "🏠 首页",
            "⚔️ 策略PK",
            "📊 策略总览",
            "📚 策略库",
            "🌐 平台对比",
            "🧠 代码分析",
            "🏦 市场看板",
            "📈 专业分析",
            "🔮 AI预测",
            "📉 K线分析",
            "📋 交易明细",
            "🗓️ 收益日历",
            "🤖 AI 分析",
            "⚠️ 风险仪表盘",
            "⚙️ 系统设置",
        ]
        selected = st.radio("导航", pages, label_visibility="collapsed")

        # 清除导航状态（防止session_state污染）
        if "page_navigate" in st.session_state:
            selected = st.session_state["page_navigate"]
            del st.session_state["page_navigate"]

        st.markdown("---")
        # AI模型选择
        st.markdown('<div class="kpi-label" style="margin-bottom:8px;">🤖 AI 模型</div>', unsafe_allow_html=True)
        providers = {k: v["name"] for k, v in AI_PROVIDERS.items()}
        prov = st.selectbox("选择模型", list(providers.keys()), format_func=lambda x: providers[x], label_visibility="collapsed")
        st.session_state.ai_provider = prov
        api_key = AI_PROVIDERS[prov].get("api_key", "")
        if api_key:
            st.markdown('<div class="alert-box alert-success" style="padding:8px 12px;">✅ API已配置</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-box alert-warning" style="padding:8px 12px;">⚠️ 未配置API Key（规则分析兜底）</div>', unsafe_allow_html=True)

        st.markdown("---")
        # 快捷操作
        st.markdown('<div class="kpi-label" style="margin-bottom:8px;">⚡ 快捷操作</div>', unsafe_allow_html=True)

        if st.button("⚔️ 去PK策略", use_container_width=True, type="primary"):
            st.session_state["page_navigate"] = "⚔️ 策略PK"
            st.rerun()

        if st.button("📋 策略库", use_container_width=True):
            st.session_state["page_navigate"] = "📚 策略库"
            st.rerun()
            with st.spinner("生成中..."):
                try:
                    from utils.report import generate_daily_report
                    results = st.session_state.db.get_latest_results().to_dict("records")
                    if results:
                        p = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d')}.html"
                        generate_daily_report(results, p)
                        st.success("✅ 日报已生成!")
                    else:
                        st.warning("暂无数据")
                except Exception as e:
                    st.error(f"失败: {e}")

        st.markdown("---")
        st.markdown('<div style="text-align:center;color:#334155;font-size:10px;line-height:1.6;">'
                    'QuantAnalyzer v2.0<br>仅供学习研究<br>不构成投资建议</div>',
                    unsafe_allow_html=True)

    return selected


# ═══════════════════════════════════════════
# 页面0: 首页仪表盘
# ═══════════════════════════════════════════
def page_home():
    from core.home_page import render_home_page, render_quick_backtest_result
    # 如果有回测结果就显示结果页，否则显示首页
    if st.session_state.get("page_navigate") == "🔬 回测结果" and st.session_state.get("home_backtest_code"):
        render_quick_backtest_result()
    else:
        render_home_page()


# ═══════════════════════════════════════════
# 页面1: 策略总览（升级版）
# ═══════════════════════════════════════════
def page_overview():
    st.title("📊 策略总览")
    st.caption(f"*最后更新: {st.session_state.get('last_refresh','暂无数据')}*")

    db = st.session_state.db
    try:
        results_df = db.get_latest_results()
    except Exception as e:
        st.error(f"数据库错误: {e}")
        return

    if results_df.empty:
        st.markdown('''
        <div style="text-align:center;padding:100px 20px;">
            <div style="font-size:48px;margin-bottom:16px;">🚀</div>
            <h2 style="color:#e2e8f0;">欢迎使用 QuantAnalyzer v2.0</h2>
            <p style="color:#64748b;max-width:500px;margin:12px auto;font-size:14px;">
                暂无回测数据。请点击左侧「运行全部回测」开始首次分析。
            </p>
            <div style="margin-top:24px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap;">
                <span class="badge badge-blue">8大策略</span>
                <span class="badge badge-green">10+指标</span>
                <span class="badge badge-purple">AI分析</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        return

    results = results_df.to_dict("records")

    # ── 预警 ──
    try:
        from utils.report import check_alerts
        alerts = check_alerts(results)
        if alerts:
            st.markdown('<div class="section-title">⚠️ 实时预警</div>', unsafe_allow_html=True)
            render_alerts(alerts)
            st.markdown("---")
    except:
        pass

    # ── KPI卡片 ──
    best = max(results, key=lambda x: x.get("annual_return", 0))
    worst = min(results, key=lambda x: x.get("annual_return", 0))
    avg_sharpe = np.mean([r.get("sharpe_ratio", 0) for r in results])
    avg_mdd = np.mean([abs(r.get("max_drawdown", 0)) for r in results])
    avg_wr = np.mean([r.get("win_rate", 0) for r in results])

    kpi_html = f'''
    <div class="kpi-container">
        {render_kpi_card("策略总数", f"<b>{len(results)}</b>", "覆盖趋势/均值回归/多因子", "blue")}
        {render_kpi_card("最佳年化", f"<b>{fmt_pct(best.get('annual_return',0))}</b>", best.get("strategy_name","")[:15], "green")}
        {render_kpi_card("平均夏普", f"<b>{avg_sharpe:.2f}</b>", "风险调整收益", "purple")}
        {render_kpi_card("平均回撤", f"<b>{avg_mdd:.1%}</b>", "最大回撤控制", "orange")}
        {render_kpi_card("平均胜率", f"<b>{avg_wr:.1%}</b>", "交易胜率", "green")}
    </div>
    '''
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ── 排名表 ──
    for r in results:
        r["_score"] = compute_score(r)
    ranked = sorted(results, key=lambda x: x.get("_score", 0), reverse=True)

    st.markdown('<div class="section-title">🏆 策略排名</div>', unsafe_allow_html=True)
    rows = []
    for i, r in enumerate(ranked):
        ar = r.get("annual_return", 0)
        sr = r.get("sharpe_ratio", 0)
        rows.append({
            "#": f'<span style="color:{"#fbbf24" if i==0 else "#94a3b8"};font-weight:700;">{i+1}</span>',
            "策略": f'<b>{r.get("strategy_name","")}</b>',
            "评级": get_rating(r["_score"]),
            "年化收益": f'<span style="color:{"#34d399" if ar>=0 else "#f87171"};">{fmt_pct(ar)}</span>',
            "最大回撤": f'<span style="color:{"#f87171" if abs(r.get("max_drawdown",0))>0.2 else "#94a3b8"};">{fmt_pct(abs(r.get("max_drawdown",0)))}</span>',
            "夏普": fmt_num(sr),
            "Sortino": fmt_num(r.get("sortino_ratio", 0)) if r.get("sortino_ratio") else "-",
            "胜率": fmt_pct(r.get("win_rate", 0)),
            "盈亏比": fmt_num(r.get("profit_loss_ratio", 0)),
            "交易": r.get("total_trades", 0),
        })
    df_html = pd.DataFrame(rows).to_html(escape=False, index=False)
    st.markdown(f'<div class="chart-container" style="overflow-x:auto;padding:0;">{df_html}</div>', unsafe_allow_html=True)

    # ── 净值曲线 ──
    st.markdown('<div class="section-title">📈 净值曲线对比</div>', unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        palette = ["#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#06b6d4","#84cc16"]
        for idx, r in enumerate(ranked[:6]):
            name = r.get("strategy_name", "")
            try:
                daily = db.get_daily_values(name)
                if not daily.empty:
                    fig.add_trace(go.Scatter(
                        x=daily.index, y=daily["portfolio_value"],
                        name=name, line=dict(color=palette[idx % len(palette)], width=2),
                        hovertemplate="<b>%{text}</b><br>净值: %{y:.2f}<extra></extra>",
                        text=[name] * len(daily),
                    ))
            except:
                pass
        # 基准
        try:
            sample = db.get_daily_values(ranked[0].get("strategy_name", ""))
            if not sample.empty and "benchmark_value" in sample.columns:
                fig.add_trace(go.Scatter(
                    x=sample.index, y=sample["benchmark_value"],
                    name="沪深300基准",
                    line=dict(color="#475569", width=1.5, dash="dot"),
                ))
        except:
            pass
        fig.update_layout(
            template="plotly_dark", height=420,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#94a3b8"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            xaxis=dict(gridcolor="#1e293b", zerolinecolor="#1e293b"),
            yaxis=dict(gridcolor="#1e293b", zerolinecolor="#1e293b"),
            margin=dict(l=40, r=20, t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"图表: {e}")

    # ── 风险-收益散点 ──
    st.markdown('<div class="section-title">🎯 风险-收益分布</div>', unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        fig2 = go.Figure()
        for r in ranked:
            ar = r.get("annual_return", 0)
            mdd = abs(r.get("max_drawdown", 0))
            sr = r.get("sharpe_ratio", 0)
            wr = r.get("win_rate", 0)
            size = 12 + wr * 10
            color = "#10b981" if sr > 1.0 else ("#f59e0b" if sr > 0.5 else "#ef4444")
            fig2.add_trace(go.Scatter(
                x=[mdd * 100], y=[ar * 100],
                name=r.get("strategy_name", ""),
                text=[f"夏普:{sr:.2f} | 胜率:{wr:.0%}"],
                mode="markers+text", marker=dict(color=color, size=size, opacity=0.85,
                    line=dict(color=color, width=2)),
                textposition="top center", textfont=dict(size=10),
                hovertemplate="<b>%{text}</b><extra></extra>",
            ))
        fig2.update_layout(
            template="plotly_dark", height=380,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#94a3b8"),
            xaxis_title="最大回撤 (%)", yaxis_title="年化收益 (%)",
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
            margin=dict(l=50, r=20, t=20, b=40),
        )
        st.plotly_chart(fig2, use_container_width=True)
    except:
        pass




# ═══════════════════════════════════════════
# 页面2: 市场看板（改进版）
# ═══════════════════════════════════════════
def page_market():
    st.title("🏦 市场看板")

    # ── 刷新按钮 ──
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 刷新数据", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        data_source = st.selectbox("数据源", ["BaoStock (免费)", "聚宽 (需注册)"], index=0)

    # ── 指数列表 ──
    indices = [
        ("sh.000001", "上证指数"),
        ("sz.399001", "深证成指"),
        ("sz.399006", "创业板指"),
        ("sh.000300", "沪深300"),
    ]

    # ── 获取数据 ──
    with st.spinner("正在获取市场数据..."):
        indices_data = {}
        
        if "聚宽" in data_source:
            # 聚宽数据源
            try:
                from data.joinquant import JoinQuantFetcher
                jq = JoinQuantFetcher()
                if jq.connected:
                    for code, name in indices:
                        # 转换代码格式
                        jqd_code = code.replace("sh.", "XSHG.").replace("sz.", "XSHE.")
                        df = jq.get_security_bars(jqd_code, count=7)
                        if df is not None:
                            indices_data[name] = df
                    jq.disconnect()
                else:
                    st.warning("聚宽未连接，将使用BaoStock备用")
                    raise Exception("聚宽未连接")
            except Exception as e:
                st.info(f"聚宽连接失败: {e}, 切换到BaoStock...")
        
        if not indices_data:
            # BaoStock备用
            try:
                import baostock as bs
                bs.login()
                end_d = datetime.now().strftime("%Y%m%d")
                start_d = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

                for code, name in indices:
                    rs = bs.query_history_k_data_plus(code, "date,open,high,low,close,volume",
                        start_date=start_d, end_date=end_d, frequency="d", adjustflag="3")
                    rows = []
                    if rs is None:
                        continue
                    while rs.error_code == "0" and rs.next():
                        rows.append(rs.get_row_data())
                    if rows:
                        df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume"])
                        for c in ["open","high","low","close","volume"]:
                            df[c] = pd.to_numeric(df[c], errors="coerce")
                        indices_data[name] = df
                bs.logout()
            except Exception as e:
                st.error(f"数据获取失败: {e}")

    # ── KPI 卡片 ──
    kpi_cards = ""
    success_count = 0
    for code, name in indices:
        df = indices_data.get(name)
        if df is not None and not df.empty:
            success_count += 1
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            price = latest["close"]
            chg = (price - prev["close"]) / prev["close"] * 100 if prev["close"] != 0 else 0
            vol = latest.get("volume", 0)
            color = "green" if chg >= 0 else "red"
            arrow = "↑" if chg >= 0 else "↓"
            kpi_cards += render_kpi_card(
                name, f"<b>{price:.2f}</b>",
                f"{arrow} {abs(chg):.2f}% | 成交量:{vol/1e8:.1f}亿",
                color, chg/100
            )
        else:
            kpi_cards += render_kpi_card(name, "—", "暂无数据", "blue")

    st.markdown(f'<div class="kpi-container">{kpi_cards}</div>', unsafe_allow_html=True)
    
    if success_count > 0:
        st.success(f"✅ 成功获取 {success_count}/{len(indices)} 个指数数据")
    else:
        st.error("❌ 未能获取任何数据，请检查网络连接")

    # ── 大盘走势 ──
    st.markdown('<div class="section-title">📉 大盘近7日走势</div>', unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.7, 0.3], vertical_spacing=0.03,
            subplot_titles=["价格走势", "成交量"])
        palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"]
        for idx, (code, name) in enumerate(indices):
            df = indices_data.get(name)
            if df is not None and not df.empty:
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df["close"], name=name,
                    line=dict(color=palette[idx], width=2),
                ), row=1, col=1)
                fig.add_trace(go.Bar(
                    x=df["date"], y=df["volume"], name=f"{name}量",
                    marker_color=palette[idx], opacity=0.5, showlegend=False,
                ), row=2, col=1)
        fig.update_layout(
            template="plotly_dark", height=480,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5),
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
            xaxis2=dict(gridcolor="#1e293b"), yaxis2=dict(gridcolor="#1e293b"),
            margin=dict(l=40, r=20, t=30, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"图表渲染失败: {e}")

    # ── 数据源说明 ──
    st.markdown('<div class="section-title">📊 数据源说明</div>', unsafe_allow_html=True)
    st.markdown('''
    <div class="glass-card">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;">
            <div>
                <div class="kpi-label">BaoStock (当前)</div>
                <div style="color:#e2e8f0;font-weight:600;">免费 · 无需注册</div>
                <div style="color:#475569;font-size:11px;">直连 · A股+指数</div>
            </div>
            <div>
                <div class="kpi-label">聚宽 (可选)</div>
                <div style="color:#e2e8f0;font-weight:600;">数据更全</div>
                <div style="color:#475569;font-size:11px;">需注册 · 期货/财务因子</div>
            </div>
            <div>
                <div class="kpi-label">数据延迟</div>
                <div style="color:#e2e8f0;font-weight:600;">盘后更新</div>
                <div style="color:#475569;font-size:11px;">交易日15:30后</div>
            </div>
            <div>
                <div class="kpi-label">API配置</div>
                <div style="color:#e2e8f0;font-weight:600;">setup_ai.py</div>
                <div style="color:#475569;font-size:11px;">一键配置数据源</div>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 页面新: 专业分析 (聚宽教程增强)
# ═══════════════════════════════════════════
def page_analysis():
    """专业分析页面 - 基于聚宽教程增强"""
    st.title("📈 专业分析")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 收益率分析", "📋 财务数据", "📈 风险指标", "🔍 策略审查"])
    
    # Tab 1: 收益率分析
    with tab1:
        st.markdown("### 🎯 股票/策略收益率分析")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            stock_code = st.text_input("股票代码", value="600519.SH", help="格式: 600519.SH 或 000001.SZ")
            days = st.slider("回测天数", 30, 500, 120)
            initial_capital = st.number_input("初始资金(元)", value=1000000.0, step=10000.0)
        
        with col2:
            st.markdown("#### 📊 分析指标说明")
            st.markdown("""
            | 指标 | 说明 |
            |------|------|
            | **总收益率** | 持有期间的总收益百分比 |
            | **年化收益率** | 折算为年度的收益率 |
            | **最大回撤** | 历史最大亏损幅度 |
            | **夏普比率** | 风险调整后的收益指标 |
            """)
        
        if st.button("🔍 开始分析", type="primary", use_container_width=True):
            with st.spinner("正在获取数据..."):
                try:
                    from data.joinquant import (
                        calculate_returns, calculate_annual_return, 
                        calculate_max_drawdown, calculate_sharpe_ratio,
                        calculate_volatility, generate_strategy_report
                    )
                    
                    # 获取数据
                    import baostock as bs
                    bs.login()
                    
                    # 转换代码格式
                    code = stock_code
                    if "." in code and not code.startswith("sh.") and not code.startswith("sz."):
                        parts = code.split(".")
                        code = f"{'sh' if parts[1]=='SH' else 'sz'}.{parts[0]}"
                    
                    end_d = datetime.now().strftime("%Y%m%d")
                    start_d = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
                    
                    rs = bs.query_history_k_data_plus(
                        code, "date,open,high,low,close,volume",
                        start_date=start_d, end_date=end_d, frequency="d", adjustflag="2"
                    )
                    rows = []
                    while rs.error_code == "0" and rs.next():
                        rows.append(rs.get_row_data())
                    bs.logout()
                    
                    if not rows:
                        st.error("获取数据失败")
                    else:
                        df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume"])
                        for c in ["open","high","low","close","volume"]:
                            df[c] = pd.to_numeric(df[c], errors="coerce")
                        df["date"] = pd.to_datetime(df["date"])
                        df = df.tail(days).reset_index(drop=True)
                        
                        # 生成分析报告
                        report = generate_strategy_report(df, initial_capital=initial_capital)
                        
                        # 显示KPI卡片
                        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
                        
                        with kpi_col1:
                            st.markdown(f'''
                            <div class="kpi-card {'green' if report['total_return'] > 0 else 'red'}">
                                <div class="kpi-label">总收益率</div>
                                <div class="kpi-value">{report['total_return']:.2%}</div>
                            </div>
                            ''', unsafe_allow_html=True)
                        
                        with kpi_col2:
                            st.markdown(f'''
                            <div class="kpi-card blue">
                                <div class="kpi-label">年化收益率</div>
                                <div class="kpi-value">{report['annual_return']:.2%}</div>
                            </div>
                            ''', unsafe_allow_html=True)
                        
                        with kpi_col3:
                            st.markdown(f'''
                            <div class="kpi-card {'red' if report['max_drawdown'] < 0 else 'green'}">
                                <div class="kpi-label">最大回撤</div>
                                <div class="kpi-value">{report['max_drawdown']:.2%}</div>
                            </div>
                            ''', unsafe_allow_html=True)
                        
                        with kpi_col4:
                            st.markdown(f'''
                            <div class="kpi-card purple">
                                <div class="kpi-label">夏普比率</div>
                                <div class="kpi-value">{report['sharpe_ratio']:.2f}</div>
                            </div>
                            ''', unsafe_allow_html=True)
                        
                        # 详细报告
                        st.markdown("---")
                        st.markdown("#### 📋 详细分析报告")
                        
                        report_col1, report_col2 = st.columns(2)
                        with report_col1:
                            st.markdown(f"""
                            **📈 收益分析**
                            - 初始资金: ¥{report['initial_capital']:,.0f}
                            - 最终资金: ¥{report['final_capital']:,.0f}
                            - 净利润: ¥{report['profit']:,.0f}
                            - 交易天数: {report['trading_days']}天 ({report['years']:.2f}年)
                            """)
                        
                        with report_col2:
                            st.markdown(f"""
                            **📉 风险分析**
                            - 年化波动率: {report['volatility']:.2%}
                            - 最大回撤日期: {report['max_drawdown_low']}
                            - 夏普比率: {report['sharpe_ratio']:.2f}
                            - Beta系数: {report['beta']:.2f}
                            """)
                        
                        # 收益率图表
                        st.markdown("---")
                        st.markdown("#### 📊 收益率曲线")
                        
                        df['cumulative_return'] = (1 + df['close'].pct_change().fillna(0)).cumprod() - 1
                        
                        import plotly.express as px
                        fig = px.line(
                            df, x='date', y='cumulative_return',
                            title=f'{stock_code} 累计收益率',
                            labels={'cumulative_return': '累计收益率', 'date': '日期'}
                        )
                        fig.update_layout(
                            template="plotly_dark",
                            xaxis_rangeslider_visible=True,
                            height=400
                        )
                        fig.update_yaxes(tickformat='.2%')
                        st.plotly_chart(fig, use_container_width=True)
                        
                except Exception as e:
                    st.error(f"分析失败: {e}")
    
    # Tab 2: 财务数据
    with tab2:
        st.markdown("### 📋 上市公司财务数据")
        
        jq_col1, jq_col2 = st.columns([1, 1])
        with jq_col1:
            jq_stock = st.text_input("股票代码", value="000001.SZ", key="jq_stock")
            jq_report_type = st.selectbox(
                "报告类型",
                ["income", "balance", "cashflow"],
                format_func=lambda x: {"income": "利润表", "balance": "资产负债表", "cashflow": "现金流量表"}[x]
            )
        
        with jq_col2:
            st.markdown("**💡 聚宽数据说明**")
            st.markdown("""
            聚宽提供高质量财务数据:
            - 📊 **利润表**: 营收、净利润、毛利率
            - 📄 **资产负债表**: 资产、负债、净资产
            - 💰 **现金流量表**: 经营/投资/筹资现金流
            """)
        
        if st.button("📥 获取财务数据", type="primary"):
            with st.spinner("正在获取财务数据..."):
                try:
                    from data.joinquant import get_financial_report, get_valuation_metrics
                    import os
                    from dotenv import load_dotenv
                    load_dotenv()
                    
                    # 尝试连接聚宽
                    import jqdatasdk as jq
                    
                    username = os.getenv("JQ_USERNAME", "")
                    password = os.getenv("JQ_PASSWORD", "")
                    
                    if username and password:
                        jq.auth(username, password)
                        st.success("✅ 聚宽已连接")
                        
                        # 获取财务报告
                        finance_df = get_financial_report(jq_stock, jq_report_type, count=4)
                        
                        if finance_df is not None and not finance_df.empty:
                            st.markdown(f"#### {jq_stock} {jq_report_type} 数据")
                            st.dataframe(finance_df, use_container_width=True)
                            
                            # 下载按钮
                            csv = finance_df.to_csv(index=False)
                            st.download_button(
                                "📥 下载CSV",
                                csv,
                                file_name=f"{jq_stock}_{jq_report_type}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("暂无财务数据，请检查股票代码")
                        
                        # 获取估值指标
                        st.markdown("---")
                        st.markdown("#### 📊 估值指标")
                        metrics = get_valuation_metrics(jq_stock)
                        if metrics:
                            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                            with metric_col1:
                                st.metric("市盈率(PE)", f"{metrics.get('pe_ratio', 0):.2f}")
                            with metric_col2:
                                st.metric("市净率(PB)", f"{metrics.get('pb_ratio', 0):.2f}")
                            with metric_col3:
                                st.metric("市销率(PS)", f"{metrics.get('ps_ratio', 0):.2f}")
                            with metric_col4:
                                st.metric("总市值(亿)", f"{metrics.get('market_cap', 0)/1e8:.2f}")
                        else:
                            st.warning("无法获取估值指标")
                        
                        jq.logout()
                    else:
                        st.warning("请先在设置中配置聚宽账号 (JQ_USERNAME, JQ_PASSWORD)")
                        
                except ImportError:
                    st.error("请先安装聚宽SDK: pip install jqdatasdk")
                except Exception as e:
                    st.error(f"获取财务数据失败: {e}")
    
    # Tab 3: 风险指标
    with tab3:
        st.markdown("### 📈 风险指标计算器")
        
        risk_col1, risk_col2 = st.columns([1, 1])
        with risk_col1:
            st.markdown("#### 🎯 个股风险分析")
            risk_stock = st.text_input("股票代码", value="600519.SH", key="risk_stock")
            risk_days = st.slider("分析周期(天)", 30, 500, 120)
            
            if st.button("📊 计算风险指标", type="primary"):
                try:
                    import baostock as bs
                    bs.login()
                    
                    code = risk_stock
                    if "." in code and not code.startswith("sh.") and not code.startswith("sz."):
                        parts = code.split(".")
                        code = f"{'sh' if parts[1]=='SH' else 'sz'}.{parts[0]}"
                    
                    end_d = datetime.now().strftime("%Y%m%d")
                    start_d = (datetime.now() - timedelta(days=risk_days * 2)).strftime("%Y%m%d")
                    
                    rs = bs.query_history_k_data_plus(
                        code, "date,close", start_date=start_d, end_date=end_d, frequency="d"
                    )
                    rows = []
                    while rs.error_code == "0" and rs.next():
                        rows.append(rs.get_row_data())
                    bs.logout()
                    
                    if rows:
                        df = pd.DataFrame(rows, columns=["date","close"])
                        df["close"] = pd.to_numeric(df["close"], errors="coerce")
                        df = df.tail(risk_days).reset_index(drop=True)
                        
                        from data.joinquant import calculate_returns, calculate_volatility, calculate_sharpe_ratio, calculate_max_drawdown
                        
                        returns = calculate_returns(df)
                        volatility = calculate_volatility(returns)
                        sharpe = calculate_sharpe_ratio(returns)
                        max_dd, _, _ = calculate_max_drawdown(df)
                        
                        r_col1, r_col2, r_col3, r_col4 = st.columns(4)
                        with r_col1:
                            st.metric("年化波动率", f"{volatility:.2%}")
                        with r_col2:
                            st.metric("夏普比率", f"{sharpe:.2f}")
                        with r_col3:
                            st.metric("最大回撤", f"{max_dd:.2%}")
                        with r_col4:
                            daily_vol = returns.std()
                            st.metric("日波动率", f"{daily_vol:.2%}")
                        
                        # 风险等级
                        risk_score = abs(max_dd) * 0.4 + volatility * 0.3 + (1 - sharpe/3 if sharpe > 0 else 1) * 0.3
                        if risk_score < 0.2:
                            risk_level = "🟢 低风险"
                            risk_color = "green"
                        elif risk_score < 0.4:
                            risk_level = "🟡 中低风险"
                            risk_color = "yellow"
                        elif risk_score < 0.6:
                            risk_level = "🟠 中风险"
                            risk_color = "orange"
                        else:
                            risk_level = "🔴 高风险"
                            risk_color = "red"
                        
                        st.markdown(f"#### {risk_level}")
                        st.progress(min(risk_score, 1.0), text=f"风险指数: {risk_score:.2%}")
                    else:
                        st.warning("暂无数据")
                        
                except Exception as e:
                    st.error(f"计算失败: {e}")
        
        with risk_col2:
            st.markdown("#### 📖 风险指标说明")
            st.markdown("""
            **年化波动率 (Volatility)**
            衡量收益率的离散程度，波动率越高表示价格变动越剧烈。
            
            **夏普比率 (Sharpe Ratio)**
            每承担一单位风险所获得的超额收益，>1为优秀，>2为极佳。
            
            **最大回撤 (Max Drawdown)**
            从最高点到最低点的最大跌幅，反映极端风险。
            
            **Beta系数**
            衡量个股相对市场的波动程度。Beta>1表示比市场波动更大。
            
            **风险指数**
            综合波动率、回撤、夏普比率计算的综合风险评分。
            """)
    
    # Tab 4: 策略逻辑审查
    with tab4:
        st.markdown("### 🔍 量化策略逻辑审查")
        st.markdown("基于【全维量化逻辑审查专家】方法论，检测策略代码中的致命逻辑漏洞")
        
        audit_col1, audit_col2 = st.columns([1, 1])
        
        with audit_col1:
            st.markdown("#### 📝 输入策略代码")
            st.caption("粘贴您的策略代码，系统将自动进行双维度审查")
            
            strategy_code = st.text_area(
                "策略代码",
                height=400,
                placeholder="""# 示例策略代码
def handle_data(context, data):
    stock = context.portfolio.positions[0]
    
    # 获取RSI指标
    rsi = data[stock].mavg(14, "rsi")
    
    # 买入信号
    if rsi < 30 and cash > 10000:
        order(stock, 100)
    
    # 卖出信号
    if rsi > 70:
        order_target_percent(stock, 0)
    
    # 止损
    if returns < -0.03:
        sell()
""",
                key="strategy_code_input"
            )
            
            # 示例代码快捷按钮
            if st.button("📋 加载示例代码", use_container_width=True):
                sample_code = '''# 简单均线策略
def handle_data(context, data):
    for stock in context.portfolio.positions:
        # 使用当日收盘价判断
        if data[stock].close > data[stock].mavg(5):
            order_target_percent(stock, 0.1)
        else:
            order_target_percent(stock, 0)

# 选股
def before_trading_start(context):
    stocks = get_stock_list()
    for s in stocks[:10]:
        if data[s].close > data[s].mavg(5):
            buy(s, 10000)
'''
                st.session_state.strategy_code_input = sample_code
            
            run_audit = st.button("🔍 开始审查", type="primary", use_container_width=True)
        
        with audit_col2:
            st.markdown("#### 📋 审查维度说明")
            st.markdown("""
            **维度一：程序逻辑审查** ("把事情做对")
            - 🔴 T+1 铁律检查
            - 🔴 涨跌停状态检测
            - 🟡 停牌股票过滤
            - 🟡 未来函数检测
            - 🔵 状态机完整性
            
            **维度二：策略逻辑审查** ("做正确的事")
            - 🟡 指标适用性分析
            - 🟡 参数敏感性测试
            - 🟡 过拟合风险评估
            - 🔵 基准标准化检查
            """)
        
        # 执行审查
        if run_audit and strategy_code:
            with st.spinner("正在审查策略逻辑..."):
                try:
                    from core.strategy_audit import StrategyAuditor, audit_strategy_code
                    
                    # 执行审查
                    report = audit_strategy_code(strategy_code)
                    
                    # 显示评分
                    st.markdown("---")
                    st.markdown("### 📊 审查报告")
                    
                    score = report["summary"]
                    grade_col1, grade_col2, grade_col3, grade_col4 = st.columns(4)
                    
                    with grade_col1:
                        grade = score["grade"]
                        grade_color = "🟢" if "A" in grade else "🟡" if "B" in grade else "🟠" if "C" in grade else "🔴"
                        st.markdown(f"""
                        <div style="background: {'#2d7d46' if 'A' in grade else '#c9a227' if 'B' in grade else '#d97706' if 'C' in grade else '#dc2626'}; padding: 20px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: white;">{grade}</div>
                            <div style="color: rgba(255,255,255,0.8);">策略评级</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with grade_col2:
                        st.metric("总分", f"{score['score']}/100", 
                                  delta="优秀" if score['score'] >= 80 else "合格" if score['score'] >= 60 else "需改进")
                    
                    with grade_col3:
                        st.metric("致命问题", f"{score['critical']}个", 
                                  delta="⚠️ 需修复" if score['critical'] > 0 else "✅ 无",
                                  delta_color="inverse")
                    
                    with grade_col4:
                        st.metric("警告问题", f"{score['warning']}个",
                                  delta="⚠️ 关注" if score['warning'] > 0 else "✅ 无")
                    
                    # 致命问题详情
                    all_issues = report["program_issues"] + report["strategy_issues"]
                    critical_issues = [i for i in all_issues if "CRITICAL" in i["severity"]]
                    warning_issues = [i for i in all_issues if "WARNING" in i["severity"]]
                    info_issues = [i for i in all_issues if "INFO" in i["severity"]]
                    
                    # 致命问题
                    if critical_issues:
                        st.markdown("#### 🔴 致命问题 (必须修复)")
                        for issue in critical_issues:
                            with st.expander(f"⚠️ {issue['title']}", expanded=True):
                                st.markdown(f"**位置**: {issue['location']}")
                                st.markdown(f"**描述**: {issue['description']}")
                                st.markdown(f"**后果**: {issue['consequence']}")
                                st.markdown("**修复方案**:")
                                st.code(issue["fix_diff"], language="diff")
                                st.markdown(f"**极限推演**: {issue['extreme_scenario']}")
                    
                    # 警告问题
                    if warning_issues:
                        st.markdown("#### 🟡 警告问题 (建议优化)")
                        for issue in warning_issues:
                            with st.expander(f"⚡ {issue['title']}"):
                                st.markdown(f"**位置**: {issue['location']}")
                                st.markdown(f"**描述**: {issue['description']}")
                                st.markdown("**修复方案**:")
                                st.code(issue["fix_diff"], language="diff")
                    
                    # 提示信息
                    if info_issues:
                        st.markdown("#### 🔵 优化建议")
                        for issue in info_issues:
                            with st.expander(f"💡 {issue['title']}"):
                                st.markdown(f"**描述**: {issue['description']}")
                                st.markdown("**建议**:")
                                st.code(issue["fix_diff"], language="diff")
                    
                    # 综合建议
                    if report["recommendations"]:
                        st.markdown("---")
                        st.markdown("#### 🎯 综合建议")
                        for rec in report["recommendations"]:
                            st.markdown(f"- {rec}")
                    
                    if not all_issues:
                        st.success("✅ 未发现逻辑问题！策略通过审查。")
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"审查失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        elif run_audit and not strategy_code:
            st.warning("请先输入策略代码")


# ═══════════════════════════════════════════
# 页面: AI预测 (G-Prophet集成)
# ═══════════════════════════════════════════
def page_ai_predict():
    """AI预测页面 - 基于G-Prophet API"""
    st.title("🔮 AI 预测分析")
    st.markdown("基于 **G-Prophet** AI量化平台，提供蒙特卡洛模拟、LSTM、Transformer等多种算法的股票预测")
    
    # 检查API Key
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GPROPHET_API_KEY", "")
    
    if not api_key:
        st.markdown("""
        ### 🔑 配置 G-Prophet API Key
        
        G-Prophet 提供 AI 驱动的股票预测与市场分析，支持以下功能：
        
        | 功能 | 说明 | 点数消耗 |
        |------|------|---------|
        | **AI价格预测** | 蒙特卡洛/LSTM/Transformer多算法预测 | 10-20点 |
        | **多算法对比** | 多算法交叉验证预测结果 | 40-80点 |
        | **技术分析** | RSI/MACD/布林带/KDJ信号 | 5点 |
        | **AI股票分析** | 单股票深度分析报告 | 58点 |
        | **5维深度分析** | 技术+基本面+资金+情绪+宏观 | 150点 |
        | **市场情绪** | 恐惧贪婪指数/市场概览 | 5点 |
        
        **如何获取 API Key:**
        1. 访问 [G-Prophet](https://www.gprophet.com) 注册账号
        2. 前往 设置 → API Keys 创建密钥
        3. 在本项目的 `.env` 文件中添加:
        ```
        GPROPHET_API_KEY=gp_sk_你的密钥
        ```
        
        > 💡 **免费体验**: 每日签到可得30积分，注册即可使用核心预测功能
        > 
        > 📖 **G-Prophet方法论**: 基于蒙特卡洛模拟的市场状态识别系统，从价格预测到概率建模
        """)
        return
    
    # API Key 已配置
    try:
        from data.gprophet import GProphetClient, MARKETS, ALGORITHMS, TECHNICAL_INDICATORS, POINTS_COST
        client = GProphetClient(api_key)
        
        # 查询余额
        balance = client.get_balance()
        if balance and balance.get("success"):
            bd = balance["data"]
            available = bd.get("available_points", 0)
            daily_used = bd.get("daily_used", 0)
            daily_quota = bd.get("daily_quota", 0)
            
            bal_col1, bal_col2, bal_col3 = st.columns(3)
            with bal_col1:
                st.metric("💎 可用点数", f"{available}")
            with bal_col2:
                st.metric("📊 今日已用", f"{daily_used}")
            with bal_col3:
                quota_pct = (daily_used / daily_quota * 100) if daily_quota > 0 else 0
                st.metric("📈 日配额", f"{quota_pct:.0f}%")
            st.markdown("---")
    
    except Exception as e:
        st.error(f"G-Prophet API 连接失败: {e}")
        st.info("请检查 API Key 是否正确，以及网络是否可以访问 gprophet.com")
        return
    
    # Tab 页面
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🤖 AI预测", "⚡ 多算法对比", 
        "📊 技术分析", "🧠 AI报告", "🌐 市场情绪"
    ])
    
    # Tab 1: AI 预测
    with tab1:
        st.markdown("### 🤖 AI 价格预测")
        st.caption("基于蒙特卡洛模拟/LSTM/Transformer等算法，预测股票未来价格走势")
        
        pred_col1, pred_col2 = st.columns([1, 2])
        with pred_col1:
            pred_symbol = st.text_input("股票代码", value="600519", key="pred_symbol",
                                        help="A股直接输入代码，美股输入如AAPL")
            pred_market = st.selectbox("市场", list(MARKETS.keys()), 
                                       format_func=lambda x: MARKETS[x], key="pred_market")
            pred_days = st.slider("预测天数", 1, 30, 7, key="pred_days")
            pred_algo = st.selectbox("算法", ALGORITHMS, key="pred_algo")
            
            if st.button("🔮 开始预测", type="primary", use_container_width=True):
                with st.spinner(f"正在用 {pred_algo} 预测 {pred_symbol} 未来{pred_days}天走势..."):
                    result = client.predict(pred_symbol, pred_market, pred_days, pred_algo)
                    
                    if result:
                        # 显示预测结果
                        dir_emoji = "🟢" if result.direction == "up" else "🔴" if result.direction == "down" else "🟡"
                        dir_text = "看涨" if result.direction == "up" else "看跌" if result.direction == "down" else "中性"
                        
                        st.markdown(f"### {dir_emoji} {result.name or result.symbol} - {dir_text}")
                        
                        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                        with kpi1:
                            st.metric("当前价格", f"${result.current_price:.2f}" if pred_market != "CN" else f"¥{result.current_price:.2f}")
                        with kpi2:
                            st.metric("预测价格", f"${result.predicted_price:.2f}" if pred_market != "CN" else f"¥{result.predicted_price:.2f}",
                                     delta=f"{result.change_percent:+.2f}%")
                        with kpi3:
                            conf_color = "🟢" if result.confidence > 0.7 else "🟡" if result.confidence > 0.5 else "🔴"
                            st.metric("置信度", f"{conf_color} {result.confidence:.0%}")
                        with kpi4:
                            st.metric("预测算法", result.algorithm)
                        
                        # 数据质量
                        if result.data_quality:
                            with st.expander("📋 数据质量详情"):
                                st.json(result.data_quality)
                    else:
                        st.error("预测失败，请检查股票代码和市场是否正确")
        
        with pred_col2:
            st.markdown("#### 📖 预测原理")
            st.markdown("""
            **G-Prophet 预测方法论:**
            
            1. **市场状态建模** — 将市场视为状态向量 `S = (T, V, U, M)`
               - T: 趋势结构（方向惯性）
               - V: 波动率水平（价格波动区间）
               - U: 不确定性分布（未来路径概率）
               - M: 市场结构（路径依赖）
            
            2. **蒙特卡洛路径生成** — 基于状态向量生成大量条件化价格路径
            
            3. **概率预测** — 输出预测区间而非单一点预测
            
            > 核心思想: "价格是市场状态的结果，决策应基于状态匹配"
            """)
            
            st.markdown("#### 💰 点数消耗")
            st.markdown(f"""
            | 市场 | 每次预测点数 |
            |------|-------------|
            | A股 (CN) | {POINTS_COST['predict_cn']} 点 |
            | 港股 (HK) | {POINTS_COST['predict_hk']} 点 |
            | 美股 (US) | {POINTS_COST['predict_us']} 点 |
            | 加密货币 | {POINTS_COST['predict_crypto']} 点 |
            """)
    
    # Tab 2: 多算法对比
    with tab2:
        st.markdown("### ⚡ 多算法对比预测")
        st.caption("多个AI算法同时预测，交叉验证提高可靠性")
        
        cmp_col1, cmp_col2 = st.columns([1, 2])
        with cmp_col1:
            cmp_symbol = st.text_input("股票代码", value="600519", key="cmp_symbol")
            cmp_market = st.selectbox("市场", list(MARKETS.keys()),
                                      format_func=lambda x: MARKETS[x], key="cmp_market")
            cmp_days = st.slider("预测天数", 1, 30, 5, key="cmp_days")
            
            cmp_algos = st.multiselect(
                "选择算法",
                [a for a in ALGORITHMS if a != "auto"],
                default=["gprophet2026v1", "lstm", "transformer", "ensemble"],
                key="cmp_algos"
            )
            
            if st.button("⚡ 开始对比", type="primary", use_container_width=True):
                if len(cmp_algos) < 2:
                    st.warning("请至少选择2个算法进行对比")
                else:
                    with st.spinner(f"正在用 {len(cmp_algos)} 个算法对比预测..."):
                        result = client.predict_compare(cmp_symbol, cmp_market, cmp_days, cmp_algos)
                        
                        if result:
                            # 共识结果
                            consensus_emoji = "🟢" if result.consensus_direction == "up" else "🔴" if result.consensus_direction == "down" else "🟡"
                            st.markdown(f"### {consensus_emoji} {result.name or result.symbol} — 共识: {result.consensus_direction}")
                            
                            st.metric("最优算法", result.best_algorithm)
                            st.metric("平均预测价", f"¥{result.average_predicted_price:.2f}" if cmp_market == "CN" else f"${result.average_predicted_price:.2f}")
                            
                            # 各算法结果表格
                            import pandas as pd
                            rows = []
                            for r in result.results:
                                rows.append({
                                    "算法": r.get("algorithm", ""),
                                    "预测价格": r.get("predicted_price", 0),
                                    "涨跌幅": f"{r.get('change_percent', 0):+.2f}%",
                                    "方向": r.get("direction", ""),
                                    "置信度": f"{r.get('confidence', 0):.0%}",
                                    "状态": "✅" if r.get("success") else "❌",
                                })
                            
                            if rows:
                                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                        else:
                            st.error("对比预测失败")
        
        with cmp_col2:
            st.markdown("#### 📊 对比分析说明")
            st.markdown("""
            **多算法交叉验证的价值:**
            
            - **降低单一模型偏差**: 每种算法有自己的盲区，多算法交叉可互相弥补
            - **共识信号更可靠**: 当多个算法一致看涨/看跌时，信号准确率更高
            - **发现分歧机会**: 算法间的分歧可能暗示市场不确定性
            
            **算法说明:**
            - **gprophet2026v1**: G-Prophet自研，蒙特卡洛+状态建模
            - **LSTM**: 长短期记忆网络，擅长时序依赖捕捉
            - **Transformer**: 注意力机制，擅长长程依赖
            - **Ensemble**: 集成模型，多模型投票
            - **Random Forest**: 随机森林，稳健性强
            """)
    
    # Tab 3: 技术分析
    with tab3:
        st.markdown("### 📊 AI 技术分析")
        st.caption("自动计算技术指标并生成交易信号")
        
        tech_col1, tech_col2 = st.columns([1, 2])
        with tech_col1:
            tech_symbol = st.text_input("股票代码", value="600519", key="tech_symbol")
            tech_market = st.selectbox("市场", list(MARKETS.keys()),
                                       format_func=lambda x: MARKETS[x], key="tech_market")
            
            tech_indicators = st.multiselect(
                "技术指标",
                TECHNICAL_INDICATORS,
                default=["rsi", "macd", "bollinger", "kdj"],
                key="tech_indicators"
            )
            
            if st.button("📊 技术分析", type="primary", use_container_width=True):
                with st.spinner("正在分析技术指标..."):
                    result = client.technical_analyze(tech_symbol, tech_market, tech_indicators)
                    
                    if result:
                        signal_emoji = "🟢" if result.overall_signal == "bullish" else "🔴" if result.overall_signal == "bearish" else "🟡"
                        signal_text = "看涨" if result.overall_signal == "bullish" else "看跌" if result.overall_signal == "bearish" else "中性"
                        
                        st.markdown(f"### {signal_emoji} {result.symbol} — {signal_text}")
                        st.metric("信号强度", f"{result.signal_strength:.0%}")
                        
                        # 指标详情
                        for name, value in result.indicators.items():
                            with st.expander(f"📋 {name.upper()}"):
                                st.json(value)
                        
                        # 信号列表
                        if result.signals:
                            st.markdown("**交易信号:**")
                            for sig in result.signals:
                                emoji = "🟢" if sig.get("type") == "bullish" else "🔴"
                                st.markdown(f"- {emoji} {sig.get('indicator', '')}: {sig.get('type', '')}")
                    else:
                        st.error("技术分析失败")
        
        with tech_col2:
            st.markdown("#### 📖 技术指标说明")
            st.markdown("""
            | 指标 | 类型 | 用途 |
            |------|------|------|
            | **RSI** | 动量 | 超买超卖判断 (>70超买, <30超卖) |
            | **MACD** | 趋势 | 趋势方向+动量 (金叉/死叉) |
            | **布林带** | 波动率 | 价格区间+突破信号 |
            | **KDJ** | 动量 | 随机振荡，短线交易信号 |
            | **SMA** | 趋势 | 简单移动平均线 |
            | **EMA** | 趋势 | 指数移动平均线 (更灵敏) |
            """)
    
    # Tab 4: AI 报告
    with tab4:
        st.markdown("### 🧠 AI 深度分析报告")
        st.caption("多智能体协作，从5个维度全面评估股票")
        
        report_type = st.radio("分析类型", ["📋 单股票分析 (58点)", "🔬 5维深度分析 (150点)"], 
                               horizontal=True, key="report_type")
        is_comprehensive = "5维" in report_type
        
        rpt_col1, rpt_col2 = st.columns([1, 2])
        with rpt_col1:
            rpt_symbol = st.text_input("股票代码", value="600519", key="rpt_symbol")
            rpt_market = st.selectbox("市场", list(MARKETS.keys()),
                                      format_func=lambda x: MARKETS[x], key="rpt_market")
            
            if st.button("🧠 生成分析报告", type="primary", use_container_width=True):
                with st.spinner("AI智能体正在分析中，请稍候..." if not is_comprehensive 
                                else "5维深度分析中，多智能体协作中..."):
                    
                    progress = st.progress(0, text="正在提交分析任务...")
                    
                    if is_comprehensive:
                        result = client.analyze_comprehensive(rpt_symbol, rpt_market)
                    else:
                        result = client.analyze_stock(rpt_symbol, rpt_market)
                    
                    progress.progress(50, text="分析完成，正在生成报告...")
                    
                    if result:
                        progress.progress(100, text="✅ 报告生成完成!")
                        
                        # 显示报告
                        rating_map = {
                            "bullish": ("🟢 看涨", "green"),
                            "bearish": ("🔴 看跌", "red"),
                            "neutral": ("🟡 中性", "yellow"),
                            "cautious": ("🟠 谨慎", "orange"),
                        }
                        rating_text, rating_color = rating_map.get(result.overall_rating, ("⚪ 未知", "gray"))
                        
                        st.markdown(f"### {rating_text} — 置信度 {result.confidence:.0%}")
                        st.metric("风险等级", result.risk_level)
                        st.markdown(f"**建议**: {result.recommendation}")
                        
                        # 各维度分析
                        if result.agents:
                            st.markdown("---")
                            agent_names = {
                                "technical": "📊 技术面",
                                "fundamental": "📄 基本面",
                                "capital_flow": "💰 资金流向",
                                "sentiment": "📰 市场情绪",
                                "macro": "🌍 宏观环境",
                            }
                            
                            agent_cols = st.columns(len(result.agents))
                            for i, (key, value) in enumerate(result.agents.items()):
                                with agent_cols[i]:
                                    name = agent_names.get(key, key)
                                    agent_rating = value.get("rating", "")
                                    agent_conf = value.get("confidence", 0)
                                    rating_emoji = "🟢" if agent_rating == "bullish" else "🔴" if agent_rating == "bearish" else "🟡"
                                    
                                    st.markdown(f"**{name}**")
                                    st.markdown(f"{rating_emoji} {agent_rating}")
                                    st.markdown(f"置信度: {agent_conf:.0%}")
                    else:
                        progress.empty()
                        st.error("分析报告生成失败，请检查余额是否充足")
        
        with rpt_col2:
            st.markdown("#### 📖 分析维度说明")
            if is_comprehensive:
                st.markdown("""
                **5维深度分析** — 模拟专业投研机构的分析流程:
                
                1. 📊 **技术面智能体** — K线形态、技术指标、趋势分析
                2. 📄 **基本面智能体** — 财务数据、行业地位、估值水平
                3. 💰 **资金流向智能体** — 主力资金、北向资金、龙虎榜
                4. 📰 **市场情绪智能体** — 社交媒体、新闻舆情、市场氛围
                5. 🌍 **宏观环境智能体** — 宏观经济、政策导向、行业周期
                
                各智能体独立分析 → 交叉验证 → 消除偏见 → 形成共识建议
                """)
            else:
                st.markdown("""
                **单股票分析** — 基础AI分析:
                
                - 自动获取最新市场数据
                - 多维度快速评估
                - 给出交易建议和风险提示
                
                > 如需更深入的分析，推荐使用 5维深度分析
                """)
    
    # Tab 5: 市场情绪
    with tab5:
        st.markdown("### 🌐 市场情绪")
        
        sent_col1, sent_col2 = st.columns(2)
        with sent_col1:
            st.markdown("#### 😱 恐惧与贪婪指数 (加密货币)")
            
            if st.button("🔄 获取最新指数", use_container_width=True):
                result = client.get_fear_greed()
                if result and result.get("success"):
                    d = result["data"]
                    value = d.get("value", 50)
                    classification = d.get("classification", "Neutral")
                    prev_value = d.get("previous_value", 50)
                    change = d.get("change", 0)
                    
                    # 可视化仪表
                    fg_color = "#22c55e" if value > 60 else "#eab308" if value > 40 else "#ef4444"
                    st.markdown(f"""
                    <div style="text-align:center; padding: 20px;">
                        <div style="font-size: 48px; font-weight: bold; color: {fg_color};">{value}</div>
                        <div style="font-size: 20px; color: {fg_color};">{classification}</div>
                        <div style="margin-top: 10px; color: #888;">
                            前值: {prev_value} | 变化: {'+' if change > 0 else ''}{change}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.progress(value / 100)
                    
                    # 刻度说明
                    st.markdown("""
                    | 区间 | 含义 |
                    |------|------|
                    | 0-25 | 😱 极度恐惧 |
                    | 25-45 | 😟 恐惧 |
                    | 45-55 | 😐 中性 |
                    | 55-75 | 😊 贪婪 |
                    | 75-100 | 🤑 极度贪婪 |
                    """)
                else:
                    st.error("获取恐惧贪婪指数失败")
        
        with sent_col2:
            st.markdown("#### 📊 市场概览")
            
            overview_market = st.selectbox("市场", ["CN", "US"], 
                                           format_func=lambda x: "A股" if x == "CN" else "美股",
                                           key="overview_market")
            
            if st.button("🔄 获取市场概览", use_container_width=True, key="btn_overview"):
                result = client.get_market_overview(overview_market)
                if result and result.get("success"):
                    d = result["data"]
                    st.json(d)
                else:
                    st.error("获取市场概览失败")



def page_kline():
    st.title("📉 K线分析")

    # 股票选择
    col1, col2 = st.columns([1, 3])
    with col1:
        stock_options = {
            "600519.SH": "贵州茅台",
            "000858.SZ": "五粮液",
            "601318.SH": "中国平安",
            "000001.SZ": "平安银行",
            "510300.SH": "沪深300ETF",
            "159915.SZ": "创业板ETF",
            "sh.000001": "上证指数",
            "sz.399001": "深证成指",
        }
        sel = st.selectbox("选择标的", list(stock_options.keys()), format_func=lambda x: stock_options[x])
        period = st.selectbox("周期", ["daily", "weekly"], index=0)
        days = st.slider("天数", 30, 500, 120)

    # 获取数据
    try:
        import baostock as bs
        bs.login()
        end_d = datetime.now().strftime("%Y%m%d")
        start_d = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
        # 转换代码格式
        code = sel
        if "." in code and not code.startswith("sh.") and not code.startswith("sz."):
            parts = code.split(".")
            code = f"{'sh' if parts[1]=='SH' else 'sz'}.{parts[0]}"

        rs = bs.query_history_k_data_plus(code, "date,open,high,low,close,volume,amount",
            start_date=start_d, end_date=end_d, frequency="d", adjustflag="2")
        rows = []
        if rs is None:
            st.error(f"获取K线数据失败，请检查股票代码或网络连接")
            bs.logout()
            return
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        bs.logout()

        if not rows:
            st.info("暂无数据")
            return

        df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume","amount"])
        for c in ["open","high","low","close","volume","amount"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df = df.tail(days).reset_index(drop=True)

        # 技术指标
        df["MA5"] = df["close"].rolling(5).mean()
        df["MA20"] = df["close"].rolling(20).mean()
        df["MA60"] = df["close"].rolling(60).mean()
        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_val = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs_val))
        # MACD
        ema12 = df["close"].ewm(span=12).mean()
        ema26 = df["close"].ewm(span=26).mean()
        df["MACD"] = ema12 - ema26
        df["Signal"] = df["MACD"].ewm(span=9).mean()
        df["Hist"] = df["MACD"] - df["Signal"]

        # ── K线图 ──
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.15, 0.15, 0.15],
            vertical_spacing=0.02,
            subplot_titles=[f"{stock_options.get(sel, sel)} K线图", "成交量", "RSI(14)", "MACD"],
        )

        # K线
        fig.add_trace(go.Candlestick(
            x=df["date"], open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            increasing_line_color="#10b981", increasing_fillcolor="#10b981",
            decreasing_line_color="#ef4444", decreasing_fillcolor="#ef4444",
            name="K线",
        ), row=1, col=1)

        # 均线
        for ma, color in [("MA5","#f59e0b"),("MA20","#3b82f6"),("MA60","#8b5cf6")]:
            fig.add_trace(go.Scatter(x=df["date"], y=df[ma], name=ma,
                line=dict(color=color, width=1.5)), row=1, col=1)

        # 成交量
        colors_vol = ["#10b981" if c >= o else "#ef4444" for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df["date"], y=df["volume"], marker_color=colors_vol,
            opacity=0.7, name="成交量", showlegend=False), row=2, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=df["date"], y=df["RSI"], name="RSI(14)",
            line=dict(color="#8b5cf6", width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", opacity=0.5, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#10b981", opacity=0.5, row=3, col=1)

        # MACD
        fig.add_trace(go.Bar(x=df["date"], y=df["Hist"], name="MACD柱",
            marker_color=["#10b981" if v >= 0 else "#ef4444" for v in df["Hist"]],
            opacity=0.7), row=4, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["MACD"], name="MACD",
            line=dict(color="#3b82f6", width=1.5)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["Signal"], name="Signal",
            line=dict(color="#f59e0b", width=1.5)), row=4, col=1)

        fig.update_layout(
            template="plotly_dark", height=750,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0.5, font=dict(size=10)),
            margin=dict(l=40, r=20, t=30, b=30),
        )
        for i in range(1, 5):
            fig.update_xaxes(gridcolor="#1e293b", row=i, col=1)
            fig.update_yaxes(gridcolor="#1e293b", row=i, col=1)

        st.plotly_chart(fig, use_container_width=True)

        # ── 关键数据 ──
        latest = df.iloc[-1]
        chg = (latest["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100 if len(df) > 1 else 0
        st.markdown('<div class="section-title">📊 最新行情</div>', unsafe_allow_html=True)
        kpi = f'''
        <div class="kpi-container">
            {render_kpi_card("最新价", f"<b>{latest['close']:.2f}</b>", stock_options.get(sel,""), "green" if chg>=0 else "red")}
            {render_kpi_card("涨跌幅", f"<b>{chg:+.2f}%</b>", f"成交额:{latest['amount']/1e8:.1f}亿", "green" if chg>=0 else "red")}
            {render_kpi_card("RSI(14)", f"<b>{latest['RSI']:.1f}</b>", "超买>70 超卖<30", "blue")}
            {render_kpi_card("MACD", f"<b>{latest['MACD']:.3f}</b>", f"信号线:{latest['Signal']:.3f}", "purple")}
        </div>
        '''
        st.markdown(kpi, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"K线数据获取失败: {e}")


# ═══════════════════════════════════════════
# 页面4: 策略对比（升级版）
# ═══════════════════════════════════════════
def page_compare():
    st.title("⚔️ 策略对比分析")
    db = st.session_state.db
    try:
        all_r = db.get_latest_results()
    except:
        st.error("数据库错误"); return
    if all_r.empty:
        st.info("暂无数据"); return
    results = all_r.to_dict("records")
    names = sorted(set(r.get("strategy_name", "") for r in results))
    selected = st.multiselect("选择策略进行对比", names, default=names[:3])
    if not selected:
        st.warning("请选择策略"); return
    filtered = [r for r in results if r.get("strategy_name", "") in selected]

    # ── 对比表 ──
    rows = []
    for r in filtered:
        rows.append({
            "策略": r.get("strategy_name", ""),
            "年化收益": fmt_pct(r.get("annual_return", 0)),
            "最大回撤": fmt_pct(abs(r.get("max_drawdown", 0))),
            "夏普比率": fmt_num(r.get("sharpe_ratio", 0)),
            "Sortino": fmt_num(r.get("sortino_ratio", 0)) if r.get("sortino_ratio") else "-",
            "Calmar": fmt_num(r.get("calmar_ratio", 0)) if r.get("calmar_ratio") else "-",
            "胜率": fmt_pct(r.get("win_rate", 0)),
            "盈亏比": fmt_num(r.get("profit_loss_ratio", 0)),
            "波动率": fmt_pct(r.get("volatility", 0)),
            "Beta": fmt_num(r.get("beta", 0)) if r.get("beta") else "-",
        })
    st.markdown(f'<div class="chart-container" style="overflow-x:auto;padding:0;">'
                f'{pd.DataFrame(rows).to_html(escape=False, index=False)}</div>',
                unsafe_allow_html=True)

    # ── 雷达图 ──
    st.markdown('<div class="section-title">🕸️ 综合能力雷达图</div>', unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        categories = ["年化收益", "夏普比率", "胜率", "盈亏比", "低回撤", "稳定性"]
        colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]
        fig = go.Figure()
        for idx, r in enumerate(filtered):
            vals = [
                min(10, max(0, r.get("annual_return", 0) * 100)),
                min(10, max(0, r.get("sharpe_ratio", 0) * 5)),
                r.get("win_rate", 0) * 10,
                min(10, max(0, r.get("profit_loss_ratio", 0) * 5)),
                min(10, max(0, (1 - abs(r.get("max_drawdown", 0))) * 10)),
                min(10, max(0, (1 - r.get("volatility", 0)) * 10)),
            ]
            fig.add_trace(go.Scatterpolar(
                r=vals + [vals[0]], theta=categories + [categories[0]],
                fill="toself", name=r.get("strategy_name", ""),
                line_color=colors[idx % len(colors)], opacity=0.4,
            ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10],
                gridcolor="#1e293b", tickfont=dict(size=9))),
            showlegend=True, template="plotly_dark", height=420,
            paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#94a3b8"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1),
            margin=dict(l=60, r=60, t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)
    except:
        pass

    # ── 净值叠加 ──
    st.markdown('<div class="section-title">📈 净值曲线叠加</div>', unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        fig2 = go.Figure()
        for idx, r in enumerate(filtered):
            daily = db.get_daily_values(r.get("strategy_name", ""))
            if not daily.empty:
                first = daily["portfolio_value"].iloc[0]
                norm = daily["portfolio_value"] / first if first > 0 else daily["portfolio_value"]
                fig2.add_trace(go.Scatter(x=daily.index, y=norm, name=r.get("strategy_name", ""),
                    line=dict(color=colors[idx % len(colors)], width=2)))
        fig2.update_layout(template="plotly_dark", height=380, yaxis_title="归一化净值",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            legend=dict(orientation="h", y=1.02), margin=dict(l=40, r=20, t=20, b=30),
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
        st.plotly_chart(fig2, use_container_width=True)
    except:
        pass

    # ── 回撤对比 ──
    st.markdown('<div class="section-title">📉 回撤对比</div>', unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        fig3 = go.Figure()
        for idx, r in enumerate(filtered):
            daily = db.get_daily_values(r.get("strategy_name", ""))
            if not daily.empty and "drawdown" in daily.columns:
                fig3.add_trace(go.Scatter(x=daily.index, y=daily["drawdown"] * 100,
                    name=r.get("strategy_name", ""), fill="tozeroy",
                    line=dict(color=colors[idx % len(colors)], width=1)))
        fig3.update_layout(template="plotly_dark", height=300, yaxis_title="回撤(%)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            margin=dict(l=40, r=20, t=10, b=30),
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
        st.plotly_chart(fig3, use_container_width=True)
    except:
        pass


# ═══════════════════════════════════════════
# 页面5: 策略详情（升级版）
# ═══════════════════════════════════════════
def page_detail():
    st.title("📈 策略详情分析")
    db = st.session_state.db
    try:
        all_r = db.get_latest_results()
    except:
        st.error("数据库错误"); return
    if all_r.empty:
        st.info("暂无数据"); return
    results = all_r.to_dict("records")
    names = sorted(set(r.get("strategy_name", "") for r in results))
    sel = st.selectbox("选择策略", names)
    r = next((x for x in results if x.get("strategy_name") == sel), None)
    if not r:
        return

    # ── KPI ──
    kpi = f'''
    <div class="kpi-container">
        {render_kpi_card("年化收益", f"<b>{fmt_pct(r.get('annual_return',0))}</b>", "复合年增长率", "green" if r.get("annual_return",0)>=0 else "red")}
        {render_kpi_card("最大回撤", f"<b>{fmt_pct(abs(r.get('max_drawdown',0)))}</b>", "峰值到谷底", "red")}
        {render_kpi_card("夏普比率", f"<b>{fmt_num(r.get('sharpe_ratio',0))}</b>", "风险调整收益", "blue")}
        {render_kpi_card("胜率", f"<b>{fmt_pct(r.get('win_rate',0))}</b>", "盈利交易占比", "purple")}
    </div>
    <div class="kpi-container">
        {render_kpi_card("Sortino", fmt_num(r.get("sortino_ratio",0)) if r.get("sortino_ratio") else "N/A", "下行风险调整", "blue")}
        {render_kpi_card("Calmar", fmt_num(r.get("calmar_ratio",0)) if r.get("calmar_ratio") else "N/A", "收益/回撤比", "green")}
        {render_kpi_card("盈亏比", f"<b>{fmt_num(r.get('profit_loss_ratio',0))}</b>", "平均盈利/亏损", "orange")}
        {render_kpi_card("总交易", f"<b>{r.get('total_trades',0)}</b>", "买入+卖出", "purple")}
    </div>
    '''
    st.markdown(kpi, unsafe_allow_html=True)

    # ── 图表 ──
    import plotly.graph_objects as go
    try:
        daily = db.get_daily_values(sel)
    except:
        daily = pd.DataFrame()

    if not daily.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-title">净值曲线</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily.index, y=daily["portfolio_value"], name="策略净值",
                line=dict(color="#10b981", width=2), fill="tozeroy",
                fillcolor="rgba(16,185,129,0.05)"))
            if "benchmark_value" in daily.columns:
                fig.add_trace(go.Scatter(x=daily.index, y=daily["benchmark_value"],
                    name="沪深300", line=dict(color="#475569", width=1.5, dash="dot")))
            fig.update_layout(template="plotly_dark", height=320,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#94a3b8"),
                margin=dict(l=40, r=20, t=10, b=30),
                xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="section-title">回撤曲线</div>', unsafe_allow_html=True)
            if "drawdown" in daily.columns:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=daily.index, y=daily["drawdown"] * 100,
                    fill="tozeroy", line=dict(color="#ef4444", width=1.5)))
                fig2.update_layout(template="plotly_dark", height=320, yaxis_title="回撤(%)",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter", color="#94a3b8"),
                    margin=dict(l=40, r=20, t=10, b=30),
                    xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
                st.plotly_chart(fig2, use_container_width=True)

        # 日收益率分布
        st.markdown('<div class="section-title">📊 日收益率分布</div>', unsafe_allow_html=True)
        rets = daily["portfolio_value"].pct_change().dropna()
        fig3 = go.Figure()
        fig3.add_trace(go.Histogram(x=rets * 100, nbinsx=50, marker_color="#3b82f6", opacity=0.8))
        fig3.add_vline(x=0, line_dash="dash", line_color="#ef4444", opacity=0.5)
        fig3.update_layout(template="plotly_dark", height=260, xaxis_title="日收益率(%)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            margin=dict(l=40, r=20, t=10, b=30),
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
        st.plotly_chart(fig3, use_container_width=True)

    # ── AI分析 ──
    st.markdown("---")
    if st.button("🤖 AI 深度分析此策略", type="primary"):
        with st.spinner("分析中..."):
            try:
                from core.ai_analyzer import AIAnalyzer
                analyzer = AIAnalyzer(st.session_state.get("ai_provider", "zhipu"))
                st.session_state["ai_detail"] = analyzer.analyze_strategy(r)
            except Exception as e:
                st.error(f"失败: {e}")
    if "ai_detail" in st.session_state:
        st.markdown('<div class="section-title">🤖 AI 分析报告</div>', unsafe_allow_html=True)
        st.markdown(st.session_state["ai_detail"])


# ═══════════════════════════════════════════
# 页面6: 交易明细（新增）
# ═══════════════════════════════════════════
def page_trades():
    st.title("📋 交易明细")
    db = st.session_state.db

    # 获取策略列表
    try:
        all_r = db.get_latest_results()
    except:
        st.error("数据库错误"); return
    if all_r.empty:
        st.info("暂无数据"); return

    results = all_r.to_dict("records")
    names = sorted(set(r.get("strategy_name", "") for r in results))
    sel = st.selectbox("选择策略", names)

    # 获取交易记录
    try:
        conn = db._get_conn()
        import sqlite3
        trades = pd.read_sql_query(
            "SELECT * FROM trade_records WHERE strategy_name=? ORDER BY entry_date DESC LIMIT 100",
            conn, params=(sel,)
        )
        if trades.empty:
            st.info("该策略暂无交易记录")
            return
        # 展示
        cols_to_show = [c for c in ["entry_date", "exit_date", "direction", "price", "size",
                        "pnl", "pnl_pct", "holding_days"] if c in trades.columns]
        if cols_to_show:
            col_names = {
                "entry_date": "买入日期", "exit_date": "卖出日期", "direction": "方向",
                "price": "价格", "size": "数量", "pnl": "盈亏", "pnl_pct": "收益率",
                "holding_days": "持有天数"
            }
            display_df = trades[cols_to_show].rename(columns=col_names)
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

        # 交易统计
        st.markdown('<div class="section-title">📊 交易统计</div>', unsafe_allow_html=True)
        if "pnl" in trades.columns:
            win_trades = len(trades[trades["pnl"] > 0])
            lose_trades = len(trades[trades["pnl"] <= 0])
            total_pnl = trades["pnl"].sum()
            avg_pnl = trades["pnl"].mean()
            max_win = trades["pnl"].max()
            max_loss = trades["pnl"].min()
            kpi = f'''
            <div class="kpi-container">
                {render_kpi_card("总交易", f"<b>{len(trades)}</b>", f"胜{win_trades} 负{lose_trades}", "blue")}
                {render_kpi_card("总盈亏", f"<b>{fmt_num(total_pnl)}</b>", "累计盈亏金额", "green" if total_pnl>=0 else "red")}
                {render_kpi_card("平均盈亏", f"<b>{fmt_num(avg_pnl)}</b>", "每笔平均", "blue")}
                {render_kpi_card("最大单笔盈利", f"<b>{fmt_num(max_win)}</b>", "最佳交易", "green")}
                {render_kpi_card("最大单笔亏损", f"<b>{fmt_num(max_loss)}</b>", "最差交易", "red")}
            </div>
            '''
            st.markdown(kpi, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"交易记录获取失败: {e}")


# ═══════════════════════════════════════════
# 页面7: 收益日历（新增）
# ═══════════════════════════════════════════
def page_calendar():
    st.title("🗓️ 收益日历")
    db = st.session_state.db

    try:
        all_r = db.get_latest_results()
    except:
        st.error("数据库错误"); return
    if all_r.empty:
        st.info("暂无数据"); return

    results = all_r.to_dict("records")
    names = sorted(set(r.get("strategy_name", "") for r in results))
    sel = st.selectbox("选择策略", names)

    try:
        daily = db.get_daily_values(sel)
        if daily.empty:
            st.info("暂无日净值数据"); return

        # 计算日收益率
        daily["date"] = daily.index
        daily["ret"] = daily["portfolio_value"].pct_change() * 100

        # ── 月度收益热力图 ──
        st.markdown('<div class="section-title">📅 月度收益热力图</div>', unsafe_allow_html=True)
        daily["year"] = daily.index.year
        daily["month"] = daily.index.month

        # 计算每月收益
        monthly = daily.groupby(["year", "month"])["ret"].sum().reset_index()
        monthly.columns = ["year", "month", "ret"]

        # 构建热力图
        import plotly.graph_objects as go
        years = sorted(monthly["year"].unique())
        months = list(range(1, 13))
        month_names = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]

        # 创建数据矩阵
        heatmap_data = []
        for y in years:
            row = []
            for m in months:
                val = monthly[(monthly["year"] == y) & (monthly["month"] == m)]["ret"]
                row.append(val.values[0] if len(val) > 0 else None)
            heatmap_data.append(row)

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data, x=month_names, y=[str(y) for y in years],
            colorscale=[[0,"#ef4444"],[0.5,"#1e293b"],[1,"#10b981"]],
            zmid=0, texttemplate="%{z:.1f}%", textfont=dict(size=11, color="#e2e8f0"),
            hovertemplate="%{y}年%{x}: %{z:.2f}%<extra></extra>",
        ))
        fig.update_layout(
            template="plotly_dark", height=max(300, len(years) * 50 + 100),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            xaxis=dict(side="top"), margin=dict(l=50, r=20, t=10, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── 年度收益统计 ──
        st.markdown('<div class="section-title">📊 年度收益统计</div>', unsafe_allow_html=True)
        yearly = daily.groupby("year")["ret"].agg(["sum", "mean", "std", "min", "max", "count"]).reset_index()
        yearly.columns = ["年份", "累计收益%", "日均%", "波动%", "最大单日%", "最小单日%", "交易日"]
        st.markdown(f'<div class="chart-container" style="overflow-x:auto;padding:0;">'
                    f'{yearly.to_html(escape=False, index=False, float_format=lambda x: f"{x:.2f}")}</div>',
                    unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"收益日历生成失败: {e}")


# ═══════════════════════════════════════════
# 页面8: AI 分析（增强版）
# ═══════════════════════════════════════════
def page_ai():
    st.title("🤖 AI 智能分析")
    tab1, tab2, tab3 = st.tabs(["📊 策略分析", "🌍 市场解读", "🧬 自学习进化"])
    db = st.session_state.db
    try:
        all_r = db.get_latest_results()
    except:
        all_r = pd.DataFrame()
    results = all_r.to_dict("records") if not all_r.empty else []

    with tab1:
        if results:
            names = sorted(set(r.get("strategy_name", "") for r in results))
            mode = st.radio("分析模式", ["单策略深度分析", "多策略对比分析"], horizontal=True)
            if mode == "单策略深度分析":
                sel = st.selectbox("选择策略", names)
                r = next((x for x in results if x.get("strategy_name") == sel), None)
                if r and st.button("🔬 开始AI分析", type="primary"):
                    with st.spinner("AI分析中..."):
                        try:
                            from core.ai_analyzer import AIAnalyzer
                            st.markdown(AIAnalyzer(st.session_state.get("ai_provider", "zhipu")).analyze_strategy(r))
                        except Exception as e:
                            st.error(f"失败: {e}")
            else:
                sel = st.multiselect("选择策略", names, default=names[:3])
                if sel and st.button("📊 开始对比分析", type="primary"):
                    with st.spinner("分析中..."):
                        try:
                            from core.ai_analyzer import AIAnalyzer
                            filtered = [x for x in results if x.get("strategy_name") in sel]
                            st.markdown(AIAnalyzer(st.session_state.get("ai_provider", "zhipu")).compare_strategies(filtered))
                        except Exception as e:
                            st.error(f"失败: {e}")
        else:
            st.info("暂无数据，请先运行回测")

    with tab2:
        if st.button("🌍 分析市场环境", type="primary"):
            with st.spinner("分析中..."):
                try:
                    from core.ai_analyzer import AIAnalyzer
                    st.markdown(AIAnalyzer(st.session_state.get("ai_provider", "zhipu")).market_analysis())
                except Exception as e:
                    st.error(f"失败: {e}")

        # 实时数据
        try:
            import baostock as bs
            lg = bs.login()
            end_d = datetime.now().strftime("%Y%m%d")
            start_d = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")
            indices = [("sh.000001", "上证"), ("sz.399006", "创业板")]
            for code, name in indices:
                rs = bs.query_history_k_data_plus(code, "date,close,volume",
                    start_date=start_d, end_date=end_d, frequency="d", adjustflag="3")
                rows = []
                if rs is None:
                    st.warning(f"获取{code}指数数据失败")
                else:
                    while rs.error_code == "0" and rs.next():
                        rows.append(rs.get_row_data())
                if rows:
                    df = pd.DataFrame(rows, columns=["date", "close", "volume"])
                    df["close"] = pd.to_numeric(df["close"])
                    latest = df.iloc[-1]["close"]
                    prev = df.iloc[-2]["close"] if len(df) > 1 else latest
                    chg = (latest - prev) / prev * 100
                    color = "green" if chg >= 0 else "red"
                    st.markdown(f'<div class="alert-box alert-{color}">'
                                f'<b>{name}</b>: {latest:.2f} ({chg:+.2f}%)</div>',
                                unsafe_allow_html=True)
            bs.logout()
        except Exception as e:
            st.warning(f"市场数据获取失败: {e}")

    with tab3:
        st.markdown("### 🧬 AI 自学习进化引擎")
        st.markdown('''
        <div class="glass-card">
            <p style="color:#94a3b8;font-size:14px;line-height:1.8;">
                AI引擎自动分析历史回测数据，识别以下模式：<br>
                🔍 <b>策略退化检测</b> — 识别近期表现下滑的策略<br>
                📊 <b>参数优化方向</b> — 建议参数调整区间<br>
                💡 <b>新策略建议</b> — 基于现有策略弱点推荐改进方向<br>
                ⚠️ <b>风险预警</b> — 发现潜在风险因子
            </p>
        </div>
        ''', unsafe_allow_html=True)
        if st.button("🔬 触发自学习", type="primary"):
            with st.spinner("学习中..."):
                try:
                    from core.ai_analyzer import AIAnalyzer
                    st.markdown(AIAnalyzer(st.session_state.get("ai_provider", "zhipu")).auto_learn(results))
                except Exception as e:
                    st.error(f"失败: {e}")


# ═══════════════════════════════════════════
# 页面9: 风险仪表盘（新增）
# ═══════════════════════════════════════════
def page_risk():
    st.title("⚠️ 风险仪表盘")
    db = st.session_state.db
    try:
        all_r = db.get_latest_results()
    except:
        st.error("数据库错误"); return
    if all_r.empty:
        st.info("暂无数据"); return

    results = all_r.to_dict("records")

    # ── 风险等级评估 ──
    risk_items = []
    for r in results:
        name = r.get("strategy_name", "")
        mdd = abs(r.get("max_drawdown", 0))
        sr = r.get("sharpe_ratio", 0)
        vol = r.get("volatility", 0)
        wr = r.get("win_rate", 0)
        ar = r.get("annual_return", 0)

        # 风险评分（0-100，越高越危险）
        risk_score = 0
        if mdd > 0.3: risk_score += 30
        elif mdd > 0.2: risk_score += 20
        elif mdd > 0.1: risk_score += 10
        if sr < 0.5: risk_score += 25
        elif sr < 1.0: risk_score += 15
        if vol > 0.3: risk_score += 20
        elif vol > 0.2: risk_score += 10
        if wr < 0.4: risk_score += 15
        elif wr < 0.5: risk_score += 8
        if ar < 0: risk_score += 10

        if risk_score >= 60: level, color = "高风险", "red"
        elif risk_score >= 35: level, color = "中风险", "orange"
        else: level, color = "低风险", "green"

        risk_items.append({
            "strategy": name, "risk_score": risk_score, "level": level, "color": color,
            "max_dd": mdd, "sharpe": sr, "volatility": vol, "win_rate": wr
        })

    # ── 风险概览KPI ──
    high_risk = [r for r in risk_items if r["level"] == "高风险"]
    mid_risk = [r for r in risk_items if r["level"] == "中风险"]
    low_risk = [r for r in risk_items if r["level"] == "低风险"]
    avg_risk = np.mean([r["risk_score"] for r in risk_items])

    kpi = f'''
    <div class="kpi-container">
        {render_kpi_card("高风险策略", f"<b>{len(high_risk)}</b>", "需要立即关注", "red")}
        {render_kpi_card("中风险策略", f"<b>{len(mid_risk)}</b>", "持续监控", "orange")}
        {render_kpi_card("低风险策略", f"<b>{len(low_risk)}</b>", "表现健康", "green")}
        {render_kpi_card("综合风险指数", f"<b>{avg_risk:.0f}</b>", "满分100", "red" if avg_risk>=50 else "orange" if avg_risk>=30 else "green")}
    </div>
    '''
    st.markdown(kpi, unsafe_allow_html=True)

    # ── 风险矩阵 ──
    st.markdown('<div class="section-title">🎯 风险-收益矩阵</div>', unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        for r in results:
            ar = r.get("annual_return", 0)
            mdd = abs(r.get("max_drawdown", 0))
            sr = r.get("sharpe_ratio", 0)
            vol = r.get("volatility", 0)
            size = 15 + (1 - vol) * 20
            color = "#10b981" if sr > 1.0 else ("#f59e0b" if sr > 0.5 else "#ef4444")
            fig.add_trace(go.Scatter(
                x=[mdd * 100], y=[ar * 100], name=r.get("strategy_name", ""),
                text=[f"波动率:{vol:.1%}<br>夏普:{sr:.2f}"],
                mode="markers+text", marker=dict(color=color, size=size, opacity=0.8,
                    line=dict(color="white", width=1)),
                textposition="top center", textfont=dict(size=10),
            ))
        # 安全区域
        fig.add_hrect(y0=-5, y1=5, x0=0, x1=10, fillcolor="rgba(16,185,129,0.05)",
            line=dict(color="rgba(16,185,129,0.2)", dash="dot"))
        fig.add_vrect(x0=0, x1=15, y0=5, line=dict(color="rgba(239,68,68,0.2)", dash="dot"))
        fig.update_layout(
            template="plotly_dark", height=400,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#94a3b8"),
            xaxis_title="最大回撤 (%)", yaxis_title="年化收益 (%)",
            margin=dict(l=50, r=20, t=10, b=40),
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
        )
        st.plotly_chart(fig, use_container_width=True)
    except:
        pass

    # ── 策略风险明细 ──
    st.markdown('<div class="section-title">📋 策略风险明细</div>', unsafe_allow_html=True)
    risk_rows = []
    for r in sorted(risk_items, key=lambda x: x["risk_score"], reverse=True):
        badge = f'<span class="badge badge-{r["color"]}">{r["level"]}</span>'
        risk_rows.append({
            "策略": f'<b>{r["strategy"]}</b>',
            "风险等级": badge,
            "风险分数": f'<span style="color:{"#f87171" if r["risk_score"]>=60 else "#fbbf24" if r["risk_score"]>=35 else "#34d399"};">{r["risk_score"]:.0f}/100</span>',
            "最大回撤": fmt_pct(r["max_dd"]),
            "夏普比率": fmt_num(r["sharpe"]),
            "波动率": fmt_pct(r["volatility"]),
            "胜率": fmt_pct(r["win_rate"]),
        })
    st.markdown(f'<div class="chart-container" style="overflow-x:auto;padding:0;">'
                f'{pd.DataFrame(risk_rows).to_html(escape=False, index=False)}</div>',
                unsafe_allow_html=True)

    # ── 常见陷阱提醒 ──
    st.markdown('<div class="section-title">📚 量化交易常见陷阱</div>', unsafe_allow_html=True)
    st.markdown('''
    <div class="glass-card" style="font-size:13px;color:#94a3b8;line-height:1.8;">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;">
            <div><span style="color:#ef4444;font-weight:600;">⚠️ 过拟合</span> — 过度优化参数，回测漂亮实盘亏损</div>
            <div><span style="color:#ef4444;font-weight:600;">⚠️ 未来函数</span> — 使用了回测时还不存在的数据</div>
            <div><span style="color:#ef4444;font-weight:600;">⚠️ 生存者偏差</span> — 只用当前存续股票做回测</div>
            <div><span style="color:#ef4444;font-weight:600;">⚠️ 滑点忽视</span> — 忽略手续费/滑点导致虚高收益</div>
            <div><span style="color:#ef4444;font-weight:600;">⚠️ 流动性风险</span> — 小盘股策略实盘无法完全成交</div>
            <div><span style="color:#ef4444;font-weight:600;">⚠️ 情绪化干预</span> — 实盘手动干预导致策略失效</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 页面10: 系统设置（升级版）
# ═══════════════════════════════════════════
def page_settings():
    st.title("⚙️ 系统设置")
    tab1, tab2, tab3 = st.tabs(["🔑 API配置", "📝 自定义策略", "📊 数据管理"])

    with tab1:
        st.markdown("### 🤖 AI 模型 API Key 配置")
        from config import AI_MODELS
        # 按tier分组展示
        tiers = {1: "🌐 无需注册 / 注册即用", 2: "📝 注册后免费额度", 3: "💰 付费/有限免费"}
        tier_names = {1: "Tier 1 — 免费无Key", 2: "Tier 2 — 注册免费Key", 3: "Tier 3 — 付费Key"}

        for tier in [1, 2, 3]:
            tier_models = {k: v for k, v in AI_MODELS.items() if v.get("tier") == tier}
            if not tier_models:
                continue

            with st.expander(f"{tier_names[tier]} ({len(tier_models)}个模型)", expanded=(tier <= 2)):
                for key, cfg in tier_models.items():
                    has_key = bool(cfg.get("api_key") or os.getenv(cfg["env_key"], ""))
                    status = "✅ 已配置" if has_key else "⚙️ 未配置"
                    st.markdown(f"**{cfg['name']}** — {cfg['desc']} — **{status}**  | 限额: `{cfg['rate_limit']}`")

                    new_key = st.text_input(
                        f"{cfg['name']}", value=cfg.get("api_key", ""),
                        key=f"key_{key}", type="password", label_visibility="collapsed"
                    )
                    if new_key and new_key != cfg.get("api_key", ""):
                        env_path = ROOT_DIR / ".env"
                        env_lines = []
                        if env_path.exists():
                            env_lines = env_path.read_text(encoding="utf-8").splitlines()
                        env_key = f"{key.upper()}_API_KEY"
                        found = False
                        for i, line in enumerate(env_lines):
                            if line.startswith(f"{env_key}="):
                                env_lines[i] = f"{env_key}={new_key}"
                                found = True
                                break
                        if not found:
                            env_lines.append(f"{env_key}={new_key}")
                        env_path.write_text("\n".join(env_lines), encoding="utf-8")
                        os.environ[env_key] = new_key
                        cfg["api_key"] = new_key
                        st.success(f"✅ {cfg['name']} API Key 已保存到.env文件")

                        # 自动添加到策略库
                        from strategy_library import STRATEGY_LIBRARY
                        st.rerun()

        st.markdown("---")
        st.markdown('''
        <div class="glass-card">
            <div style="color:#e2e8f0;font-weight:600;margin-bottom:12px;">🔑 免费 API Key 获取地址</div>
            <div style="color:#94a3b8;font-size:12px;line-height:2.2;">
                <b style="color:#10b981;">🌐 国际免费首选:</b><br>
                &nbsp;&nbsp;• <b>Groq</b> (Llama 3.3) — <a href="https://console.groq.com/keys" target="_blank" style="color:#3b82f6;">console.groq.com</a> — 免费无限制, 30秒注册<br>
                &nbsp;&nbsp;• <b>Cerebras</b> (Llama 3.3) — <a href="https://cloud.cerebras.ai/" target="_blank" style="color:#3b82f6;">cloud.cerebras.ai</a> — 免费无限制<br>
                &nbsp;&nbsp;• <b>Google Gemini</b> — <a href="https://aistudio.google.com/apikey" target="_blank" style="color:#3b82f6;">aistudio.google.com</a> — 免费额度<br>
                <b style="color:#f59e0b;">🇨🇳 国产免费首选:</b><br>
                &nbsp;&nbsp;• <b>智谱AI</b> (GLM-4-Flash) — <a href="https://open.bigmodel.cn/" target="_blank" style="color:#3b82f6;">open.bigmodel.cn</a> — 免费额度, 25 RPM<br>
                &nbsp;&nbsp;• <b>DeepSeek V3</b> — <a href="https://platform.deepseek.com/" target="_blank" style="color:#3b82f6;">platform.deepseek.com</a> — 新用户500万token<br>
                &nbsp;&nbsp;• <b>通义千问</b> (Qwen) — <a href="https://dashscope.console.aliyun.com/" target="_blank" style="color:#3b82f6;">dashscope.aliyun.com</a> — 100万token/月免费<br>
                &nbsp;&nbsp;• <b>Kimi/Moonshot</b> — <a href="https://platform.moonshot.cn/" target="_blank" style="color:#3b82f6;">platform.moonshot.cn</a> — 免费额度<br>
                &nbsp;&nbsp;• <b>SiliconFlow</b> (聚合) — <a href="https://cloud.siliconflow.cn/" target="_blank" style="color:#3b82f6;">cloud.siliconflow.cn</a> — 14元/天免费<br>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    with tab2:
        st.markdown("### 📤 上传自定义策略")
        st.markdown('<div class="alert-box alert-info">支持上传 .py 策略文件（Backtrader格式），上传后直接回测！</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("选择.py文件（支持拖拽）", type=["py"])
        if uploaded:
            code = uploaded.read().decode("utf-8")
            st.markdown(f"**📄 已上传:** `{uploaded.name}` （{len(code)} 字符）")
            st.code(code[:500] + "..." if len(code) > 500 else code, language="python")

            # 保存
            (ROOT_DIR / "uploads").mkdir(parents=True, exist_ok=True)
            save_path = ROOT_DIR / "uploads" / uploaded.name
            with open(save_path, "wb") as f:
                f.write(uploaded.getvalue())

            # 自动检测策略
            import re
            bt_classes = re.findall(r"class\s+(\w+)\(bt\.Strategy\)", code)
            bt_classes_also = re.findall(r"class\s+(\w+)\(bt\.\w+Strategy\)", code)
            all_classes = list(set(bt_classes + bt_classes_also))

            if all_classes:
                st.markdown(f"**✅ 检测到 Backtrader 策略类:** `{', '.join(all_classes)}`")
                st.success("策略格式正确，可以回测！")

                # 立即回测
                st.markdown("#### ⚡ 立即回测这个策略")
                s_col, e_col = st.columns(2)
                with s_col:
                    up_stock = st.selectbox("回测标的", [
                        "000001.SZ", "000002.SZ", "600000.SH", "600519.SH",
                        "000858.SZ", "601318.SH", "000300.SH"
                    ], key="up_stock", format_func=lambda x: f"{x} {'平安' if x=='601318.SH' else '茅台' if x=='600519.SH' else '沪深300' if x=='000300.SH' else '万科' if x=='000002.SZ' else '浦发' if x=='600000.SH' else '五粮液' if x=='000858.SZ' else '股票'}")
                with e_col:
                    up_start = st.date_input("开始", value=datetime(2015,1,1), key="up_start")
                    up_end = st.date_input("结束", value=datetime(2024,12,31), key="up_end")

                if st.button("🚀 **立即回测**", type="primary", use_container_width=True):
                    with st.spinner("回测中，请稍候..."):
                        try:
                            from core.strategy_arena import safe_backtest_strategy
                            success, results, equity_df = safe_backtest_strategy(
                                code=code,
                                stock=up_stock,
                                start_date=up_start.strftime("%Y-%m-%d"),
                                end_date=up_end.strftime("%Y-%m-%d"),
                                initial_cash=100000.0,
                            )
                            if success:
                                col1, col2, col3, col4 = st.columns(4)
                                c = "#10b981" if results["total_return"] >= 0 else "#ef4444"
                                with col1:
                                    st.metric("累计收益", f"{results['total_return']:.2f}%", delta_color="normal" if results["total_return"] >= 0 else "inverse")
                                with col2:
                                    st.metric("夏普比率", f"{results['sharpe']:.2f}")
                                with col3:
                                    st.metric("最大回撤", f"-{results['max_drawdown']:.2f}%", delta_color="inverse")
                                with col4:
                                    st.metric("交易次数", results["total_trades"])
                                st.success(f"✅ 回测成功！策略名: **{results['strategy_name']}** · 最终资金 ¥{results['final_value']:,.0f}")
                            else:
                                st.error(f"❌ 回测失败: {results.get('error','未知错误')}")
                        except Exception as e:
                            st.error(f"❌ 执行异常: {e}")
            else:
                st.warning("⚠️ 未检测到 Backtrader 策略类，请确认代码包含 `class XXX(bt.Strategy):`")
                st.info("提示：支持 Backtrader / 聚宽 / AKShare 格式的策略代码")

            st.markdown(f"✅ 已保存到: `{save_path.relative_to(ROOT_DIR)}`")

    with tab3:
        st.markdown("### 数据管理")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🗑️ 清空回测数据", use_container_width=True):
                try:
                    conn = st.session_state.db._get_conn()
                    conn.execute("DELETE FROM backtest_results")
                    conn.execute("DELETE FROM daily_values")
                    conn.execute("DELETE FROM trade_records")
                    conn.commit()
                    st.success("✅ 已清空")
                except Exception as e:
                    st.error(str(e))
        with c2:
            if st.button("🗑️ 清空AI报告", use_container_width=True):
                try:
                    conn = st.session_state.db._get_conn()
                    conn.execute("DELETE FROM ai_reports")
                    conn.commit()
                    st.success("✅ 已清空")
                except Exception as e:
                    st.error(str(e))
        with c3:
            if st.button("⚠️ 重置数据库", use_container_width=True):
                try:
                    from config import DB_PATH
                    if DB_PATH.exists():
                        DB_PATH.unlink()
                    st.success("✅ 已重置，请刷新页面")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        st.markdown("---")
        st.markdown('<div class="section-title">☁️ 部署信息</div>', unsafe_allow_html=True)
        st.markdown('''
        <div class="glass-card">
            <div style="color:#94a3b8;font-size:13px;line-height:2;">
                <b style="color:#e2e8f0;">🌐 公网地址</b> — <a href="https://bondtwilight-quant-analyzer.hf.space" target="_blank" style="color:#3b82f6;">Hugging Face Spaces</a><br>
                <b style="color:#e2e8f0;">💻 本地运行</b> — <code style="background:#1e293b;padding:2px 8px;border-radius:4px;color:#94a3b8;">streamlit run app.py --server.port 8501</code><br>
                <b style="color:#e2e8f0;">📦 GitHub</b> — <a href="https://github.com/BondTwilight/QuantAnalyzer" target="_blank" style="color:#3b82f6;">BondTwilight/QuantAnalyzer</a><br>
                <b style="color:#e2e8f0;">📊 数据源</b> — BaoStock（免费、稳定、无需代理）
            </div>
        </div>
        ''', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 📚 策略库页面
# ═══════════════════════════════════════════
def page_library():
    st.markdown('<div class="section-title">📚 内置策略库</div>', unsafe_allow_html=True)
    st.markdown('<div class="alert-box alert-info">🎯 点击任意策略即可一键回测。支持趋势跟踪、均值回归、动量因子、多因子等多种类型。</div>', unsafe_allow_html=True)

    # 导入策略库
    try:
        from strategy_library import STRATEGY_LIBRARY, get_all_strategies, list_categories
        all_strategies = get_all_strategies()
    except ImportError:
        st.error("策略库加载失败")
        return

    # 分类筛选
    categories = list(list_categories().keys())
    cols = st.columns([2, 2, 1])
    with cols[0]:
        selected_cat = st.selectbox("📁 策略分类", ["全部"] + categories)
    with cols[1]:
        difficulty_filter = st.selectbox("⭐ 难度筛选", ["全部", "⭐", "⭐⭐", "⭐⭐⭐"])
    with cols[2]:
        st.write("")  # 占位

    # 搜索
    search_q = st.text_input("🔍 搜索策略", placeholder="输入策略名称或描述...")

    # 过滤
    filtered = all_strategies
    if selected_cat != "全部":
        filtered = [s for s in filtered if s["category"] == selected_cat]
    if difficulty_filter != "全部":
        filtered = [s for s in filtered if s["difficulty"] == difficulty_filter]
    if search_q:
        q = search_q.lower()
        filtered = [s for s in filtered if q in s["name_cn"].lower() or q in s["name"].lower() or q in s["description"].lower()]

    st.markdown(f"**共 {len(filtered)} 个策略**")
    st.markdown("---")

    # 展示策略卡片
    for i in range(0, len(filtered), 2):
        col1, col2 = st.columns(2)
        for j, col in enumerate([col1, col2]):
            idx = i + j
            if idx >= len(filtered):
                break
            s = filtered[idx]

            with col:
                cat_colors = {
                    "趋势跟踪": "#3b82f6", "均值回归": "#10b981",
                    "动量因子": "#f59e0b", "多因子": "#8b5cf6",
                    "技术指标": "#ec4899", "事件驱动": "#06b6d4",
                }
            color = cat_colors.get(s["category"], "#3b82f6")

            with col.container():
                st.markdown(f"""
                <div style="background:#111827;border:1px solid #1e293b;border-radius:16px;padding:20px;margin-bottom:12px;position:relative;overflow:hidden;">
                    <div style="position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,{color},transparent);"></div>
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                        <span style="background:{color}22;color:{color};padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600;">{s["category"]}</span>
                        <span style="color:#94a3b8;font-size:12px;">{s["difficulty"]}</span>
                        <span style="color:#475569;font-size:12px;margin-left:auto;">{s["source"]}</span>
                    </div>
                    <div style="color:#e2e8f0;font-size:16px;font-weight:600;margin-bottom:6px;">{s["name_cn"]}</div>
                    <div style="color:#64748b;font-size:12px;margin-bottom:10px;">{s["name"]}</div>
                    <div style="color:#94a3b8;font-size:13px;line-height:1.6;margin-bottom:12px;">{s["description"][:120]}{'...' if len(s['description'])>120 else ''}</div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
                        <span style="background:#1e293b;color:#94a3b8;padding:2px 8px;border-radius:6px;font-size:11px;">💰 预期 {s["annual_expected"]}</span>
                        <span style="background:#1e293b;color:#94a3b8;padding:2px 8px;border-radius:6px;font-size:11px;">📌 适用 {s["suitable"]}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 回测按钮
                if st.button(f"▶️ 回测 {s['name_cn']}", key=f"run_{s['name']}", use_container_width=True):
                    st.session_state.selected_stock = "000001.SZ"
                    st.session_state.selected_strategy = s["name"]
                    st.session_state.run_backtest = True
                    st.success(f"✅ 已选择策略: {s['name_cn']}，请前往「⚔️ 策略对比」页面运行回测")
                    st.rerun()

    st.markdown("---")
    st.markdown("""
    <div class="glass-card" style="text-align:center;color:#64748b;font-size:13px;">
        💡 <b>提示</b>：策略库持续更新中。你可以上传自己的策略到「⚙️ 系统设置」页面，AI将自动分析并给出改进建议。
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 🧠 策略代码分析器页面
# ═══════════════════════════════════════════
def page_code_analyzer():
    st.markdown('<div class="section-title">🧠 策略代码 AI 分析器</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="alert-box alert-info">
        🤖 将任意量化策略代码粘贴到下方，AI将自动解析买卖逻辑、评估风险等级、给出改进建议。<br>
        支持 <b>Backtrader</b> / <b>聚宽</b> / <b>任意Python交易代码</b>。
    </div>
    """, unsafe_allow_html=True)

    # 初始化分析器
    from core.ai_analyzer import AIAnalyzer, MultiModelAnalyzer
    from config import AI_MODELS, DEFAULT_MODEL_PRIORITY

    analyzer = AIAnalyzer()
    multi = MultiModelAnalyzer()

    # 检测可用模型
    available = [AI_MODELS[m]["name"] for m in multi.available_models]
    unavailable = [AI_MODELS[m]["name"] for m in DEFAULT_MODEL_PRIORITY if m not in multi.available_models]

    col1, col2 = st.columns([1, 1])
    with col1:
        if available:
            st.markdown(f"✅ **已接入模型 ({len(available)})**: {', '.join(available[:4])}{'...' if len(available)>4 else ''}")
    with col2:
        if unavailable:
            st.markdown(f"⚙️ **未配置 ({len(unavailable)})**: {', '.join(unavailable[:3])}{'...' if len(unavailable)>3 else ''}")

    st.markdown("---")

    # 示例代码
    with st.expander("📋 查看示例 Backtrader 策略代码"):
        example_code = '''import backtrader as bt

class MyStrategy(bt.Strategy):
    params = (
        ("fast", 5),    # 短期均线周期
        ("slow", 20),   # 长期均线周期
    )

    def __init__(self):
        # 均线指标
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.fast)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.slow)
        # 金叉/死叉信号
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        # 金叉买入，死叉卖出
        if self.crossover > 0:
            self.buy()
        elif self.crossover < 0:
            self.sell()
'''
        st.code(example_code, language="python")

    # 代码输入
    st.markdown("#### 📝 粘贴策略代码")
    code_input = st.text_area(
        "策略代码",
        placeholder="在此粘贴你的量化策略代码...",
        height=350,
        label_visibility="collapsed"
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        source_type = st.selectbox("代码类型", ["auto", "backtrader", "jqdata", "pseudocode"], format_func=lambda x: {
            "auto": "🤖 自动检测", "backtrader": "Backtrader", "jqdata": "聚宽JQData", "pseudocode": "伪代码/描述"
        }[x])

    with col2:
        st.write("")

    if st.button("🚀 AI 深度分析", type="primary", use_container_width=True):
        if not code_input.strip():
            st.warning("请先粘贴策略代码")
        else:
            with st.spinner("🤖 AI 正在分析策略代码..."):
                result = analyzer.analyze_code(code_input, source_type)

            # 解析结果
            structure = result.get("structure", {})
            ai_analysis = result.get("ai_analysis", "")
            risk_info = result.get("risk_info", {})

            # 结构分析
            st.markdown("#### 📊 代码结构分析")
            struct_cols = st.columns(4)
            with struct_cols[0]:
                st.metric("交易逻辑", "✅ 有" if structure.get("has_next") else "❌ 缺失", delta=None)
            with struct_cols[1]:
                st.metric("买入逻辑", "✅ 有" if structure.get("has_buy_logic") else "❌ 缺失", delta=None)
            with struct_cols[2]:
                st.metric("卖出逻辑", "✅ 有" if structure.get("has_sell_logic") else "❌ 缺失", delta=None)
            with struct_cols[3]:
                st.metric("可回测性", "✅ 可回测" if structure.get("can_backtest") else "⚠️ 需修改", delta=None)

            # 检测到的指标
            indicators = structure.get("indicators", [])
            if indicators:
                st.markdown("**🔧 检测到的技术指标**: " + " ".join([f"`{i}`" for i in indicators]))

            # 检测到的参数
            params = structure.get("parameters", [])
            if params:
                st.markdown(f"**⚙️ 检测到的参数** ({len(params)}个): " + ", ".join([f"`{p['name']}={p['value']}`" for p in params[:8]]))

            # 问题
            issues = structure.get("issues", [])
            if issues:
                for issue in issues:
                    st.markdown(f'<div class="alert-box alert-warning">⚠️ {issue}</div>', unsafe_allow_html=True)

            st.markdown("---")

            # 风险评估
            st.markdown("#### ⚠️ 风险评估")
            risk_level = risk_info.get("level", "未知")
            risk_issues = risk_info.get("issues", [])
            st.markdown(f"**风险等级**: {risk_level}")
            for rissue in risk_issues:
                st.markdown(f"- {rissue}")

            st.markdown("---")

            # AI深度分析
            if ai_analysis and "分析失败" not in ai_analysis:
                st.markdown("#### 🤖 AI 深度分析报告")
                st.markdown(ai_analysis)
            else:
                st.markdown('<div class="alert-box alert-warning">AI分析暂不可用。请在「⚙️ 系统设置」中配置 API Key。</div>', unsafe_allow_html=True)

            st.markdown("---")

            # 快速回测按钮
            if structure.get("can_backtest"):
                st.markdown("""
                <div style="background:#111827;border:1px solid #10b981;border-radius:12px;padding:16px;text-align:center;">
                    <span style="color:#10b981;font-weight:600;">✅ 策略代码可回测</span><br>
                    <span style="color:#64748b;font-size:13px;">前往「⚔️ 策略对比」页面运行回测</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-box alert-warning">⚠️ 策略代码存在缺失项，建议根据AI分析报告修改后再回测</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# ⚔️ 策略PK竞技场页面（核心新功能）
# ═══════════════════════════════════════════
def page_strategy_pk():
    try:
        from core.strategy_arena import render_strategy_pk_arena
        render_strategy_pk_arena()
    except ImportError as e:
        import streamlit as st
        st.error(f"策略PK模块加载失败: {e}")

# 🌐 量化平台对比页面
# ═══════════════════════════════════════════
def page_platform_comparison():
    try:
        from core.platform_comparison import render_platform_comparison
        render_platform_comparison()
    except ImportError as e:
        import streamlit as st
        st.error(f"平台对比模块加载失败: {e}")

# ═══════════════════════════════════════════
# 主路由
# ═══════════════════════════════════════════
page = render_sidebar()
page_map = {
    "🏠 首页": page_home,
    "⚔️ 策略PK": page_strategy_pk,
    "📊 策略总览": page_overview,
    "📚 策略库": page_library,
    "🌐 平台对比": page_platform_comparison,
    "🧠 代码分析": page_code_analyzer,
    "🏦 市场看板": page_market,
    "📈 专业分析": page_analysis,
    "🔮 AI预测": page_ai_predict,
    "📉 K线分析": page_kline,
    "⚔️ 策略对比": page_compare,
    "📈 策略详情": page_detail,
    "📋 交易明细": page_trades,
    "🗓️ 收益日历": page_calendar,
    "🤖 AI 分析": page_ai,
    "⚠️ 风险仪表盘": page_risk,
    "⚙️ 系统设置": page_settings,
}
page_map.get(page, page_overview)()
