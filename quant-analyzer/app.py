"""
QuantBrain — 智能量化策略进化平台

核心功能：
🧬 AlphaForge 自动因子挖掘引擎（遗传编程 + IC/IR评估）
📡 策略情报采集系统（5大情报源自动同步）
🔬 因子实验室（交互式因子研究与可视化）
📊 策略回测与归因分析
📚 量化策略知识库
"""

import streamlit as st
from pathlib import Path
import sys

# ── 项目路径 ──
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from config import PAGE_CONFIG

# ── 页面配置 ──
st.set_page_config(**PAGE_CONFIG)

# ── 暗色专业主题（中文优化版） ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700;900&display=swap');

.stApp {
    background: #0a0e17;
    font-family: 'Inter', 'Noto Sans SC', -apple-system, 'Microsoft YaHei', sans-serif;
}
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: rgba(10,14,23,0.95);
    backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(30,41,59,0.5);
}

/* 侧边栏 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1320 0%, #0a0e17 100%);
    border-right: 1px solid #1a2235;
}
[data-testid="stSidebar"] [class*="css-1vbd490"] {
    background: transparent !important;
}
[data-testid="stSidebar"] .css-17lntkn {
    font-family: 'Noto Sans SC', sans-serif !important;
}

/* 主标题区域 */
.hero-section {
    text-align: center;
    padding: 36px 20px 24px;
    position: relative;
}
.hero-title {
    font-size: 44px;
    font-weight: 900;
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
}
.hero-subtitle {
    color: #94a3b8;
    font-size: 16px;
    letter-spacing: 3px;
    font-weight: 500;
}
.hero-desc {
    color: #475569;
    font-size: 13px;
    margin-top: 10px;
    line-height: 1.7;
}

