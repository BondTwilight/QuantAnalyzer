"""
🧬 策略进化中心 v5.0 — AlphaForge 全新中文版

核心功能:
1. AlphaForge 自动因子挖掘引擎（遗传编程 + IC/IR评估）
2. 7阶段流水线可视化（数据→种子→GP进化→评估→组合→验证→更新）
3. 实时因子发现与IC/IR展示
4. 策略组合信号回测
5. 进化历史与最佳策略追踪
6. 策略情报采集系统（Alpha101 / GitHub / 论文 / 社交媒体 / Factors.Directory）

v5.0 更新:
- 全面中文化
- 优化UI布局和交互体验
- 新增使用提示和引导
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
    page_title="🧬 AlphaForge 进化中心 | QuantBrain",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 中文优化样式 ──
st.markdown("""<style>
/* 标题渐变 */
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
    display: inline-block; font-weight: 600;
}
.af-phase-badge.pending { background: #334155; color: #94a3b8; }
.af-phase-badge.running { background: rgba(59,130,246,0.15); color: #60a5fa; }
.af-phase-badge.completed { background: rgba(16,185,129,0.15); color: #34d399; }
.af-phase-badge.failed { background: rgba(239,68,68,0.15); color: #f87171; }

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
.af-factor-value.good { color: #34d399; }
.af-factor-value.mid { color: #fbbf24; }
.af-factor-value.bad { color: #f87171; }

/* 日志区域 */
.af-log {
    background: #0a0e1a; border: 1px solid #1e293b;
    border-radius: 8px; padding: 12px;
    height: 280px; overflow-y: auto;
    font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 11px;
}
.af-log-time { color: #64748b; margin-right: 6px; }
.af-log-phase { color: #3b82f6; margin-right: 6px; font-weight: 600; }
.af-log-msg { color: #e2e8f0; }
.af-log-ok { color: #34d399; }
.af-log-err { color: #f87171; }
.af-log-warn { color: #fbbf24; }

/* KPI 卡片 */
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

/* 连接箭头 */
.af-connector {
    text-align: center; color: #334155; font-size: 18px; padding: 0 4px;
}

/* 引擎状态面板 */
.engine-status-panel {
    background: linear-gradient(135deg, #1a1f35, #141929);
    border-radius: 12px;
    padding: 16px;
    border: 1px solid #1e293b;
}

/* 提示框 */
.tip-box {
    background: rgba(59,130,246,0.08);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 13px;
    color: #93c5fd;
    line-height: 1.7;
}
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 初始化 AlphaForge 引擎
# ═══════════════════════════════════════════════
@st.cache_resource
def init_alphaforge():
    """初始化 AlphaForge 引擎（带缓存，避免重复加载）"""
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

# Session state 初始化
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
    ("data_load", "📥", "加载数据", "获取最新 A 股行情"),
    ("seed_factors", "🌱", "种子因子", "生成已知有效因子池"),
    ("gp_evolve", "🧬", "GP 进化", "遗传编程搜索新因子"),
    ("factor_eval", "📊", "因子评估", "IC/IR 分析 + 分层回测"),
    ("ensemble", "🎯", "策略组合", "多因子加权融合"),
    ("validate", "✅", "回测验证", "组合策略历史验证"),
    ("update", "🚀", "更新策略", "持久化最佳策略"),
]

def af_log(msg: str, phase: str = "", level: str = "info"):
    """添加日志记录"""
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "phase": phase, "msg": msg, "level": level,
    }
    st.session_state.af_logs.append(entry)
    if len(st.session_state.af_logs) > 200:
        st.session_state.af_logs = st.session_state.af_logs[-200:]

def get_ic_color(ic: float) -> str:
    """根据 IC 值返回颜色等级"""
    if abs(ic) >= 0.05: return "good"
    elif abs(ic) >= 0.02: return "mid"
    return "bad"

def render_phase(icon: str, name: str, desc: str, status: str, progress: float = 0):
    """渲染单个流水线阶段"""
    cls = status if status in ("pending", "running", "completed", "failed") else "pending"
    badge_label = {"pending": "⏳ 等待", "running": "🔄 运行中", "completed": "✅ 完成", "failed": "❌ 失败"}.get(cls, cls)
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
st.markdown("### 自动因子挖掘 · 遗传编程进化 · 多因子组合策略")
st.markdown("---")

# 引擎加载检查
if not engines.get("loaded"):
    st.error(f"❌ AlphaForge 引擎加载失败: `{engines.get('error', '未知错误')}`")
    st.info("请确保已安装所有依赖: `numpy`, `pandas`, `scipy`, `scikit-learn`")
    st.stop()


# ═══════════════════════════════════════════════
# 主控制区 — 引擎状态 + 操作按钮
# ═══════════════════════════════════════════════
col_c1, col_c2, col_c3, col_c4 = st.columns([3, 1.5, 1, 1])

with col_c1:
    status_text = "🔄 进化运行中..." if st.session_state.af_running else "✅ 引擎就绪"
    status_color = "#fbbf24" if st.session_state.af_running else "#34d399"
    st.markdown(f"""
    <div class="engine-status-panel">
        <div style="font-size:12px;color:#64748b;margin-bottom:4px;">引擎状态</div>
        <div style="font-size:18px;font-weight:600;color:#f8fafc;">{status_text}</div>
        <div style="font-size:11px;color:#94a3b8;margin-top:6px;">
            ✅ 因子引擎 &nbsp;|&nbsp; ✅ 遗传编程 &nbsp;|&nbsp; ✅ 因子分析器 &nbsp;|&nbsp; ✅ 策略组合器 &nbsp;|&nbsp; ✅ 情报采集
        </div>
    </div>""", unsafe_allow_html=True)

with col_c2:
    with st.popover("⚙️ 进化参数"):
        gen_count = st.slider("进化代数", 1, 20, 3, help="每轮进化的代数越多，搜索越充分但耗时更长")
        pop_size = st.slider("种群大小", 10, 200, 50, help="每代的因子候选数量")
        min_ic = st.slider("IC 阈值", 0.0, 0.1, 0.02, 0.005, help="低于此阈值的因子将被淘汰")
        st.caption("💡 参数仅在下次启动时生效")

with col_c3:
    if st.button("🚀 启动进化", type="primary", use_container_width=True,
                 disabled=st.session_state.af_running):
        st.session_state.af_running = True
        st.session_state.af_auto_refresh = True
        af_log("🚀 AlphaForge 进化已启动！", "系统", "ok")
        
        def run_evolution():
            """后台执行进化流程"""
            try:
                scheduler = engines["scheduler"]
                
                def progress_cb(pct: float, msg: str):
                    af_log(f"[{pct:.0f}%] {msg}", "进化", "info")
                
                scheduler.set_progress_callback(progress_cb)
                task = scheduler.run_evolution(
                    task_type="full",
                    progress_cb=progress_cb,
                )
                
                st.session_state.af_last_result = {
                    "task": task.to_dict() if hasattr(task, 'to_dict') else str(task),
                    "timestamp": datetime.now().isoformat(),
                }
                
                best = scheduler.get_best_strategy()
                if best:
                    st.session_state.af_best_factors = best.get("factors", [])
                    st.session_state.af_ensemble_result = best
                
                st.session_state.af_running = False
                tested = getattr(task, 'factors_tested', '?')
                valid = getattr(task, 'factors_valid', '?')
                fit = getattr(task, 'best_fitness', '?')
                af_log(f"✅ 进化完成！测试: {tested} 因子, 有效: {valid}, 最佳适应度: {fit}", "系统", "ok")
                
            except Exception as e:
                st.session_state.af_running = False
                af_log(f"❌ 进化失败: {str(e)}", "系统", "err")
                import traceback
                af_log(traceback.format_exc()[:500], "系统", "err")
        
        thread = threading.Thread(target=run_evolution, daemon=True)
        thread.start()
        time.sleep(0.3)
        st.rerun()

with col_c4:
    if st.button("⏹️ 停止", use_container_width=True,
                 disabled=not st.session_state.af_running):
        st.session_state.af_running = False
        st.session_state.af_auto_refresh = False
        af_log("⏹️ 进化已手动停止", "系统", "warn")
        st.rerun()

auto_ref = st.toggle("🔄 自动刷新页面", value=st.session_state.af_auto_refresh, key="af_toggle")
if auto_ref != st.session_state.af_auto_refresh:
    st.session_state.af_auto_refresh = auto_ref
    st.rerun()


# ═══════════════════════════════════════════════
# 7 阶段流水线可视化
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🔄 进化流水线")
st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:12px;'>数据加载 → 种子因子生成 → GP 进化搜索 → IC/IR 评估 → 多因子融合 → 回测验证 → 持久化更新</div>", unsafe_allow_html=True)

# 计算各阶段状态 — 从 scheduler 实时获取（修复"永远卡在阶段1"的bug）
phase_status = {}

# 尝试从 EvolutionScheduler 获取真实运行状态
_real_phase_map = {
    "data_loading": "data_load",
    "seed_generation": "seed_factors", 
    "gp_evolution": "gp_evolve",
    "factor_evaluation": "factor_eval",
    "ensemble_building": "ensemble",
    "validation": "validate",
    "update_best": "update",
}

try:
    if engines.get("loaded"):
        sched_status = engines["scheduler"].get_status()
        is_running = sched_status.get("is_running", False)
        current_task = sched_status.get("current_task")
        
        if is_running and current_task:
            # 从正在运行的任务中获取真实阶段
            real_phase = current_task.get("current_phase", "")
            progress = current_task.get("progress_pct", 0)
            error_msg = current_task.get("error", "")
            
            # 映射到前端显示的阶段ID
            mapped_phase = _real_phase_map.get(real_phase, "")
            
            for i, (pid, _, _, _) in enumerate(PHASES_7):
                if pid == mapped_phase:
                    phase_status[pid] = ("running", progress)
                elif error_msg and pid == PHASES_7[i][0]:
                    # 如果有错误且还没到当前阶段，标记失败
                    pass
                else:
                    # 判断是否已完成
                    phase_order = ["data_load", "seed_factors", "gp_evolve", "factor_eval", "ensemble", "validate", "update"]
                    current_idx = phase_order.index(mapped_phase) if mapped_phase in phase_order else -1
                    my_idx = phase_order.index(pid) if pid in phase_order else -1
                    
                    if my_idx >= 0 and current_idx >= 0 and my_idx < current_idx:
                        phase_status[pid] = ("completed", 100)
                    else:
                        phase_status[pid] = ("pending", 0)
            
            # 如果有错误信息，在日志里显示
            if error_msg:
                if not any("❌" in l.get("msg","") and error_msg[:30] in l.get("msg","") 
                          for l in st.session_state.af_logs):
                    af_log(f"❌ 阶段异常: {error_msg}", "系统", "err")
        elif st.session_state.af_last_result:
            for pid, _, _, _ in PHASES_7:
                phase_status[pid] = ("completed", 100)
        else:
            for pid, _, _, _ in PHASES_7:
                phase_status[pid] = ("pending", 0)
    else:
        # 引擎未加载时的fallback（理论上不会到这里）
        if st.session_state.af_running:
            for i, (pid, _, _, _) in enumerate(PHASES_7):
                if i == 0:
                    phase_status[pid] = ("running", 50)
                else:
                    phase_status[pid] = ("pending", 0)
        elif st.session_state.af_last_result:
            for pid, _, _, _ in PHASES_7:
                phase_status[pid] = ("completed", 100)
        else:
            for pid, _, _, _ in PHASES_7:
                phase_status[pid] = ("pending", 0)
except Exception as e:
    # 最终兜底：如果状态读取也出错，用session_state判断
    if st.session_state.af_running:
        for i, (pid, _, _, _) in enumerate(PHASES_7):
            if i == 0:
                phase_status[pid] = ("running", 50)
            else:
                phase_status[pid] = ("pending", 0)
    elif st.session_state.af_last_result:
        for pid, _, _, _ in PHASES_7:
            phase_status[pid] = ("completed", 100)
    else:
        for pid, _, _, _ in PHASES_7:
            phase_status[pid] = ("pending", 0)

# 渲染 7 阶段 (上4 + 下3)
cols_top = st.columns(4)
cols_bot = st.columns(3)

for i, (pid, icon, name, desc) in enumerate(PHASES_7):
    status, pct = phase_status.get(pid, ("pending", 0))
    html = render_phase(icon, name, desc, status, pct)
    col = cols_top[i] if i < 4 else cols_bot[i - 4]
    col.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 🆕 策略情报采集面板（中文版）
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🕵️ 策略情报采集")
st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:12px;'>从全球顶级量化机构的公开策略中采集有效因子，注入 AlphaForge 进化引擎</div>", unsafe_allow_html=True)

# 初始化情报采集器
try:
    from core.alphaforge.intelligence_collector import IntelligenceCollector, INTELLIGENCE_SOURCES
    ic_collector = IntelligenceCollector()
    ic_stats = ic_collector.get_collected_stats()
    ic_loaded = True
except Exception as e:
    ic_loaded = False
    ic_stats = {"total": 0, "by_source": {}, "by_category": {}}

# 情报源概览卡片
if ic_loaded:
    ic_cols = st.columns(6)
    source_icons = {
        "worldquant_alpha101": ("🏛️", "WorldQuant\nAlpha101"),
        "factors_directory": ("🌐", "Factors\nDirectory"),
        "github_open_source": ("📦", "GitHub\n开源"),
        "academic_papers": ("📄", "学术\n论文"),
        "social_media": ("📱", "社交\n媒体"),
    }

    for i, (key, (icon, label)) in enumerate(source_icons.items()):
        count = ic_stats.get("by_source", {}).get(key, 0)
        source_info = INTELLIGENCE_SOURCES.get(key, {})
        
        with ic_cols[i]:
            has_data = count > 0
            color = "#34d399" if has_data else "#475569"
            border_color = "#10b981" if has_data else "#1e293b"
            bg_color = "rgba(16,185,129,0.06)" if has_data else "transparent"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#111827,#1a2235);
                        border:1px solid {border_color};border-radius:10px;padding:12px;text-align:center;">
                <div style="font-size:22px;">{icon}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;line-height:1.3;">{label}</div>
                <div style="font-size:20px;font-weight:800;color:{color};margin-top:4px;">{count}</div>
                <div style="font-size:10px;color:#334155;">{'✅ 已采集' if has_data else '待采集'}</div>
            </div>""", unsafe_allow_html=True)

    # 操作栏
    ic_col1, ic_col2, ic_col3 = st.columns([2, 2, 1])

    with ic_col1:
        if st.button("🔍 一键采集全部情报源", type="primary", use_container_width=True):
            with st.spinner("正在从 5 大源采集策略情报..."):
                try:
                    result = ic_collector.collect_all()
                    st.session_state.af_intelligence_result = result
                    st.success(f"✅ 采集完成！新增 **{result['total_new']}** 个因子（总计 **{result['total_collected']}**）")
                    af_log(f"情报采集完成: 新增 {result['total_new']} 因子", "情报", "ok")
                except Exception as e:
                    st.error(f"❌ 采集出错: {e}")
                    af_log(f"情报采集失败: {e}", "情报", "err")
                st.rerun()

    with ic_col2:
        categories = list(ic_stats.get("by_category", {}).keys())
        cat_names_cn = {
            "price_momentum": "价格动量",
            "volume_price": "量价关系",
            "volatility": "波动率",
            "reversal": "均值反转",
            "trend": "趋势跟踪",
            "statistical": "统计套利",
            "composite": "复合因子",
            "liquidity": "流动性",
        }
        cat_options = ["全部分类"] + [cat_names_cn.get(c, c) for c in categories]
        selected_cat = st.selectbox("分类筛选", cat_options, key="ic_cat_filter")
    
    with ic_col3:
        if st.button("💡 采集建议", use_container_width=True):
            try:
                rec = ic_collector.get_schedule_recommendation()
                st.session_state.af_ic_recommendations = rec
            except Exception:
                pass

    # 分类饼图 + 来源柱图
    cat_data = ic_stats.get("by_category", {})
    if cat_data:
        ic_chart1, ic_chart2 = st.columns(2)

        with ic_chart1:
            fig_cat = go.Figure(data=[go.Pie(
                labels=list(cat_data.keys()),
                values=list(cat_data.values()),
                hole=0.5,
                marker_colors=["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"],
                textinfo='label+percent',
                textfont_size=10,
            )])
            fig_cat.update_layout(
                title="📊 因子分类分布",
                template="plotly_dark",
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(font_size=9),
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        with ic_chart2:
            src_data = ic_stats.get("by_source", {})
            src_labels = {"worldquant_alpha101": "WQ Alpha101", "factors_directory": "F.Dir", 
                         "github_open_source": "GitHub", "academic_papers": "论文", 
                         "social_media": "社交"}
            if src_data:
                labels = [src_labels.get(k, k) for k in src_data.keys()]
                fig_src = go.Figure(data=[go.Bar(
                    x=labels,
                    y=list(src_data.values()),
                    marker_color=["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"][:len(src_data)],
                    text=[str(v) for v in src_data.values()],
                    textposition="auto",
                )])
                fig_src.update_layout(
                    title="📈 因子来源分布",
                    template="plotly_dark",
                    height=280,
                    margin=dict(l=20, r=20, t=40, b=20),
                    yaxis_title="因子数量",
                )
                st.plotly_chart(fig_src, use_container_width=True)

    # 已采集因子列表
    with st.expander("📋 已采集因子详情", expanded=False):
        collected = ic_collector.get_collected_factors()
        if collected:
            # 反转中文映射用于筛选
            cn_to_en = {v: k for k, v in cat_names_cn.items()}
            filter_category = cn_to_en.get(selected_cat, selected_cat) if selected_cat != "全部分类" else None
            
            if filter_category:
                collected = [f for f in collected if f.category == filter_category]

            # 分页
            page_size = 20
            max_page = max(1, len(collected) // page_size + 1)
            page = st.number_input("页码", min_value=1, max_value=max_page, value=1)
            start = (page - 1) * page_size
            page_factors = collected[start:start + page_size]

            st.markdown(f"<div style='color:#64748b;font-size:11px;margin-bottom:8px;'>显示第 **{start+1}-{min(start+page_size, len(collected))}** 条，共 **{len(collected)}** 个因子</div>", unsafe_allow_html=True)

            src_badge_map = {
                "worldquant_alpha101": '<span style="background:rgba(139,92,246,0.15);color:#a78bba;padding:1px 6px;border-radius:4px;font-size:10px;">🏛️ WQ</span>',
                "factors_directory": '<span style="background:rgba(6,182,212,0.15);color:#67e8f9;padding:1px 6px;border-radius:4px;font-size:10px;">🌐 FD</span>',
                "github_open_source": '<span style="background:rgba(16,185,129,0.15);color:#34d399;padding:1px 6px;border-radius:4px;font-size:10px;">📦 GH</span>',
                "academic_papers": '<span style="background:rgba(245,158,11,0.15);color:#fbbf24;padding:1px 6px;border-radius:4px;font-size:10px;">📄 论文</span>',
                "social_media": '<span style="background:rgba(236,72,153,0.15);color:#f472b6;padding:1px 6px;border-radius:4px;font-size:10px;">📱 社交</span>',
            }

            for f in page_factors:
                src_badge = src_badge_map.get(f.source, "❓")
                cat_cn = cat_names_cn.get(f.category, f.category)
                st.markdown(f"""
                <div class="af-factor-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            {src_badge}
                            <span style="font-size:10px;color:#64748b;margin-left:4px;">{cat_cn}</span>
                            <span style="font-size:12px;color:#e2e8f0;margin-left:6px;font-weight:600;">{f.name}</span>
                            <div class="af-factor-expr" style="margin-top:3px;">`{f.expression}`</div>
                        </div>
                        <div style="text-align:right;flex-shrink:0;margin-left:12px;">
                            <div style="font-size:10px;color:#64748b;">{f.description or ''}</div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("📭 暂无采集因子。点击上方「一键采集全部情报源」开始收集。")

    # 采集建议展示
    if "af_ic_recommendations" in st.session_state:
        rec = st.session_state.af_ic_recommendations
        with st.expander("💡 智能采集建议"):
            for r in rec.get("recommendations", []):
                action_icon = {"first_collect": "🆕 首次采集", "expand": "📈 扩充采集"}.get(r.get("action", ""), "📌 建议")
                st.markdown(f"{action_icon} **{r['name']}** （优先级 P{r['priority']})— {r['message']}")

else:
    st.warning("⚠️ 情报采集器加载失败，请确保 alphaforge 模块正确安装。")


# ═══════════════════════════════════════════════
# KPI 核心指标
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📊 本轮进化指标")

result = st.session_state.af_last_result
task_data = result.get("task", {}) if result else {}

k1, k2, k3, k4, k5 = st.columns(5)

k1.markdown(f"""<div class="af-kpi blue">
    <div class="af-kpi-label">🔬 测试因子数</div>
    <div class="af-kpi-value">{task_data.get('factors_tested', 0)}</div>
    <div class="af-kpi-sub">本轮探索的因子总数</div>
</div>""", unsafe_allow_html=True)

k2.markdown(f"""<div class="af-kpi green">
    <div class="af-kpi-label">✅ 有效因子</div>
    <div class="af-kpi-value">{task_data.get('factors_valid', 0)}</div>
    <div class="af-kpi-sub">通过 IC 阈值筛选</div>
</div>""", unsafe_allow_html=True)

k3.markdown(f"""<div class="af-kpi purple">
    <div class="af-kpi-label">🏆 最佳适应度</div>
    <div class="af-kpi-value">{task_data.get('best_fitness', 0):.4f}</div>
    <div class="af-kpi-sub">IC·IR·夏普 加权得分</div>
</div>""", unsafe_allow_html=True)

k4.markdown(f"""<div class="af-kpi orange">
    <div class="af-kpi-label">🎯 组合评分</div>
    <div class="af-kpi-value">{task_data.get('ensemble_score', 0):.1f}</div>
    <div class="af-kpi-sub">多因子融合效果</div>
</div>""", unsafe_allow_html=True)

k5.markdown(f"""<div class="af-kpi blue">
    <div class="af-kpi-label">⏱️ 耗时</div>
    <div class="af-kpi-value">{task_data.get('duration_seconds', 0):.1f}s</div>
    <div class="af-kpi-sub">端到端进化时间</div>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 有效因子列表 + 实时日志
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
                            IR={ir_val:.3f} | 适应度={fit:.3f}
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("🔍 暂无因子数据。点击「启动进化」让 AlphaForge 开始自动挖掘。")
    
    # 内置种子因子库
    with st.expander("📋 内置种子因子库 (20个)", expanded=False):
        seed_factor_info = [
            ("sma(close, 5) / sma(close, 20)", "短期/长期均线比 — 趋势跟踪"),
            ("ts_rank(close, 10)", "价格排名 — 动量因子"),
            ("ts_delta(close, 3) / close", "3日收益率 — 短期动量"),
            ("ts_std(returns, 20) * sqrt(252)", "年化波动率 — 风险度量"),
            ("ts_corr(close, volume, 10)", "量价相关性 — 成交量确认"),
            ("ts_skewness(returns, 20)", "收益偏度 — 尾部风险"),
            ("ts_min(low, 5) / close", "5日最低价比 — 支撑位"),
            ("ts_max(high, 10) / close", "10日最高价比 — 压力位"),
            ("(close-ts_min(low,20))/(ts_max(high,20)-ts_min(low,20)+1e-8)", "KDJ位置 — 超买超卖"),
            ("volume / ts_mean(volume, 20)", "量比 — 异常成交量"),
            ("ts_rank(returns, 5)", "收益排名 — 相对强弱"),
            ("ts_decay_linear(close, 10)", "线性衰减价格 — 近期权重"),
            ("ts_mean(returns,5)/ts_std(returns,20)", "简易夏普 — 风险调整收益"),
            ("ts_corr(close, ts_rank(volume,10), 5)", "价格-量排名相关 — 价量背离"),
            ("ts_sum(max(returns,0),20)/ts_sum(abs(returns),20)", "正收益占比 — 上涨动能"),
            ("ts_delta(volume,3)/ts_mean(volume,20)", "量变率 — 成交量趋势"),
            ("ts_argmax(close, 20) / 20", "近期高点位置 — 动能衰减"),
            ("ts_argmin(close, 20) / 20", "近期低点位置 — 抄底信号"),
            ("ts_regression(close, ts_step(5), 5, 1)", "5日线性斜率 — 价格趋势强度"),
            ("ts_zscore(close, 20)", "Z-Score标准化 — 统计偏离"),
        ]
        for i, (expr, desc) in enumerate(seed_factor_info):
            st.code(f"{i+1:2d}. {expr}", language=None)
            st.caption(desc, unsafe_allow_html=False)

with col_right:
    st.markdown("### 📜 实时运行日志")
    
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
        log_html += '<div style="color:#475569;padding:20px;text-align:center;">等待启动进化...</div>'
    log_html += '</div>'
    st.markdown(log_html, unsafe_allow_html=True)
    
    if st.button("🗑️ 清空日志"):
        st.session_state.af_logs = []
        st.rerun()


# ═══════════════════════════════════════════════
# 🎯 最佳组合策略结果
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
            <div style="font-size:11px;color:#94a3b8;">多因子加权融合</div>
        </div>""", unsafe_allow_html=True)
    
    with col_e2:
        trades = ensemble.get("total_trades", 0)
        wr = ensemble.get("win_rate", 0)
        wr_color = "#34d399" if wr > 0.5 else "#f87171"
        st.markdown(f"""<div class="af-strategy">
            <div style="font-size:11px;color:#64748b;">交易统计</div>
            <div style="font-size:18px;font-weight:700;color:#f8fafc;">{trades} 笔</div>
            <div style="font-size:14px;font-weight:600;color:{wr_color};">胜率 {wr:.1%}</div>
        </div>""", unsafe_allow_html=True)
    
    with col_e3:
        sharpe = ensemble.get("sharpe_ratio", 0)
        ret = ensemble.get("annual_return", 0)
        ret_color = "#34d399" if ret > 0 else "#f87171"
        st.markdown(f"""<div class="af-strategy">
            <div style="font-size:11px;color:#64748b;">收益指标</div>
            <div style="font-size:18px;font-weight:700;color:{ret_color};">{ret:.1%}</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8;">夏普比率 {sharpe:.2f}</div>
        </div>""", unsafe_allow_html=True)
    
    with col_e4:
        dd = abs(ensemble.get("max_drawdown", 0))
        pf = ensemble.get("profit_factor", 0)
        st.markdown(f"""<div class="af-strategy">
            <div style="font-size:11px;color:#64748b;">风险控制</div>
            <div style="font-size:18px;font-weight:700;color:#f87171;">最大回撤 {dd:.1%}</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8;">盈亏比 {pf:.2f}</div>
        </div>""", unsafe_allow_html=True)
    
    # 策略因子构成
    factors_in_ensemble = ensemble.get("factors", [])
    if factors_in_ensemble:
        with st.expander("📋 策略因子构成详情"):
            for i, f in enumerate(factors_in_ensemble):
                weight = f.get("weight", 0)
                ic = f.get("ic_mean", 0)
                bar_width = min(weight * 100, 100)
                bar_color = "#3b82f6" if weight > 0 else "#ef4444"
                st.markdown(f"""
                **{i+1}.** `{f.get('expression','?')}`  
                权重: **{weight:.3f}** | IC: *{ic:.4f}*  
                <div style="background:#1e293b;border-radius:4px;height:6px;width:{bar_width}%;margin-top:2px;"></div>
                """, unsafe_allow_html=True)
    
    # 交易信号明细
    signals = ensemble.get("signals", [])
    if signals:
        with st.expander("📊 最近交易信号（前50条）"):
            df_signals = pd.DataFrame(signals[:50])
            if not df_signals.empty:
                # 重命名列为中文
                rename_map = {}
                df_signals_renamed = df_signals.rename(columns=rename_map)
                st.dataframe(df_signals_renamed, use_container_width=True, hide_index=True)

else:
    st.markdown("""
    <div class="tip-box">
        💡 <b>暂无组合策略</b><br>
        运行一轮完整进化后，系统将自动生成最优多因子组合策略，
        包含权重分配、交易信号、回测结果等详细信息。
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 📈 进化历史记录
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📈 进化历史")

try:
    scheduler = engines["scheduler"]
    history = scheduler.get_evolution_history(limit=10)
    
    if history:
        hist_data = []
        for h in history:
            status_icon = {"completed": "✅ 完成", "failed": "❌ 失败", "running": "🔄 运行中"}.get(h.get("status","?"), "❓ 未知")
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
        
        # 适应度变化趋势图
        if len(history) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=[h.get("best_fitness", 0) for h in history],
                mode="lines+markers",
                name="最佳适应度",
                line=dict(color="#3b82f6", width=2.5),
                marker=dict(size=10, color="#a855f7"),
                fill='tozeroy',
                fillcolor='rgba(59,130,246,0.1)',
            ))
            fig.update_layout(
                title="📈 适应度进化趋势",
                xaxis_title="进化轮次",
                yaxis_title="Fitness 得分",
                template="plotly_dark",
                height=300,
                margin=dict(l=40, r=20, t=40, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 暂无进化历史。完成第一轮进化后将在此显示记录。")
except Exception as e:
    st.warning(f"读取历史失败: {e}")


# ═══════════════════════════════════════════════
# 🔬 快速因子计算实验室
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🔬 因子计算实验室")

with st.form("factor_calc_form"):
    col_fc1, col_fc2, col_fc3 = st.columns([2, 1, 1])
    
    with col_fc1:
        factor_expr = st.text_input(
            "✏️ 输入因子表达式",
            value="sma(close, 5) / sma(close, 20)",
            placeholder="例如: ts_rank(close, 10)、ts_delta(close, 3) / close",
            help="支持所有 AlphaForge 算子: sma, ema, rsi, macd, ts_rank, ts_delta, ts_corr, ts_std 等"
        )
    
    with col_fc2:
        stock_code = st.text_input("📌 股票代码", value="000001.SZ", help="需带交易所后缀，如 .SZ / .SH")
    
    with col_fc3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🧪 计算因子", type="primary", use_container_width=True)
    
    if submitted and factor_expr:
        with st.spinner("正在计算因子值..."):
            try:
                from data.fetcher import get_stock_data
                engine = engines["factor_engine"]
                
                df = get_stock_data(stock_code, period="2y")
                if df is not None and not df.empty:
                    result = engine.evaluate_factor(factor_expr, df)
                    
                    if result:
                        col_r1, col_r2, col_r3 = st.columns(3)
                        col_r1.metric("📊 IC 均值", f"{result.get('ic_mean', 0):.4f}")
                        col_r2.metric("📈 IR 比率", f"{result.get('ir', 0):.3f}")
                        col_r3.metric("🏆 适应度", f"{result.get('fitness', 0):.4f}")
                        
                        # 因子值序列图
                        factor_values = result.get("factor_values")
                        if factor_values is not None and len(factor_values) > 0:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                y=factor_values.tail(60).values,
                                mode="lines",
                                name=factor_expr,
                                line=dict(color="#3b82f6", width=1.8),
                                fill='tozeroy',
                                fillcolor='rgba(59,130,246,0.08)',
                            ))
                            fig.update_layout(
                                title=f"📉 因子值序列（最近 60 天）",
                                template="plotly_dark",
                                height=260,
                                margin=dict(l=40, r=20, t=40, b=40),
                                yaxis_title="因子值",
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        af_log(f"因子计算成功: {factor_expr}, IC={result.get('ic_mean',0):.4f}", "实验室", "ok")
                    else:
                        st.error("❌ 因子计算失败，请检查表达式语法是否正确")
                else:
                    st.error(f"❌ 无法获取股票 [{stock_code}] 的数据")
            except Exception as e:
                st.error(f"❌ 计算出错: {e}")


# ═══════════════════════════════════════════════
# 📡 数据源总览面板（Phase 3 新增）
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📡 数据源总览")
st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:12px;'>多源聚合策略（参考易涨EasyUp/OpenClaw）: AkShare(主) → BaoStock(备) → 模拟数据(兜底)</div>", unsafe_allow_html=True)

try:
    from core.multi_data_source import MultiDataSource, _is_cloud_env
    
    # 数据源状态卡片
    ds_col1, ds_col2, ds_col3 = st.columns(3)
    
    with ds_col1:
        # 实时行情概览
        with st.expander("📊 A股实时行情", expanded=False):
            if st.button("🔄 刷新行情", key="refresh_rt", use_container_width=True):
                with st.spinner("获取实时行情..."):
                    try:
                        overview = MultiDataSource.get_market_overview()
                        st.session_state.af_market_overview = overview
                    except Exception as e:
                        st.warning(f"获取失败: {e}")
            
            ov = st.session_state.get("af_market_overview", {})
            if ov:
                indices = ov.get("indices", [])
                for idx in indices[:6]:
                    pct = idx.get("pct_change", 0)
                    color = "#f87171" if isinstance(pct, (int,float)) and pct > 0 else "#34d399"
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e293b;">
                        <span style="color:#94a3b8;">{idx.get('name','')}</span>
                        <span>
                            <span style="color:#e2e8f0;font-weight:600;">{idx.get('price','-')}</span>
                            <span style="color:{color};font-size:11px;margin-left:4px;">{str(pct) if pct else '-'}</span>
                        </span>
                    </div>""", unsafe_allow_html=True)
                
                stats = ov.get("market_stats", {})
                st.caption(f"总计 {stats.get('total',0)} 只 | 📈{stats.get('up_count',0)} 📉{stats.get('down_count',0)} | 涨停≈{stats.get('limit_up',0)}")
                
                # 涨幅前5
                top_g = ov.get("top_gainers", [])
                if top_g:
                    st.markdown("**🔥 涨幅榜 Top 5**")
                    for g in top_g[:5]:
                        st.markdown(f"`{g.get('代码','')}` {g.get('名称','')} **+{g.get('涨跌幅',0):.1f}%**")
    
    with ds_col2:
        # ETF / 基金 / 期货
        with st.expander("📈 ETF / 基金 / 期货", expanded=False):
            etab = st.tabs(["ETF", "基金排行", "期货"])
            with etab[0]:
                if st.button("刷新ETF列表", key="etf_refresh"):
                    try:
                        df_etf = MultiDataSource.get_etf_list()
                        st.session_state.af_etf_data = df_etf.head(10)
                    except Exception as e:
                        st.error(f"ETF获取失败: {e}")
                
                etf_df = st.session_state.get("af_etf_data")
                if etf_df is not None and not etf_df.empty:
                    st.dataframe(etf_df, use_container_width=True, hide_index=True)
                else:
                    st.info("点击「刷新ETF列表」获取最新数据")
            
            with etab[1]:
                cat_options_fund = ["股票型", "混合型", "债券型", "指数型"]
                sel_cat = st.selectbox("基金类型", cat_options_fund, key="fund_cat_sel")
                if st.button(f"刷新{sel_cat}排行", key="fund_rank_btn"):
                    try:
                        df_fund = MultiDataSource.get_fund_rank(sel_cat)
                        st.session_state.af_fund_data = df_fund.head(10)
                    except Exception as e:
                        st.error(f"基金排行失败: {e}")
                
                fund_df = st.session_state.get("af_fund_data")
                if fund_df is not None and not fund_df.empty:
                    st.dataframe(fund_df, use_container_width=True, hide_index=True)
            
            with etab[2]:
                if st.button("刷新期货列表", key="future_btn"):
                    try:
                        df_future = MultiDataSource.get_future_list()
                        st.session_state.af_future_data = df_future.head(10)
                    except Exception as e:
                        st.error(f"期货失败: {e}")
                
                fut_df = st.session_state.get("af_future_data")
                if fut_df is not None and not fut_df.empty:
                    st.dataframe(fut_df, use_container_width=True, hide_index=True)

    with ds_col3:
        # 宏观经济 + 市场情绪
        with st.expander("🌍 宏观经济 + 市场情绪", expanded=False):
            macro_tab = st.tabs(["宏观指标", "市场情绪"])
            
            with macro_tab[0]:
                macro_buttons = st.columns(3)
                with macro_buttons[0]:
                    if st.button("GDP", use_container_width=True, key="gdp_btn"):
                        try:
                            gdp = MultiDataSource.get_gdp_data()
                            st.session_state.af_gdp = gdp
                        except: pass
                with macro_buttons[1]:
                    if st.button("CPI/PPI", use_container_width=True, key="cpi_btn"):
                        try:
                            cpi = MultiDataSource.get_cpi_data()
                            ppi = MultiDataSource.get_ppi_data()
                            st.session_state.af_cpi = cpi
                            st.session_state.af_ppi = ppi
                        except: pass
                with macro_buttons[2]:
                    if st.button("Shibor/M2", use_container_width=True, key="shibor_btn"):
                        try:
                            shibor = MultiDataSource.get_shibor_rates()
                            m2 = MultiDataSource.get_money_supply()
                            st.session_state.af_shibor = shibor
                            st.session_state.af_m2 = m2
                        except: pass
                
                for key in ["af_gdp", "af_cpi", "af_ppi", "af_shibor", "af_m2"]:
                    data = st.session_state.get(key)
                    if data is not None and hasattr(data, 'head'):
                        st.dataframe(data.head(5), use_container_width=True, hide_index=True)
            
            with macro_tab[1]:
                if st.button("🔄 刷新市场情绪", key="sentiment_btn"):
                    try:
                        sent = MultiDataSource.get_market_sentiment()
                        st.session_state.af_sentiment = sent
                    except: pass
                
                sent_data = st.session_state.get("af_sentiment", {})
                if sent_data:
                    s_cols = st.columns(4)
                    s_cols[0].metric("股票总数", f"{sent_data.get('total_stocks', 0)}")
                    up_n = sent_data.get('up_count', 0)
                    down_n = sent_data.get('down_count', 0)
                    s_cols[1].metric("上涨/下跌", f"{up_n}/{down_n}", delta=f"比:{sent_data.get('advance_decline_ratio',0):.2f}")
                    s_cols[2].metric("平均涨跌%", f"{sent_data.get('avg_pct_change', 0):.2f}%")
                    adr = sent_data.get('advance_decline_ratio', 0)
                    color = "normal" if adr > 1 else "inverse"
                    s_cols[3].metric("涨跌比", f"{adr:.2f}", delta_color=color)
                    
                    # 板块资金流向
                    if st.button("板块资金流", key="sector_flow_btn"):
                        try:
                            sf = MultiDataSource.get_sector_money_flow()
                            st.session_state.af_sector_flow = sf
                        except: pass
                    
                    sf_data = st.session_state.get("af_sector_flow")
                    if sf_data is not None and not sf_data.empty:
                        st.dataframe(sf_data.head(10), use_container_width=True, hide_index=True)

except Exception as e:
    st.warning(f"⚠️ 数据源模块加载异常: {e}")


# ═══════════════════════════════════════════════
# 🔔 通知设置面板（Phase 3 新增）
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🔔 通知设置")

try:
    from core.notifications import get_notification_status, init_notifications, notify
    
    # 获取当前状态
    notif_status = get_notification_status()
    
    nc1, nc2, nc3 = st.columns([2, 2, 1])
    
    with nc1:
        st.markdown("**已注册的通知渠道**")
        for name, info in notif_status.items():
            avail_icon = "✅" if info["available"] else "⚪"
            enabled_icon = "🟢" if info["enabled"] else "🔴"
            label_map = {"log": "系统日志", "feishu": "飞书机器人", "wechat": "微信推送", "email": "邮件通知"}
            cn_name = label_map.get(name, name)
            st.markdown(f"{avail_icon} {enabled_icon} **{cn_name}** — {'可用' if info['available'] else '未配置'}")
        
        st.info("💡 配置方式：设置环境变量 `FEISHU_WEBHOOK_URL` / `WECHAT_SENDKEY` / `SMTP_HOST` 等，或使用下方表单快速测试。")

    with nc2:
        with st.form("notif_test_form"):
            st.markdown("**🧪 发送测试通知**")
            test_title = st.text_input("标题", value="QuantBrain 测试消息")
            test_content = st.text_area("内容", value="这是一条来自 AlphaForge 进化中心的测试通知 ✨")
            test_priority = st.selectbox(
                "优先级",
                options=["info", "success", "warning", "error", "critical"],
                format_func=lambda x: {"info": "ℹ️ 信息", "success": "✅ 成功", "warning": "⚠️ 警告", "error": "❌ 错误", "critical": "🔥 严重"}[x],
            )
            submitted_notif = st.form_submit_button("📤 发送测试", type="primary", use_container_width=True)
            
            if submitted_notif:
                result = notify.send(test_title, test_content, priority=test_priority)
                success_channels = [k for k, v in result.items() if v is True]
                failed_channels = [k for k, v in result.items() if v is False]
                
                if success_channels:
                    st.success(f"✅ 已发送至: {', '.join(success_channels)}")
                if failed_channels:
                    st.warning(f"⏭️ 跳过: {', '.join(failed_channels)}")
    
    with nc3:
        # 快速统计
        total_logs = len(st.session_state.get("af_logs", []))
        total_factors = len(st.session_state.get("af_best_factors", []))
        has_result = st.session_state.get("af_last_result") is not None
        
        st.metric("运行日志数", f"{total_logs}")
        st.metric("有效因子数", f"{total_factors}")
        st.metric("进化完成", f"{'是' if has_result else '否'}")
        
        if st.button("🧹 清理缓存", use_container_width=True):
            st.cache_resource.clear()

except Exception as e:
    st.info(f"ℹ️ 通知模块未启用（需配置环境变量）。当前仅使用日志记录。错误: {e}")



# ═══════════════════════════════════════════════
# 底部信息
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#1e293b;font-size:11px;padding:10px;line-height:1.8;'>
    🧬 <b>QuantBrain AlphaForge v5.0</b> — 智能量化因子自动进化系统<br>
    <span style="color:#0f172a;">
    因子引擎 (50+ 算子) · 遗传编程 (GP v2) · 因子分析器 (IC/IR) · 策略组合器 (多因子融合) · 情报采集器 (5大源)<br>
    ⚠️ 仅供学习研究使用，不构成任何投资建议 · 投资有风险，入市需谨慎
    </span>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 自动刷新
# ═══════════════════════════════════════════════
if st.session_state.af_auto_refresh and st.session_state.af_running:
    time.sleep(2)
    st.rerun()
