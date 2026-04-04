"""
🧬 策略进化中心 v4.0 — AlphaForge + 情报采集

核心升级:
1. AlphaForge 自动因子挖掘引擎
2. 7阶段流水线可视化（数据→种子→GP进化→评估→组合→验证→更新）
3. 实时因子发现与IC/IR展示
4. 策略组合信号回测
5. 进化历史与最佳策略追踪
6. 🆕 策略情报采集系统（WorldQuant Alpha101 / 学术论文 / GitHub开源 / 社交媒体）
"""

import streamlit as st
import json
import time
import threading
from datetime import datetime
from pathlib import Path
import sys
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

# ═══════════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════════
st.set_page_config(
    page_title="AlphaForge 进化中心 | QuantBrain",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 进化中心专用样式
st.markdown("""<style>
/* AlphaForge 专属渐变 */
.af-gradient { 
    background: linear-gradient(135deg, #3b82f6, #8b5cf6, #a855f7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

/* 流水线阶段卡片 */
.af-phase {
    background: linear-gradient(135deg, #1a1f35, #141929);
    border: 2px solid #1e293b;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 6px;
    transition: all 0.3s ease;
}
.af-phase.pending { border-color: #334155; opacity: 0.5; }
.af-phase.running { 
    border-color: #3b82f6; 
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
    animation: af-pulse 2s infinite;
}
.af-phase.completed { border-color: #10b981; }
.af-phase.failed { border-color: #ef4444; }

@keyframes af-pulse {
    0%, 100% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
    50% { box-shadow: 0 0 30px rgba(59, 130, 246, 0.5); }
}

.af-phase-icon { font-size: 20px; margin-right: 6px; }
.af-phase-title { font-size: 13px; font-weight: 600; color: #f8fafc; }
.af-phase-desc { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.af-phase-badge {
    font-size: 10px; padding: 2px 8px; border-radius: 10px;
    display: inline-block; font-weight: 600; text-transform: uppercase;
}
.af-phase-badge.pending { background: #334155; color: #94a3b8; }
.af-phase-badge.running { background: #3b82f622; color: #3b82f6; }
.af-phase-badge.completed { background: #10b98122; color: #10b981; }
.af-phase-badge.failed { background: #ef444422; color: #ef4444; }

/* 进度条 */
.af-progress-bg {
    background: #0f1629; border-radius: 6px; height: 4px;
    overflow: hidden; margin-top: 8px;
}
.af-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #a855f7);
    border-radius: 6px; transition: width 0.5s ease;
}

/* 因子卡片 */
.af-factor-card {
    background: linear-gradient(135deg, #1a1f35, #141929);
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    transition: all 0.2s;
}
.af-factor-card:hover { border-color: #3b82f6; transform: translateY(-1px); }
.af-factor-expr {
    font-family: 'Fira Code', 'Courier New', monospace;
    font-size: 12px; color: #93c5fd; word-break: break-all;
}
.af-factor-metric { font-size: 12px; color: #94a3b8; }
.af-factor-value { font-weight: 700; }
.af-factor-value.good { color: #10b981; }
.af-factor-value.mid { color: #fbbf24; }
.af-factor-value.bad { color: #ef4444; }

/* 日志 */
.af-log {
    background: #0a0e1a; border: 1px solid #1e293b;
    border-radius: 8px; padding: 12px;
    height: 280px; overflow-y: auto;
    font-family: 'Courier New', monospace; font-size: 11px;
}
.af-log-time { color: #64748b; margin-right: 6px; }
.af-log-phase { color: #3b82f6; margin-right: 6px; font-weight: 600; }
.af-log-msg { color: #e2e8f0; }
.af-log-ok { color: #10b981; }
.af-log-err { color: #ef4444; }
.af-log-warn { color: #fbbf24; }

/* KPI */
.af-kpi {
    background: linear-gradient(135deg, #111827, #1a2235);
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 14px 18px;
    position: relative; overflow: hidden;
}
.af-kpi::before {
    content: ''; position: absolute;
    top: 0; left: 0; right: 0; height: 3px;
}
.af-kpi.blue::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.af-kpi.green::before { background: linear-gradient(90deg, #10b981, #34d399); }
.af-kpi.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.af-kpi.orange::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.af-kpi-label { color: #64748b; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }
.af-kpi-value { color: #f1f5f9; font-size: 22px; font-weight: 800; margin-top: 4px; }
.af-kpi-sub { color: #475569; font-size: 11px; margin-top: 4px; }

/* 策略卡 */
.af-strategy {
    background: linear-gradient(135deg, #1a1f35, #141929);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    transition: all 0.2s;
}
.af-strategy:hover { border-color: #10b981; transform: translateY(-1px); }
.af-strategy-score {
    font-size: 28px; font-weight: 800;
    background: linear-gradient(90deg, #3b82f6, #a855f7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

/* 连接线 */
.af-connector {
    text-align: center; color: #334155; font-size: 18px; padding: 0 4px;
}
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 初始化 AlphaForge 引擎
# ═══════════════════════════════════════════════
@st.cache_resource
def init_alphaforge():
    """初始化 AlphaForge 引擎"""
    try:
        from core.alphaforge.factor_engine import FactorEngine
        from core.alphaforge.factor_analyzer import FactorAnalyzer
        from core.alphaforge.genetic_programming import GeneticProgrammer
        from core.alphaforge.strategy_ensemble import StrategyEnsemble
        from core.alphaforge.auto_scheduler import EvolutionScheduler, get_evolution_scheduler
        return {
            "factor_engine": FactorEngine(),
            "factor_analyzer": FactorAnalyzer(),
            "genetic_programmer": GeneticProgrammer(),
            "strategy_ensemble": StrategyEnsemble(),
            "scheduler": get_evolution_scheduler(),
            "loaded": True,
        }
    except Exception as e:
        return {"loaded": False, "error": str(e)}

engines = init_alphaforge()

# Session state
if "af_logs" not in st.session_state:
    st.session_state.af_logs = []
if "af_running" not in st.session_state:
    st.session_state.af_running = False
if "af_last_result" not in st.session_state:
    st.session_state.af_last_result = None
if "af_auto_refresh" not in st.session_state:
    st.session_state.af_auto_refresh = False
if "af_best_factors" not in st.session_state:
    st.session_state.af_best_factors = []
if "af_ensemble_result" not in st.session_state:
    st.session_state.af_ensemble_result = None


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════
PHASES_7 = [
    ("data_load", "📥", "数据加载", "获取最新行情数据"),
    ("seed_factors", "🌱", "种子因子", "生成20个已知有效因子"),
    ("gp_evolve", "🧬", "GP进化", "遗传编程搜索新因子"),
    ("factor_eval", "📊", "因子评估", "IC/IR分析+分层回测"),
    ("ensemble", "🎯", "策略组合", "多因子加权融合"),
    ("validate", "✅", "回测验证", "组合策略历史回测"),
    ("update", "🚀", "更新策略", "持久化最佳策略"),
]

def af_log(msg: str, phase: str = "", level: str = "info"):
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "phase": phase, "msg": msg, "level": level,
    }
    st.session_state.af_logs.append(entry)
    if len(st.session_state.af_logs) > 200:
        st.session_state.af_logs = st.session_state.af_logs[-200:]

def get_ic_color(ic: float) -> str:
    if abs(ic) >= 0.05: return "good"
    elif abs(ic) >= 0.02: return "mid"
    return "bad"

def render_phase(icon: str, name: str, desc: str, status: str, progress: float = 0):
    cls = status if status in ("pending", "running", "completed", "failed") else "pending"
    badge_label = {"pending": "等待", "running": "运行中", "completed": "完成", "failed": "失败"}.get(cls, cls)
    return f"""
    <div class="af-phase {cls}">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <span class="af-phase-icon">{icon}</span>
                <span class="af-phase-title">{name}</span>
                <div class="af-phase-desc">{desc}</div>
            </div>
            <span class="af-phase-badge {cls}">{badge_label}</span>
        </div>
        <div class="af-progress-bg">
            <div class="af-progress-bar" style="width:{progress}%"></div>
        </div>
    </div>"""


# ═══════════════════════════════════════════════
# 页面标题
# ═══════════════════════════════════════════════
st.markdown("# 🧬 AlphaForge 进化中心")
st.markdown("### 自动因子挖掘 + 遗传编程进化 + 多因子组合策略")
st.markdown("---")

# 引擎加载检查
if not engines.get("loaded"):
    st.error(f"⚠️ AlphaForge 引擎加载失败: {engines.get('error', '未知错误')}")
    st.info("请确保已安装所有依赖: numpy, pandas, scipy, scikit-learn")
    st.stop()


# ═══════════════════════════════════════════════
# 主控制区
# ═══════════════════════════════════════════════
col_c1, col_c2, col_c3, col_c4 = st.columns([3, 1.5, 1, 1])

with col_c1:
    status_text = "🟡 进化中..." if st.session_state.af_running else "🟢 就绪"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1f35,#141929);border-radius:12px;padding:16px;border:1px solid #1e293b;">
        <div style="font-size:12px;color:#64748b;margin-bottom:4px;">AlphaForge 引擎状态</div>
        <div style="font-size:18px;font-weight:600;color:#f8fafc;">{status_text}</div>
        <div style="font-size:11px;color:#94a3b8;margin-top:4px;">
            FactorEngine ✅ | GeneticProgrammer ✅ | FactorAnalyzer ✅ | StrategyEnsemble ✅
        </div>
    </div>""", unsafe_allow_html=True)

with col_c2:
    # 进化参数
    with st.popover("⚙️ 参数设置"):
        gen_count = st.slider("进化代数", 1, 20, 3)
        pop_size = st.slider("种群大小", 10, 200, 50)
        min_ic = st.slider("最小IC阈值", 0.0, 0.1, 0.02, 0.005)
        st.caption("参数仅在下次启动时生效")

with col_c3:
    if st.button("🚀 启动进化", type="primary", use_container_width=True,
                 disabled=st.session_state.af_running):
        st.session_state.af_running = True
        st.session_state.af_auto_refresh = True
        af_log("🚀 AlphaForge 进化启动", "system", "ok")
        
        def run_evolution():
            """后台运行进化"""
            try:
                scheduler = engines["scheduler"]
                
                # 进度回调函数
                def progress_cb(pct: float, msg: str):
                    af_log(f"[{pct:.0f}%] {msg}", "evolution", "info")
                
                # 设置进度回调
                scheduler.set_progress_callback(progress_cb)
                
                # 直接调用 run_evolution（适配 EvolutionScheduler 的实际接口）
                task = scheduler.run_evolution(
                    task_type="full",
                    progress_cb=progress_cb,
                )
                
                # 存储结果
                st.session_state.af_last_result = {
                    "task": task.to_dict() if hasattr(task, 'to_dict') else str(task),
                    "timestamp": datetime.now().isoformat(),
                }
                
                # 获取最佳因子
                best = scheduler.get_best_strategy()
                if best:
                    st.session_state.af_best_factors = best.get("factors", [])
                    st.session_state.af_ensemble_result = best
                
                st.session_state.af_running = False
                af_log(f"✅ 进化完成！测试: {task.factors_tested} 因子, 有效: {task.factors_valid}, 最佳适应度: {task.best_fitness:.4f}", "system", "ok")
                
            except Exception as e:
                st.session_state.af_running = False
                af_log(f"❌ 进化失败: {str(e)}", "system", "err")
                import traceback
                af_log(traceback.format_exc()[:500], "system", "err")
        
        thread = threading.Thread(target=run_evolution, daemon=True)
        thread.start()
        time.sleep(0.3)
        st.rerun()

with col_c4:
    if st.button("⏹️ 停止", use_container_width=True,
                 disabled=not st.session_state.af_running):
        st.session_state.af_running = False
        st.session_state.af_auto_refresh = False
        af_log("⏹️ 进化已停止", "system", "warn")
        st.rerun()
    
    auto_ref = st.toggle("🔄 自动刷新", value=st.session_state.af_auto_refresh, key="af_toggle")
    if auto_ref != st.session_state.af_auto_refresh:
        st.session_state.af_auto_refresh = auto_ref
        st.rerun()


# ═══════════════════════════════════════════════
# 7 阶段流水线
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🔄 进化流水线")
st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:12px;'>数据加载 → 种子因子 → GP进化搜索 → IC/IR评估 → 多因子组合 → 回测验证 → 更新最佳策略</div>", unsafe_allow_html=True)

# 获取当前状态
phase_status = {}
if st.session_state.af_running:
    # 进化中：按顺序标记
    for i, (pid, _, _, _) in enumerate(PHASES_7):
        if i == 0:
            phase_status[pid] = ("running", 30)
        elif i < 3:
            phase_status[pid] = ("pending", 0)
        else:
            phase_status[pid] = ("pending", 0)
elif st.session_state.af_last_result:
    for pid, _, _, _ in PHASES_7:
        phase_status[pid] = ("completed", 100)
else:
    for pid, _, _, _ in PHASES_7:
        phase_status[pid] = ("pending", 0)

# 渲染 7 阶段 — 4+3 布局
cols_top = st.columns(4)
cols_bot = st.columns(3)

for i, (pid, icon, name, desc) in enumerate(PHASES_7):
    status, pct = phase_status.get(pid, ("pending", 0))
    html = render_phase(icon, name, desc, status, pct)
    col = cols_top[i] if i < 4 else cols_bot[i - 4]
    col.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 🆕 策略情报采集面板
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🕵️ 策略情报采集")
st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:12px;'>从顶级量化机构的公开策略中采集因子，注入 AlphaForge 进化引擎</div>", unsafe_allow_html=True)

# 初始化情报采集器
try:
    from core.alphaforge.intelligence_collector import IntelligenceCollector, INTELLIGENCE_SOURCES
    ic_collector = IntelligenceCollector()
    ic_stats = ic_collector.get_collected_stats()
    ic_loaded = True
except Exception as e:
    ic_loaded = False
    ic_stats = {"total": 0, "by_source": {}, "by_category": {}}

# 情报源概览
if ic_loaded:
    ic_cols = st.columns(6)
    source_icons = {
        "worldquant_alpha101": ("🏛️", "WQ Alpha101"),
        "factors_directory": ("🌐", "Factors.Dir"),
        "github_open_source": ("📦", "GitHub"),
        "academic_papers": ("📄", "学术论文"),
        "social_media": ("📱", "社交媒体"),
    }

    for i, (key, (icon, label)) in enumerate(source_icons.items()):
        count = ic_stats.get("by_source", {}).get(key, 0)
        source_info = INTELLIGENCE_SOURCES.get(key, {})
        enabled = source_info.get("enabled", True)
        priority = source_info.get("priority", 0)

        with ic_cols[i]:
            color = "#10b981" if count > 0 else "#334155"
            border_color = "#10b981" if count > 0 else "#1e293b"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#111827,#1a2235);
                        border:1px solid {border_color};border-radius:10px;padding:12px;text-align:center;">
                <div style="font-size:20px;">{icon}</div>
                <div style="font-size:12px;color:#94a3b8;margin-top:4px;">{label}</div>
                <div style="font-size:18px;font-weight:700;color:{color};margin-top:4px;">{count}</div>
                <div style="font-size:10px;color:#475569;">P{priority} {'✅' if enabled else '❌'}</div>
            </div>""", unsafe_allow_html=True)

    # 采集操作栏
    ic_col1, ic_col2, ic_col3 = st.columns([2, 2, 1])

    with ic_col1:
        if st.button("🔍 一键采集所有情报源", type="primary", use_container_width=True):
            with st.spinner("正在采集策略情报..."):
                try:
                    result = ic_collector.collect_all()
                    st.session_state.af_intelligence_result = result
                    st.success(f"✅ 采集完成！新增 {result['total_new']} 个因子（总计 {result['total_collected']}）")
                    af_log(f"情报采集完成: 新增 {result['total_new']} 因子", "intelligence", "ok")
                except Exception as e:
                    st.error(f"采集失败: {e}")
                    af_log(f"情报采集失败: {e}", "intelligence", "err")
                st.rerun()

    with ic_col2:
        # 分类筛选
        categories = list(ic_stats.get("by_category", {}).keys())
        selected_cat = st.selectbox("按分类筛选", ["全部"] + categories, key="ic_cat_filter")
    
    with ic_col3:
        # 采集建议
        if st.button("💡 采集建议", use_container_width=True):
            try:
                rec = ic_collector.get_schedule_recommendation()
                st.session_state.af_ic_recommendations = rec
            except Exception:
                pass

    # 分类分布
    cat_data = ic_stats.get("by_category", {})
    if cat_data:
        ic_chart1, ic_chart2 = st.columns(2)

        with ic_chart1:
            fig_cat = go.Figure(data=[go.Pie(
                labels=list(cat_data.keys()),
                values=list(cat_data.values()),
                hole=0.5,
                marker_colors=["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"],
            )])
            fig_cat.update_layout(
                title="因子分类分布",
                template="plotly_dark",
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=True,
                legend=dict(font_size=10),
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        with ic_chart2:
            # 来源分布
            src_data = ic_stats.get("by_source", {})
            if src_data:
                fig_src = go.Figure(data=[go.Bar(
                    x=list(src_data.keys()),
                    y=list(src_data.values()),
                    marker_color=["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"][:len(src_data)],
                    text=[str(v) for v in src_data.values()],
                    textposition="auto",
                )])
                fig_src.update_layout(
                    title="因子来源分布",
                    template="plotly_dark",
                    height=280,
                    margin=dict(l=20, r=20, t=40, b=20),
                    xaxis=dict(tickangle=-30, tickfont=dict(size=9)),
                    yaxis_title="因子数",
                )
                st.plotly_chart(fig_src, use_container_width=True)

    # 因子列表展示
    with st.expander("📋 已采集因子详情", expanded=False):
        collected = ic_collector.get_collected_factors()
        if collected:
            # 按筛选条件过滤
            if selected_cat and selected_cat != "全部":
                collected = [f for f in collected if f.category == selected_cat]

            # 分页显示
            page_size = 20
            page = st.number_input("页码", min_value=1, max_value=max(1, len(collected) // page_size + 1), value=1)
            start = (page - 1) * page_size
            page_factors = collected[start:start + page_size]

            st.markdown(f"<div style='color:#64748b;font-size:11px;margin-bottom:8px;'>显示 {start+1}-{min(start+page_size, len(collected))} / {len(collected)} 个因子</div>", unsafe_allow_html=True)

            for f in page_factors:
                src_badge = {
                    "worldquant_alpha101": "🏛️WQ",
                    "factors_directory": "🌐FD",
                    "github_open_source": "📦GH",
                    "academic_papers": "📄AC",
                    "social_media": "📱SM",
                }.get(f.source, "❓")
                cat_names = {
                    "price_momentum": "📈动量",
                    "volume_price": "📊量价",
                    "volatility": "🌊波动",
                    "reversal": "🔄反转",
                    "trend": "📈趋势",
                    "statistical": "📐统计",
                    "composite": "🧩复合",
                    "liquidity": "💧流动",
                }.get(f.category, f.category)

                st.markdown(f"""
                <div class="af-factor-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <span style="font-size:10px;color:#64748b;">{src_badge}</span>
                            <span style="font-size:10px;color:#64748b;margin-left:4px;">{cat_names}</span>
                            <span style="font-size:11px;color:#e2e8f0;margin-left:6px;font-weight:600;">{f.name}</span>
                            <div class="af-factor-expr" style="margin-top:2px;">{f.expression}</div>
                        </div>
                        <div style="text-align:right;flex-shrink:0;margin-left:12px;">
                            <div style="font-size:10px;color:#64748b;">{f.description}</div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("暂无采集因子。点击「一键采集所有情报源」开始。")

    # 采集建议展示
    if "af_ic_recommendations" in st.session_state:
        rec = st.session_state.af_ic_recommendations
        with st.expander("💡 采集建议"):
            for r in rec.get("recommendations", []):
                action_icon = {"first_collect": "🆕", "expand": "📈"}.get(r.get("action", ""), "📌")
                st.markdown(f"{action_icon} **{r['name']}** (P{r['priority']}) — {r['message']}")

else:
    st.warning("情报采集器加载失败，请确保 alphaforge 模块已正确安装。")


# ═══════════════════════════════════════════════
# KPI 指标区
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📊 核心指标")

result = st.session_state.af_last_result
task_data = result.get("task", {}) if result else {}

k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(f"""<div class="af-kpi blue">
    <div class="af-kpi-label">测试因子数</div>
    <div class="af-kpi-value">{task_data.get('factors_tested', 0)}</div>
    <div class="af-kpi-sub">本轮进化探索</div>
</div>""", unsafe_allow_html=True)

k2.markdown(f"""<div class="af-kpi green">
    <div class="af-kpi-label">有效因子数</div>
    <div class="af-kpi-value">{task_data.get('factors_valid', 0)}</div>
    <div class="af-kpi-sub">通过IC阈值筛选</div>
</div>""", unsafe_allow_html=True)

k3.markdown(f"""<div class="af-kpi purple">
    <div class="af-kpi-label">最佳适应度</div>
    <div class="af-kpi-value">{task_data.get('best_fitness', 0):.4f}</div>
    <div class="af-kpi-sub">IC·IR·夏普加权</div>
</div>""", unsafe_allow_html=True)

k4.markdown(f"""<div class="af-kpi orange">
    <div class="af-kpi-label">组合评分</div>
    <div class="af-kpi-value">{task_data.get('ensemble_score', 0):.1f}</div>
    <div class="af-kpi-sub">多因子融合效果</div>
</div>""", unsafe_allow_html=True)

k5.markdown(f"""<div class="af-kpi blue">
    <div class="af-kpi-label">耗时</div>
    <div class="af-kpi-value">{task_data.get('duration_seconds', 0):.1f}s</div>
    <div class="af-kpi-sub">端到端进化时间</div>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 最佳因子 + 实时日志
# ═══════════════════════════════════════════════
st.markdown("---")
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.markdown("### 🧪 发现的有效因子")
    
    factors = st.session_state.af_best_factors
    if factors:
        for i, f in enumerate(factors[:10]):
            ic_val = f.get("ic_mean", 0)
            ir_val = f.get("ir", 0)
            fit = f.get("fitness", 0)
            ic_cls = get_ic_color(ic_val)
            
            st.markdown(f"""
            <div class="af-factor-card">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="font-size:10px;color:#64748b;">#{i+1}</span>
                        <span class="af-factor-expr">{f.get('expression', 'N/A')}</span>
                    </div>
                    <div style="text-align:right;">
                        <div class="af-factor-metric">
                            IC=<span class="af-factor-value {ic_cls}">{ic_val:.4f}</span>
                        </div>
                        <div class="af-factor-metric">
                            IR={ir_val:.3f} | Fit={fit:.3f}
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("暂无因子数据。点击「启动进化」开始自动因子挖掘。")
        
    # 展示内置种子因子
    with st.expander("📋 内置种子因子库 (20个)"):
        seed_factors = [
            "sma(close, 5) / sma(close, 20)",          # 短期vs长期均线
            "ts_rank(close, 10)",                       # 价格排名
            "ts_delta(close, 3) / close",               # 3日动量
            "ts_std(returns, 20) * sqrt(252)",           # 年化波动率
            "ts_corr(close, volume, 10)",               # 量价相关性
            "ts_skewness(returns, 20)",                  # 收益偏度
            "ts_min(low, 5) / close",                   # 5日最低价比
            "ts_max(high, 10) / close",                 # 10日最高价比
            "(close - ts_min(low, 20)) / (ts_max(high, 20) - ts_min(low, 20) + 1e-8)",  # KDJ
            "volume / ts_mean(volume, 20)",              # 量比
            "ts_rank(returns, 5)",                       # 短期收益排名
            "ts_decay_linear(close, 10)",                # 线性衰减
            "ts_mean(returns, 5) / ts_std(returns, 20)",  # 夏普因子
            "ts_corr(close, ts_rank(volume, 10), 5)",    # 价格量排名相关性
            "ts_sum(max(returns, 0), 20) / ts_sum(abs(returns), 20)",  # 上涨占比
            "ts_delta(volume, 3) / ts_mean(volume, 20)",  # 量变化率
            "ts_argmax(close, 20) / 20",                 # 最高点位置
            "ts_argmin(close, 20) / 20",                 # 最低点位置
            "ts_regression(close, ts_step(5), 5, 1)",    # 5日斜率
            "ts_zscore(close, 20)",                       # Z-score标准化
        ]
        for i, sf in enumerate(seed_factors):
            st.code(f"{i+1:2d}. {sf}", language="text")

with col_right:
    st.markdown("### 📜 实时日志")
    
    log_html = '<div class="af-log">'
    logs = st.session_state.af_logs[-30:]
    if logs:
        for log in logs:
            lvl = log.get("level", "info")
            phase_tag = f'<span class="af-log-phase">[{log.get("phase","")}]</span>' if log.get("phase") else ""
            msg_cls = {"ok": "af-log-ok", "err": "af-log-err", "warn": "af-log-warn"}.get(lvl, "af-log-msg")
            log_html += f'''<div style="padding:1px 0;border-bottom:1px solid #1e293b22;">
                <span class="af-log-time">{log["time"]}</span>
                {phase_tag}
                <span class="{msg_cls}">{log["msg"]}</span>
            </div>'''
    else:
        log_html += '<div style="color:#475569;padding:20px;text-align:center;">等待进化启动...</div>'
    log_html += '</div>'
    st.markdown(log_html, unsafe_allow_html=True)
    
    if st.button("🗑️ 清空日志"):
        st.session_state.af_logs = []
        st.rerun()


# ═══════════════════════════════════════════════
# 组合策略结果
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🎯 最佳组合策略")

ensemble = st.session_state.af_ensemble_result
if ensemble:
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    
    with col_e1:
        score = ensemble.get("composite_score", 0)
        st.markdown(f"""<div class="af-strategy">
            <div style="font-size:11px;color:#64748b;">综合评分</div>
            <div class="af-strategy-score">{score:.1f}</div>
            <div style="font-size:11px;color:#94a3b8;">多因子加权</div>
        </div>""", unsafe_allow_html=True)
    
    with col_e2:
        trades = ensemble.get("total_trades", 0)
        wr = ensemble.get("win_rate", 0)
        st.markdown(f"""<div class="af-strategy">
            <div style="font-size:11px;color:#64748b;">交易统计</div>
            <div style="font-size:18px;font-weight:700;color:#f8fafc;">{trades} 笔</div>
            <div style="font-size:14px;font-weight:600;color:{'#10b981' if wr>0.5 else '#ef4444'};">胜率 {wr:.1%}</div>
        </div>""", unsafe_allow_html=True)
    
    with col_e3:
        sharpe = ensemble.get("sharpe_ratio", 0)
        ret = ensemble.get("annual_return", 0)
        st.markdown(f"""<div class="af-strategy">
            <div style="font-size:11px;color:#64748b;">收益指标</div>
            <div style="font-size:18px;font-weight:700;color:#f8fafc;">{ret:.1%}</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8;">夏普 {sharpe:.2f}</div>
        </div>""", unsafe_allow_html=True)
    
    with col_e4:
        dd = abs(ensemble.get("max_drawdown", 0))
        pf = ensemble.get("profit_factor", 0)
        st.markdown(f"""<div class="af-strategy">
            <div style="font-size:11px;color:#64748b;">风险控制</div>
            <div style="font-size:18px;font-weight:700;color:#ef4444;">{dd:.1%}</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8;">盈亏比 {pf:.2f}</div>
        </div>""", unsafe_allow_html=True)
    
    # 策略详情
    factors_in_ensemble = ensemble.get("factors", [])
    if factors_in_ensemble:
        with st.expander("📋 策略因子构成"):
            for i, f in enumerate(factors_in_ensemble):
                weight = f.get("weight", 0)
                ic = f.get("ic_mean", 0)
                st.markdown(f"**{i+1}.** `{f.get('expression','?')}` — 权重: {weight:.3f}, IC: {ic:.4f}")
    
    # 交易信号
    signals = ensemble.get("signals", [])
    if signals:
        with st.expander("📊 交易信号明细"):
            df_signals = pd.DataFrame(signals[:50])
            if not df_signals.empty:
                st.dataframe(df_signals, use_container_width=True, hide_index=True)

else:
    st.info("暂无组合策略数据。运行进化后将自动生成多因子组合策略。")


# ═══════════════════════════════════════════════
# 进化历史
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📈 进化历史")

try:
    scheduler = engines["scheduler"]
    history = scheduler.get_evolution_history(limit=10)
    
    if history:
        # 构建DataFrame
        hist_data = []
        for h in history:
            status_icon = {"completed": "✅", "failed": "❌", "running": "🔄"}.get(h.get("status","?"), "❓")
            hist_data.append({
                "状态": status_icon,
                "时间": h.get("started_at", "")[:16],
                "类型": h.get("task_type", ""),
                "测试因子": h.get("factors_tested", 0),
                "有效因子": h.get("factors_valid", 0),
                "最佳适应度": f"{h.get('best_fitness', 0):.4f}",
                "组合评分": f"{h.get('ensemble_score', 0):.1f}",
                "耗时": f"{h.get('duration_seconds', 0):.1f}s",
            })
        
        df_hist = pd.DataFrame(hist_data)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        
        # 适应度变化图
        if len(history) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=[h.get("best_fitness", 0) for h in history],
                mode="lines+markers",
                name="最佳适应度",
                line=dict(color="#3b82f6", width=2),
                marker=dict(size=8, color="#a855f7"),
            ))
            fig.update_layout(
                title="适应度进化趋势",
                xaxis_title="进化轮次",
                yaxis_title="Fitness",
                template="plotly_dark",
                height=300,
                margin=dict(l=40, r=20, t=40, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无进化历史记录。")
except Exception as e:
    st.warning(f"读取历史失败: {e}")


# ═══════════════════════════════════════════════
# 快速因子探索
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🔬 快速因子计算")

with st.form("factor_calc_form"):
    col_fc1, col_fc2, col_fc3 = st.columns([2, 1, 1])
    
    with col_fc1:
        factor_expr = st.text_input(
            "因子表达式",
            value="sma(close, 5) / sma(close, 20)",
            placeholder="例如: ts_rank(close, 10), ts_delta(close, 3) / close",
            help="支持所有 AlphaForge 算子: sma, ema, rsi, macd, ts_rank, ts_delta, ts_corr, ts_std 等"
        )
    
    with col_fc2:
        stock_code = st.text_input("股票代码", value="000001.SZ", help="带交易所后缀")
    
    with col_fc3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🧪 计算因子", type="primary", use_container_width=True)
    
    if submitted and factor_expr:
        with st.spinner("计算中..."):
            try:
                from data.fetcher import get_stock_data
                engine = engines["factor_engine"]
                
                # 获取数据
                df = get_stock_data(stock_code, period="2y")
                if df is not None and not df.empty:
                    # 计算因子
                    result = engine.evaluate_factor(factor_expr, df)
                    
                    if result:
                        col_r1, col_r2, col_r3 = st.columns(3)
                        col_r1.metric("IC均值", f"{result.get('ic_mean', 0):.4f}")
                        col_r2.metric("IR", f"{result.get('ir', 0):.3f}")
                        col_r3.metric("适应度", f"{result.get('fitness', 0):.4f}")
                        
                        # 展示因子值序列
                        factor_values = result.get("factor_values")
                        if factor_values is not None and len(factor_values) > 0:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                y=factor_values.tail(60).values,
                                mode="lines",
                                name=factor_expr,
                                line=dict(color="#3b82f6", width=1.5),
                            ))
                            fig.update_layout(
                                title=f"因子值序列 (最近60天)",
                                template="plotly_dark",
                                height=250,
                                margin=dict(l=40, r=20, t=40, b=40),
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        af_log(f"因子计算完成: {factor_expr} IC={result.get('ic_mean',0):.4f}", "factor", "ok")
                    else:
                        st.error("因子计算失败，请检查表达式语法")
                else:
                    st.error(f"获取 {stock_code} 数据失败")
            except Exception as e:
                st.error(f"计算出错: {e}")


# ═══════════════════════════════════════════════
# 底部
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#334155;font-size:11px;padding:8px;'>
    AlphaForge v4.0 — 自动进化量化因子挖掘系统 | 
    FactorEngine (50+算子) + GeneticProgrammer (GP进化) + FactorAnalyzer (IC/IR) + StrategyEnsemble (多因子融合) + IntelligenceCollector (情报采集) |
    仅供学习研究，不构成投资建议
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 自动刷新
# ═══════════════════════════════════════════════
if st.session_state.af_auto_refresh and st.session_state.af_running:
    time.sleep(2)
    st.rerun()
