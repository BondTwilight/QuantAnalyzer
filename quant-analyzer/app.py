"""
QuantBrain — AlphaForge 全自动进化引擎

核心定位：抓取策略 → 学习提取因子 → 遗传编程自动进化 → 生成新策略/新因子
"""

import streamlit as st
import sys
from pathlib import Path

# ── 项目路径 ──
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from config import PAGE_CONFIG

# ── 页面配置 ──
st.set_page_config(**PAGE_CONFIG)

# ── 暗色专业主题 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.stApp {
    background: #0a0e17;
    font-family: 'Inter', -apple-system, 'Microsoft YaHei', sans-serif;
}
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: rgba(10,14,23,0.9);
    backdrop-filter: blur(20px);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1320 0%, #0a0e17 100%);
    border-right: 1px solid #1a2235;
}

/* KPI 卡片 */
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
.kpi-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.kpi-card.orange::before { background: linear-gradient(90deg, #f59e0b, #fbb24); }
.kpi-label { color: #64748b; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
.kpi-value { color: #f1f5f9; font-size: 24px; font-weight: 800; line-height: 1.2; }
.kpi-sub { color: #475569; font-size: 11px; margin-top: 4px; }

/* 流水线阶段 */
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

/* Badge */
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.badge-green { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.badge-red { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
.badge-blue { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
.badge-purple { background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }

/* Section Title */
.section-title {
    font-size: 16px; font-weight: 700; color: #e2e8f0;
    margin: 24px 0 12px; display: flex; align-items: center; gap: 8px;
}
.section-title::before {
    content: ''; width: 4px; height: 20px;
    background: linear-gradient(180deg, #3b82f6, #8b5cf6);
    border-radius: 2px;
}

/* Alert */
.alert-box {
    padding: 14px 18px; border-radius: 10px; margin-bottom: 12px;
    font-size: 13px; border-left: 4px solid;
}
.alert-danger { background: rgba(239,68,68,0.08); border-color: #ef4444; color: #fca5a5; }
.alert-warning { background: rgba(245,158,11,0.08); border-color: #f59e0b; color: #fcd34d; }
.alert-info { background: rgba(59,130,246,0.08); border-color: #3b82f6; color: #93c5fd; }
.alert-success { background: rgba(16,185,129,0.08); border-color: #10b981; color: #6ee7b7; }

/* Button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    border: none; border-radius: 8px; font-weight: 600; transition: all 0.2s;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #60a5fa, #3b82f6);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59,130,246,0.3);
}

/* Table */
.dataframe th { background: #111827 !important; color: #94a3b8 !important; font-weight: 600 !important; font-size: 12px !important; border-bottom: 2px solid #1e293b !important; }
.dataframe td { color: #cbd5e1 !important; font-size: 13px !important; border-bottom: 1px solid #1e293b !important; }
.dataframe tr:hover { background: rgba(59,130,246,0.05) !important; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a0e17; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════
# 主入口 — 直接跳转到 AlphaForge 进化中心
# ════════════════════════════════════════════

def main():
    st.markdown("""
    <div style="text-align:center;padding:40px 20px 20px;">
        <div style="font-size:42px;font-weight:900;background:linear-gradient(135deg,#3b82f6,#8b5cf6,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px;">
            🧬 QuantBrain
        </div>
        <div style="color:#64748b;font-size:16px;letter-spacing:2px;">
            AlphaForge 全自动进化引擎
        </div>
        <div style="color:#475569;font-size:13px;margin-top:8px;">
            抓取策略 · 学习提取因子 · 遗传编程进化 · 自动生成新策略
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 核心功能卡片
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="kpi-card blue">
            <div class="kpi-label">📡 策略情报采集</div>
            <div class="kpi-value">5 大源</div>
            <div class="kpi-sub">Alpha101 / GitHub / 论文 / 社交媒体 / Factors.Directory</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="kpi-card purple">
            <div class="kpi-label">🧬 因子进化</div>
            <div class="kpi-value">GP v2.0</div>
            <div class="kpi-sub">遗传编程 + 算子感知变异 + Warm Start</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="kpi-card green">
            <div class="kpi-label">🎯 策略组合</div>
            <div class="kpi-value">Auto</div>
            <div class="kpi-sub">多因子融合 IC加权 + 风险控制 + 回测验证</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 进入按钮
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 进入 AlphaForge 进化中心", type="primary", use_container_width=True):
            st.switch_page("pages/evolution_center.py")

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;color:#334155;font-size:11px;line-height:1.6;padding:10px;">
        QuantBrain AlphaForge Engine · Powered by Genetic Programming & LLM<br>
        仅供学习研究 · 不构成投资建议
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
