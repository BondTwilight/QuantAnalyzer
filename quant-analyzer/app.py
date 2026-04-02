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
# 页面3: K线分析（新增）
# ═══════════════════════════════════════════
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