/* 功能卡片 */
.feature-card {
    background: linear-gradient(135deg, #111827 0%, #1a2235 100%);
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 22px 18px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
    height: 100%;
}
.feature-card:hover {
    border-color: #334155;
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.3);
}
.feature-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.feature-card.blue::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.feature-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.feature-card.green::before { background: linear-gradient(90deg, #10b981, #34d399); }
.feature-card.orange::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.feature-card.pink::before { background: linear-gradient(90deg, #ec4899, #f472b6); }

.feature-icon {
    font-size: 28px;
    margin-bottom: 8px;
    display: block;
}
.feature-label {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 6px;
}
.feature-value {
    color: #f1f5f9;
    font-size: 22px;
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: 4px;
}
.feature-desc {
    color: #475569;
    font-size: 11.5px;
    line-height: 1.5;
}

/* 入口按钮 */
.entry-btn {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 50%, #3b82f6 100%);
    background-size: 200% 200%;
    animation: gradient-shift 3s ease infinite;
    border: none;
    border-radius: 12px;
    padding: 16px 32px;
    font-size: 15px;
    font-weight: 700;
    color: white !important;
    cursor: pointer;
    transition: all 0.3s ease;
    letter-spacing: 1px;
    width: 100%;
}
.entry-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(59,130,246,0.4);
}

@keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* 使用流程步骤 */
.flow-step {
    background: linear-gradient(135deg, rgba(17,24,39,0.6), rgba(26,34,53,0.6));
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    transition: all 0.3s;
}
.flow-step:hover {
    border-color: #3b82f6;
    background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(26,34,53,0.9));
}
.step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px; height: 32px;
    border-radius: 50%;
    font-size: 14px;
    font-weight: 800;
    margin-bottom: 8px;
}
.step-num.blue { background: rgba(59,130,246,0.2); color: #60a5fa; }
.step-num.purple { background: rgba(139,92,246,0.2); color: #a78bfa; }
.step-num.green { background: rgba(16,185,129,0.2); color: #34d399; }
.step-num.orange { background: rgba(245,158,11,0.2); color: #fbbf24; }

/* 统计数字 */
.stat-row {
    display: flex;
    justify-content: center;
    gap: 40px;
    flex-wrap: wrap;
    padding: 20px 0;
}
.stat-item {
    text-align: center;
}
.stat-num {
    font-size: 28px;
    font-weight: 900;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.stat-label {
    color: #64748b;
    font-size: 12px;
    margin-top: 2px;
}

/* 提示框 */
.info-tip {
    background: rgba(59,130,246,0.08);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 12.5px;
    color: #93c5fd;
    line-height: 1.6;
}

/* 分隔线 */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e293b, transparent);
    margin: 28px 0;
    border: none;
}

/* 页脚 */
.footer-note {
    text-align: center;
    color: #1e293b;
    font-size: 11px;
    line-height: 1.8;
    padding: 16px;
    margin-top: 20px;
}
</style>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# 首页主界面
# ════════════════════════════════════════════════════════

def main():
    
    # ── Hero 区域 ──
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">🧬 QuantBrain</div>
        <div class="hero-subtitle">智能量化策略进化平台</div>
        <div class="hero-desc">
            从公开策略中学习 · 自动挖掘有效因子 · 遗传编程持续进化<br>
            <span style="color:#334155;">Powered by Genetic Programming + LLM Intelligence</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── 核心数据统计 ──
    st.markdown("""
    <div class="stat-row">
        <div class="stat-item">
            <div class="stat-num">187+</div>
            <div class="stat-label">内置因子库</div>
        </div>
        <div class="stat-item">
            <div class="stat-num">5</div>
            <div class="stat-label">情报采集源</div>
        </div>
        <div class="stat-item">
            <div class="stat-num">GP v2</div>
            <div class="stat-label">遗传编程引擎</div>
        </div>
        <div class="stat-item">
            <div class="stat-num">Auto</div>
            <div class="stat-label">每日自动进化</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 五大功能模块 ──
    st.markdown("### ✨ 核心功能")
    st.markdown('<div style="font-size:12px;color:#475569;margin-bottom:14px;">点击下方卡片进入对应功能模块</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card blue">
            <span class="feature-icon">🧬</span>
            <div class="feature-label">🧬 进化引擎</div>
            <div class="feature-value">AlphaForge</div>
            <div class="feature-desc">遗传编程自动挖掘因子，IC/IR评估筛选，多因子融合生成策略组合</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card purple">
            <span class="feature-icon">🔬</span>
            <div class="feature-label">🔬 因子实验室</div>
            <div class="feature-value">Factor Lab</div>
            <div class="feature-desc">交互式因子计算与可视化，实时IC分析，自定义算子组合研究</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card green">
            <span class="feature-icon">🕵️</span>
            <div class="feature-label">🕵️ 情报采集</div>
            <div class="feature-value">5 大源</div>
            <div class="feature-desc">Alpha101 / GitHub开源 / 学术论文 / Factors.Directory / 社交媒体</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    col4, col5, col6 = st.columns(3)

    with col4:
        st.markdown("""
        <div class="feature-card orange">
            <span class="feature-icon">📊</span>
            <div class="feature-label">📊 回测归因</div>
            <div class="feature-value">Backtest</div>
            <div class="feature-desc">多维度回测验证，Brinson归因分析，风险指标全面评估</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("""
        <div class="feature-card pink">
            <span class="feature-icon">📚</span>
            <div class="feature-label">📚 知识库</div>
            <div class="feature-value">Knowledge</div>
            <div class="feature-desc">量化策略体系整理，经典因子解析，实战经验沉淀</div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown("""
        <div class="feature-card blue">
            <span class="feature-icon">⚙️</span>
            <div class="feature-label">⚙️ 参数配置</div>
            <div class="feature-value">Config</div>
            <div class="feature-desc">股票池管理、AI模型选择、进化参数调优、回测设置</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── 快速入口按钮 ──
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 进入 AlphaForge 进化中心", type="primary", use_container_width=True,
                     key="main_entry_btn"):
            st.switch_page("pages/evolution_center.py")

    st.markdown("")
    
    # ── 次级入口按钮 ──
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        if st.button("🔬 因子实验室", use_container_width=True, key="factor_lab_btn"):
            st.switch_page("pages/factor_lab.py")
    with ec2:
        if st.button("📚 策略知识库", use_container_width=True, key="knowledge_btn"):
            st.switch_page("pages/strategy_knowledge.py")
    with ec3:
        if st.button("⚙️ 参数配置", use_container_width=True, key="config_btn"):
            st.switch_page("pages/config.py")

    # ── 使用流程指引 ──
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown("### 📖 使用流程")
    
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    
    with fcol1:
        st.markdown("""
        <div class="flow-step">
            <div class="step-num blue">1</div>
            <div style="font-size:13px;font-weight:600;color:#e2e8f0;">采集情报</div>
            <div style="font-size:11px;color:#64748b;margin-top:4px;">从5大源自动采集<br>已知有效因子</div>
        </div>
        """, unsafe_allow_html=True)

    with fcol2:
        st.markdown("""
        <div class="flow-step">
            <div class="step-num purple">2</div>
            <div style="font-size:13px;font-weight:600;color:#e2e8f0;">GP 进化</div>
            <div style="font-size:11px;color:#64748b;margin-top:4px;">遗传编程搜索<br>新因子表达式</div>
        </div>
        """, unsafe_allow_html=True)

    with fcol3:
        st.markdown("""
        <div class="flow-step">
            <div class="step-num green">3</div>
            <div style="font-size:13px;font-weight:600;color:#e2e8f0;">评估组合</div>
            <div style="font-size:11px;color:#64748b;margin-top:4px;">IC/IR筛选最优<br>多因子加权融合</div>
        </div>
        """, unsafe_allow_html=True)

    with fcol4:
        st.markdown("""
        <div class="flow-step">
            <div class="step-num orange">4</div>
            <div style="font-size:13px;font-weight:600;color:#e2e8f0;">验证更新</div>
            <div style="font-size:11px;color:#64748b;margin-top:4px;">历史回测验证<br>更新最佳策略</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 提示信息 ──
    st.markdown("")
    st.markdown("""
    <div class="info-tip">
        💡 <b>新手推荐</b>：首次使用请先进入「进化中心」，点击「一键采集所有情报源」获取初始因子池，
        然后点击「启动进化」让 AlphaForge 自动搜索最优因子组合。
        整个过程全自动运行，通常在 30 秒内完成一轮进化。
    </div>
    """, unsafe_allow_html=True)

    # ── 页脚 ──
    st.markdown(f"""
    <div class="footer-note">
        QuantBrain 智能量化策略进化平台 · Powered by Genetic Programming & GLM AI<br>
        🧬 AlphaForge Engine — 因子自动挖掘 · 策略自动进化 · 每日自我迭代<br>
        <span style="color:#0f172a;">仅供学习研究使用 · 不构成任何投资建议 · 投资有风险 · 入市需谨慎</span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
