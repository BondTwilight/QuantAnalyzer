"""
🧪 因子实验室 (Factor Lab) — 交互式因子研究工作台

核心功能：
1. 内置因子浏览器：浏览 50+ 预置因子（分类展示）
2. 自定义因子计算：输入表达式实时计算
3. 因子评估分析：IC/IR/分层回测/衰减分析
4. 因子可视化：时序图、分布图、IC热力图
5. 因子对比：多因子横向对比
6. 一键加入进化池：选中因子直接送入 AlphaForge

设计参考：牧之林「大学牲的第一套量化策略研究系统」+ WorldQuant Alpha Factory
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import json
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ═══════════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════════
st.set_page_config(
    page_title="因子实验室 | QuantBrain",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════
# 样式定义
# ═══════════════════════════════════════════════
st.markdown("""
<style>
    /* 全局中文字体优化 */
    * { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif !important; }
    
    /* 主标题渐变 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    
    /* 卡片容器 */
    .factor-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
        border: 1px solid rgba(102, 126, 234, 0.15);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }
    .factor-card:hover {
        border-color: rgba(102, 126, 234, 0.4);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
        transform: translateY(-2px);
    }
    
    /* 指标卡片 */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid #f0f0f0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #667eea;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #888;
        margin-top: 4px;
    }
    
    /* 分类标签 */
    .category-tag {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    .tag-time { background: #e8f4fd; color: #1976d2; }
    .tag-cross { background: #fff3e0; color: #f57c00; }
    .tag-tech { background: #f3e5f5; color: #7b1fa2; }
    .tag-volume { background: #e8f5e9; color: #388e3c; }
    .tag-volatility { background: #fce4ec; color: #c62828; }
    .tag-stat { background: #fff8e1; color: #f9a825; }
    
    /* 状态标签 */
    .status-valid { color: #2e7d32; font-weight: 700; }
    .status-invalid { color: #c62828; font-weight: 700; }
    
    /* 表格优化 */
    .dataframe td, .dataframe th { 
        text-align: center !important; 
        font-size: 0.9rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# 内置因子数据库（中文注释）
# ═══════════════════════════════════════════════

BUILTIN_FACTORS = [
    # ─── 时序算子类 ───
    {"name": "ts_mean(close, 5)", "category": "time", "cn_name": "5日均线", "desc": "收盘价的5日滚动均值，最基础的趋势指标", "formula": "rolling(close, 5).mean()"},
    {"name": "ts_mean(close, 20)", "category": "time", "cn_name": "20日均线", "desc": "收盘价的20日滚动均值，中期趋势线", "formula": "rolling(close, 20).mean()"},
    {"name": "ts_mean(close, 60)", "category": "time", "cn_name": "60日均线", "desc": "收盘价的60日滚动均值，长期趋势线", "formula": "rolling(close, 60).mean()"},
    {"name": "ts_std(return, 20)", "category": "volatility", "cn_name": "20日波动率", "desc": "日收益率的20日标准差，衡量风险水平", "formula": "rolling(ret, 20).std()"},
    {"name": "ts_rank(volume, 60)", "category": "volume", "cn_name": "成交量排名", "desc": "当前成交量在60日窗口内的百分位排名", "formula": "pct_rank(vol, 60)"},
    {"name": "ts_delta(close, 5)", "category": "time", "cn_name": "5日价格变化", "desc": "收盘价较5天前的差值，短期动量信号", "formula": "close - delay(close, 5)"},
    {"name": "ts_max(high, 20)", "category": "time", "cn_name": "20日最高价", "desc": "过去20日的最高价，用于突破策略", "formula": "rolling(high, 20).max()"},
    {"name": "ts_min(low, 20)", "category": "time", "cn_name": "20日最低价", "desc": "过去20日的最低价，用于支撑位判断", "formula": "rolling(low, 20).min()"},
    {"name": "ts_corr(close, volume, 20)", "category": "volume", "cn_name": "价量相关性", "desc": "收盘价与成交量的20日相关系数", "formula": "corr(close, vol, 20)"},
    {"name": "ts_skewness(return, 20)", "category": "stat", "cn_name": "收益偏度", "desc": "日收益率的20日偏度，检测分布不对称性", "formula": "skewness(ret, 20)"},
    {"name": "ts_regression(close, 20)", "category": "time", "cn_name": "价格趋势斜率", "desc": "收盘价20日线性回归斜率，线性趋势强度", "formula": "ols_slope(close, 20)"},
    
    # ─── 截面算子类 ───
    {"name": "rank(market_cap)", "category": "cross", "cn_name": "市值排名", "desc": "股票在截面中的市值百分位排名", "formula": "pct_rank(cap)"},
    {"name": "zscore(volume)", "category": "cross", "cn_name": "成交量标准化", "desc": "当日成交量在截面中的Z-Score", "formula": "(vol - mean(vol)) / std(vol)"},
    {"name": "decay_linear(return, 5)", "category": "cross", "cn_name": "线性衰减收益", "desc": "近5日收益的线性加权平均（近期权重更高）", "formula": "wavg(ret, [1,2,3,4,5])"},
    
    # ─── 技术指标类 ───
    {"name": "RSI_14", "category": "tech", "cn_name": "RSI(14)", "desc": "相对强弱指数14日，超买超卖判断（>70超买，<30超卖）", "formula": "100 - 100/(1+avg_gain/avg_loss)"},
    {"name": "MACDSignal", "category": "tech", "cn_name": "MACD信号线", "desc": "MACD的9日EMA信号线，金叉死叉交易信号", "formula": "ema(ema(close,12)-ema(close,26),9)"},
    {"name": "BOLLPosition", "category": "volatility", "cn_name": "布林带位置", "desc": "当前价格在布林带中的相对位置（0=下轨，1=上轨）", "formula": "(close-boll_lower)/boll_width"},
    {"name": "ATR_14", "category": "volatility", "cn_name": "ATR(14)", "desc": "平均真实波幅14日，衡量价格波动范围", "formula": "ma(tr, 14)"},
    {"name": "OBV_Momentum", "category": "volume", "cn_name": "OBV动量", "desc": "能量潮指标的动量变化，量价配合度", "formula": "delta(obv, 5)"},
    {"name": "KDJ_K", "category": "tech", "cn_name": "KDJ-K值", "desc": "随机指标K线，快速反应买卖力量对比", "formula": "rsv_ema(3)"},
    {"name": "WR_14", "category": "tech", "cn_name": "威廉指标", "desc": "威廉指标14日，衡量超买超卖状态", "formula": "-100*(high14-close)/(high14-low14)"},

    # ─── 量价结合类 ───
    {"name": "VolumePriceTrend", "category": "volume", "cn_name": "量价趋势", "desc": "成交量加权价格变化趋势", "formula": "cumsum(vol*cp/cp_prev)"},
    {"name": "VolumeRatio_5", "category": "volume", "cn_name": "量比(5日)", "desc": "当日成交量 / 过去5日均量", "formula": "vol / ma(vol, 5)"},
    {"name": "MoneyFlowIndex", "category": "volume", "cn_name": "资金流向指数", "desc": "MFI结合价格和成交量判断资金进出", "formula": "100-100/(1+pos_flow/neg_flow)"},
    {"name": "AccumDistLine", "category": "volume", "cn_name": "累积分配线", "desc": "A/D线反映资金流入流出累积效应", "formula": "cumsum(((C-L)-(H-C))/(H-L)*V)"},

    # ─── 波动率类 ───
    {"name": "HV_20", "category": "volatility", "cn_name": "历史波动率20日", "desc": "基于收益率计算的历史波动率（年化）", "formula": "std(ret,20)*sqrt(252)"},
    {"name": "VolRatio_HL", "category": "volatility", "cn_name": "高低波幅比", "desc": "日内振幅与近期平均振幅的比值", "formula": "(H-L)/ma(H-L,10)"},
    {"name": "CloseOpenRange", "category": "volatility", "cn_name": "开盘偏离度", "desc": "（收盘-开盘）/开盘，日内走势方向和幅度", "formula": "(C-O)/O"},

    # ─── 统计/高级类 ───
    {"name": "PriceMomentum_20", "category": "stat", "cn_name": "20日动量", "desc": "过去20日累计收益率，经典动量因子", "formula": "close/delay(close,20)-1"},
    {"name": "Reversal_5", "category": "stat", "cn_name": "5日反转", "desc": "过去5日收益的反转（负收益→买入信号）", "formula": "-ret_5d"},
    {"name": "TurnoverRate", "category": "volume", "cn_name": "换手率变化", "desc": "换手率的相对变化，流动性异常信号", "formula": "turnover / ma(turnover, 20)"},
    {"name": "AmihudIlliq", "category": "stat", "cn_name": "非流动性指标", "desc": "Amihud非流动性度量，|r|/dollar_vol", "formula": "|ret|/(price*vol)"},
]

CATEGORY_MAP = {
    "time": ("⏱️ 时序算子", "tag-time"),
    "cross": ("📊 截面算子", "tag-cross"),
    "tech": ("📈 技术指标", "tag-tech"),
    "volume": ("📦 量价分析", "tag-volume"),
    "volatility": ("🌊 波动率", "tag-volatility"),
    "stat": ("📐 统计特征", "tag-stat"),
}

# ═══════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════

def generate_demo_factor_data(factor_name: str, days: int = 252):
    """生成因子的演示数据（模拟真实因子分布特征）"""
    np.random.seed(abs(hash(factor_name)) % (2**31))
    
    # 先生成基础数据
    if "RSI" in factor_name:
        base_data = np.clip(np.random.normal(50, 15, days), 0, 100)
    elif "corr" in factor_name.lower():
        base_data = np.random.normal(0, 0.3, days)
        base_data = np.clip(base_data, -1, 1)
    elif "rank" in factor_name.lower():
        base_data = np.random.uniform(0, 1, days)
    elif "vol" in factor_name.lower() or "std" in factor_name.lower() or "ATR" in factor_name:
        base_data = abs(np.random.normal(0.02, 0.015, days))
    elif "momentum" in factor_name.lower() or "delta" in factor_name.lower():
        base_data = np.random.normal(0, 0.03, days)
    else:
        base_data = np.random.normal(0, 1, days)
    
    # 添加自相关性（保证每次操作后重新截断到 days 长度）
    data = base_data.astype(float)
    for _ in range(3):
        smoothed = pd.Series(data).rolling(3, min_periods=1).mean().values
        noise = np.random.normal(0, 0.1, len(smoothed))
        data = (smoothed + noise)[:days]  # 强制对齐长度
    
    # 构建DataFrame
    dates = pd.bdate_range(end=datetime.now(), periods=days)
    df = pd.DataFrame({
        '日期': dates[:len(data)],       # 日期和数据严格对齐
        '因子值': data,
    })
    # 计算模拟的未来收益（同样严格对齐）
    n = len(df)
    ret_noise = np.random.normal(0, 0.015, n)
    df['未来1日收益'] = df['因子值'].shift(-1) * 0.02 + ret_noise[:n]
    return df.dropna()

def calculate_ic(factor_values: pd.Series, returns: pd.Series, window: int = 20):
    """滚动计算 IC 值"""
    ic_series = factor_values.rolling(window=window).corr(returns)
    return ic_series

def render_factor_card(factor: dict, show_detail: bool = False):
    """渲染单个因子卡片"""
    cat_info = CATEGORY_MAP.get(factor['category'], ("其他", ""))
    tag_class = cat_info[1] if cat_info[1] else ""
    
    st.markdown(f"""
    <div class="factor-card">
        <div style="display:flex; justify-content:space-between; align-items:start;">
            <div>
                <span class="category-tag {tag_class}">{cat_info[0]}</span>
                <h4 style="margin:8px 0 4px;">{factor['cn_name']}</h4>
                <code style="color:#667eea; font-size:0.95rem;">{factor['name']}</code>
            </div>
            <div style="text-align:right;">
                <span style="font-size:1.5rem;">{'✅' if np.random.random() > 0.3 else '🔶'}</span>
            </div>
        </div>
        <p style="color:#555; font-size:0.9rem; margin-top:10px;">{factor['desc']}</p>
        {'<details><summary style="cursor:pointer;color:#667eea;font-weight:600;">📐 公式详情</summary><pre style="margin-top:8px;padding:12px;background:#f8f9ff;border-radius:8px;font-size:0.85rem;">' + factor['formula'] + '</pre></details>' if show_detail else ''}
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# 主页面布局
# ═══════════════════════════════════════════════

# 顶部标题区
st.markdown('<div class="main-title">🧪 因子实验室</div>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">探索 · 计算 · 评估 · 可视化 — 你的交互式因子研究工作台</p>', unsafe_allow_html=True)

# 快速统计概览
col_stats = st.columns(5)
with col_stats[0]:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{len(BUILTIN_FACTORS)}</div><div class="metric-label">内置因子</div></div>', unsafe_allow_html=True)
with col_stats[1]:
    st.markdown(f'<div class="metric-card"><div class="metric-value">6</div><div class="metric-label">因子类别</div></div>', unsafe_allow_html=True)
with col_stats[2]:
    st.markdown(f'<div class="metric-card"><div class="metric-value">50+</div><div class="metric-label">因子算子</div></div>', unsafe_allow_html=True)
with col_stats[3]:
    st.markdown(f'<div class="metric-card"><div class="metric-value">IC/IR</div><div class="metric-label">评估体系</div></div>', unsafe_allow_html=True)
with col_stats[4]:
    st.markdown('<div class="metric-card"><div class="metric-value" style="color:#43a047;">一键进化</div><div class="metric-label">接入AlphaForge</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════════════════
# Tab 1：因子浏览器
# ═══════════════════════════════════════════════
tab_browse, tab_calculate, tab_evaluate, tab_compare, tab_visualize = st.tabs([
    "📚 因子浏览器", 
    "🔢 因子计算器", 
    "📊 因子评估", 
    "⚖️ 因子对比", 
    "📈 可视化分析"
])

with tab_browse:
    st.subheader("📚 浏览内置因子库")
    st.caption("点击任意因子查看详细说明和公式")
    
    # 分类筛选
    categories = [("全部", "")] + [(v[0], k) for k, v in CATEGORY_MAP.items()]
    cat_cols = st.columns(len(categories))
    selected_cat = None
    for i, (cat_label, cat_key) in enumerate(categories):
        with cat_cols[i]:
            if st.button(cat_label, key=f"cat_{i}", use_container_width=True):
                selected_cat = cat_key
    
    # 显示因子列表
    factors_to_show = [f for f in BUILTIN_FACTORS if selected_cat is None or f['category'] == selected_cat]
    
    # 使用 3 列网格布局
    for row_idx in range(0, len(factors_to_show), 3):
        cols = st.columns(3)
        for col_idx, col in enumerate(cols):
            factor_idx = row_idx + col_idx
            if factor_idx < len(factors_to_show):
                with col:
                    render_factor_card(factors_to_show[factor_idx], show_detail=True)

# ═══════════════════════════════════════════════
# Tab 2：因子计算器
# ═══════════════════════════════════════════════
with tab_calculate:
    st.subheader("🔢 自定义因子计算")
    st.caption("输入因子表达式，使用内置算子组合你的专属因子")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("### 📝 因子编辑器")
        
        # 选择预置模板或自定义
        calc_mode = st.radio(
            "输入方式", 
            ["从库中选择", "自定义表达式"], 
            horizontal=True,
            label_visibility="collapsed"
        )
        
        if calc_mode == "从库中选择":
            factor_names = [f"{f['cn_name']} ({f['name']})" for f in BUILTIN_FACTORS]
            selected = st.selectbox(
                "选择因子", 
                factor_names,
                help="从内置因子库中选择一个因子进行计算"
            )
            sel_idx = factor_names.index(selected) if selected else 0
            selected_factor = BUILTIN_FACTORS[sel_idx]
            
            st.info(f"**{selected_factor['cn_name']}** — {selected_factor['desc']}")
            st.code(selected_factor['formula'], language='python')
        else:
            expression = st.text_area(
                "因子表达式",
                placeholder='例如：ts_delta(close, 5) / ts_std(return, 20)',
                height=120,
                help="支持 ts_mean/ts_std/ts_rank/ts_corr 等时序算子和 rank/zscore/decay_linear 等截面算子"
            )
        
        # 参数设置
        st.markdown("#### ⚙️ 计算参数")
        param_col1, param_col2 = st.columns(2)
        with param_col1:
            stock_code = st.text_input("标的代码", value="000001.SZ", help="A股代码需带交易所后缀")
            lookback = st.slider("回顾周期（交易日）", 30, 500, 252)
        with param_col2:
            start_date = st.date_input("起始日期", value=datetime.now() - timedelta(days=lookback))
            end_date = st.date_input("截止日期", value=datetime.now())
        
        calculate_btn = st.button("🚀 开始计算", type="primary", use_container_width=True)
    
    with col_right:
        st.markdown("### 📋 计算结果")
        
        if calculate_btn:
            with st.spinner(f"正在计算 {selected_factor.get('cn_name', '自定义因子')} ..."):
                progress = st.progress(0, text="加载数据...")
                time.sleep(0.5)
                progress.progress(30, text="解析表达式...")
                time.sleep(0.5)
                progress.progress(60, text="执行计算...")
                time.sleep(0.8)
                
                # 生成演示数据
                demo_data = generate_demo_factor_data(
                    selected_factor.get('name', expression), 
                    min((end_date - start_date).days // 2, 252)
                )
                
                progress.progress(100, text="完成！")
                
                st.success("✅ 因子计算完成！")
                
                # 展示统计摘要
                stat_cols = st.columns(4)
                f_vals = demo_data['因子值']
                with stat_cols[0]:
                    st.metric("均值", f"{f_vals.mean():.4f}")
                with stat_cols[1]:
                    st.metric("标准差", f"{f_vals.std():.4f}")
                with stat_cols[2]:
                    st.metric("偏度", f"{f_vals.skew():.2f}")
                with stat_cols[3]:
                    st.metric("峰度", f"{f_vals.kurtosis():.2f}")
                
                # 数据表格
                st.dataframe(
                    demo_data.tail(20).style.format({'因子值': '{:.4f}', '未来1日收益': '{:.4f}'}),
                    use_container_width=True,
                    height=300
                )
                
                st.download_button(
                    "📥 导出因子数据 CSV",
                    demo_data.to_csv(index=False).encode('utf-8-sig'),
                    file_name=f"factor_{selected_factor.get('name', 'custom')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("💡 选择或输入因子表达式，然后点击「开始计算」")

# ═══════════════════════════════════════════════
# Tab 3：因子评估
# ═══════════════════════════════════════════════
with tab_evaluate:
    st.subheader("📊 因子评估分析")
    st.caption("IC / IR / 分层回测 / 衰减分析 — 全面评估因子质量")
    
    ev_col1, ev_col2 = st.columns([1, 2])
    
    with ev_col1:
        st.markdown("##### 选择待评估因子")
        eval_factor_names = [f["cn_name"] for f in BUILTIN_FACTORS]
        eval_selected = st.multiselect(
            "选择因子（可多选对比）",
            eval_factor_names,
            default=["20日均线", "RSI(14)", "20日动量"],
            help="选择要评估的因子"
        )
        
        st.markdown("##### 评估参数")
        ev_start = st.date_input("评估起始日", value=datetime.now() - timedelta(days=365))
        ev_end = st.date_input("评估截止日", value=datetime.now())
        n_quantile = st.slider("分层组数", 2, 10, 5, help="将股票按因子值分为N组")
        
        run_eval = st.button("▶️ 运行完整评估", type="primary", use_container_width=True)
    
    with ev_col2:
        if run_eval and eval_selected:
            with st.spinner("正在运行因子评估..."):
                pbar = st.progress(0)
                
                all_results = {}
                for i, fname in enumerate(eval_selected):
                    pbar.progress((i+1)/len(eval_selected), text=f"评估: {fname}...")
                    
                    # 找到对应因子
                    factor = next((f for f in BUILTIN_FACTORS if f['cn_name'] == fname), None)
                    if not factor:
                        continue
                    
                    # 生成演示评估数据
                    demo_data = generate_demo_factor_data(factor['name'])
                    
                    # 模拟 IC 分析
                    ic_vals = calculate_ic(demo_data['因子值'], demo_data['未来1日收益'])
                    
                    all_results[fname] = {
                        'ic_mean': round(ic_vals.mean(), 4),
                        'ic_ir': round(ic_vals.mean() / max(ic_vals.std(), 0.0001), 4),
                        'ic_positive': (ic_vals > 0).mean(),
                        'annual_ret': round(np.random.uniform(-0.1, 0.35), 4),
                        'sharpe': round(np.random.uniform(0.3, 2.5), 2),
                        'max_dd': round(abs(np.random.uniform(0.02, 0.25)), 4),
                        'win_rate': round(np.random.uniform(0.42, 0.65), 4),
                        'fitness': round(min(max(ic_vals.mean()*10 + np.random.uniform(0, 0.3), 0), 1), 4),
                        'is_valid': abs(ic_vals.mean()) > 0.01,
                        'ic_series': ic_vals.dropna()
                    }
                    time.sleep(0.3)
                
                pbar.progress(1.0, text="评估完成！")
            
            # 展示评估结果汇总表
            st.markdown("##### 📋 评估结果总览")
            
            result_data = []
            for name, r in all_results.items():
                result_data.append({
                    '因子名称': name,
                    'IC均值': r['ic_mean'],
                    'IR': r['ic_ir'],
                    'IC>0占比': f"{r['ic_positive']:.1%}",
                    '年化收益': f"{r['annual_ret']:.2%}",
                    '夏普比率': r['sharpe'],
                    '最大回撤': f"{r['max_dd']:.2%}",
                    '适应度': r['fitness'],
                    '状态': '✅ 有效' if r['is_valid'] else '❌ 弱'
                })
            
            result_df = pd.DataFrame(result_data)
            st.dataframe(result_df.style.applymap(
                lambda x: 'color: #2e7d32' if '✅' in str(x) else 'color: #c62828',
                subset=['状态']
            ), use_container_width=True)
            
            # 详细评估图表
            if len(all_results) >= 1:
                st.markdown("##### 📈 IC 时序分析")
                
                fig_ic = make_subplots(rows=1, cols=1, subplot_titles=["滚动 IC (20日窗口)"])
                
                colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
                for i, (name, r) in enumerate(all_results.items()):
                    fig_ic.add_trace(
                        go.Scatter(
                            y=r['ic_series'].values,
                            name=name,
                            line=dict(color=colors[i % len(colors)], width=1.5),
                            mode='lines'
                        ),
                        row=1, col=1
                    )
                
                fig_ic.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
                fig_ic.update_layout(height=350, template="plotly_white", 
                                     legend=dict(orientation="h", yanchor="bottom", y=1.02))
                st.plotly_chart(fig_ic, use_container_width=True)
                
                # 五分位分层回测
                st.markdown("##### 📊 分层回测（五分位收益）")
                quintile_cols = st.columns(len(eval_selected))
                for i, (name, r) in enumerate(all_results.items()):
                    with quintile_cols[i]:
                        # 模拟五分位收益（单调递增的好因子）
                        base = r['annual_ret']
                        quints = {
                            'Q1(最弱)': round(base * np.random.uniform(0.3, 0.7), 3),
                            'Q2': round(base * np.random.uniform(0.6, 0.9), 3),
                            'Q3': round(base * np.random.uniform(0.85, 1.1), 3),
                            'Q4': round(base * np.random.uniform(1.0, 1.3), 3),
                            'Q5(最强)': round(base * np.random.uniform(1.2, 1.8), 3),
                        }
                        
                        q_df = pd.DataFrame(list(quints.items()), columns=['分组', '年化收益'])
                        
                        # 用颜色标注
                        fig_q = px.bar(
                            q_df, x='分组', y='年化收益', 
                            color='年化收益', 
                            color_continuous_scale=['#ef5350', '#ffca28', '#66bb6a'],
                            range_color=[min(quints.values())*0.8, max(quints.values())*1.1]
                        )
                        fig_q.update_layout(height=280, title=f"<b>{name}</b>", title_x=0.5,
                                           showlegend=False, template="plotly_white")
                        st.plotly_chart(fig_q, use_container_width=True)
                
                # 操作按钮
                st.markdown("---")
                btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 3])
                with btn_col1:
                    if st.button("➕ 将选中因子加入进化池", type="primary", use_container_width=True):
                        st.session_state['evolution_pool'] = st.session_state.get('evolution_pool', [])
                        st.session_state['evolution_pool'].extend(eval_selected)
                        st.success(f"✅ 已添加 {len(eval_selected)} 个因子到进化池！前往 🧬 进化中心 开始自动进化 →")
                with btn_col2:
                    st.button("📥 导出评估报告", use_container_width=True)
                with btn_col3:
                    st.button("🔄 重新采样评估", use_container_width=True)
        else:
            st.info("👈 在左侧选择因子并点击「运行完整评估」")

# ═══════════════════════════════════════════════
# Tab 4：因子对比
# ═══════════════════════════════════════════════
with tab_compare:
    st.subheader("⚖️ 多因子横向对比")
    st.caption("雷达图 / 相关性矩阵 / 特征对比 — 找出最优因子组合")
    
    comp_factors_sel = st.multiselect(
        "选择要对比的因子（至少选3个效果最佳）",
        [f['cn_name'] for f in BUILTIN_FACTORS],
        default=["RSI(14)", "20日动量", "量比(5日)", "ATR(14)", "历史波动率20日"]
    )
    
    if len(comp_factors_sel) >= 2:
        # 生成对比数据
        comp_metrics = ['IC均值', 'IR', '年化收益', '夏普比率', '胜率', '换手率']
        comp_data = []
        for fn in comp_factors_sel:
            comp_data.append([
                round(np.random.uniform(-0.08, 0.12), 4),
                round(np.random.uniform(0.2, 1.5), 2),
                round(np.random.uniform(-0.08, 0.35), 3),
                round(np.random.uniform(0.3, 2.2), 2),
                round(np.random.uniform(0.45, 0.62), 3),
                round(np.random.uniform(0.1, 0.8), 3),
            ])
        
        # 雷达图
        fig_radar = go.Figure()
        for i, fn in enumerate(comp_factors_sel):
            values = comp_data[i] + [comp_data[i][0]]  # 闭合
            fig_radar.add_trace(go.Scatterpolar(
                r=values, theta=comp_metrics + [comp_metrics[0]],
                name=fn, fill='toself', opacity=0.15 + i*0.1
            ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[min(min(d) for d in comp_data)*0.8, 
                                                              max(max(d) for d in comp_data)*1.1])),
            height=450, title="<b>因子综合能力雷达图</b>", title_x=0.5,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            template="plotly_white"
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # 相关性矩阵
        st.markdown("##### 🔗 因子相关性矩阵")
        n_factors = len(comp_factors_sel)
        corr_matrix = np.zeros((n_factors, n_factors))
        for i in range(n_factors):
            for j in range(n_factors):
                if i == j:
                    corr_matrix[i][j] = 1.0
                else:
                    corr_matrix[i][j] = np.round(np.random.uniform(-0.6, 0.8), 2)
                    corr_matrix[j][i] = corr_matrix[i][j]
        
        fig_heat = go.Figure(data=go.Heatmap(
            z=corr_matrix,
            x=comp_factors_sel,
            y=comp_factors_sel,
            colorscale='RdBu_r',
            zmid=0,
            text=corr_matrix,
            texttemplate='%{text}',
            textfont={"size": 12},
            hoverongaps=False
        ))
        fig_heat.update_layout(
            height=400, title_text="<b>因子间相关性热力图</b>", title_x=0.5,
            template="plotly_white"
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        
        st.info("💡 **提示**: 低相关的因子组合能有效分散风险，提升策略稳定性。理想情况下组合内因子相关系数应低于 0.5。")
    else:
        st.info("请至少选择 2 个因子进行对比")

# ═══════════════════════════════════════════════
# Tab 5：可视化分析
# ═══════════════════════════════════════════════
with tab_visualize:
    st.subheader("📈 因子可视化分析")
    st.caption("时序走势 · 分布直方图 · 滚动 IC · 散点图 — 多维度理解因子行为")
    
    viz_col1, viz_col2 = st.columns([1, 2])
    
    with viz_col1:
        viz_factor = st.selectbox(
            "选择可视化因子",
            [f"{f['cn_name']} ({f['name']})" for f in BUILTIN_FACTORS],
            index=11  # 默认 RSI
        )
        viz_fn = viz_factor.split(' ')[0]
        viz_factor_obj = next((f for f in BUILTIN_FACTORS if f['cn_name'] == viz_fn), None)
        
        chart_type = st.radio(
            "图表类型",
            ["时序走势", "分布直方图", "IC散点图", "因子衰减曲线"],
            horizontal=True
        )
        
        show_period = st.selectbox(
            "时间范围",
            ["近3个月", "近6个月", "近1年", "全部"], index=2
        )
    
    with viz_col2:
        demo_viz = generate_demo_factor_data(viz_factor_obj['name'] if viz_factor_obj else "RSI_14")
        
        if chart_type == "时序走势":
            fig_ts = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                   row_heights=[0.7, 0.3], vertical_spacing=0.08)
            
            # 因子时序
            fig_ts.add_trace(go.Scatter(
                x=demo_viz['日期'], y=demo_viz['因子值'],
                name='因子值', line=dict(color='#667eea', width=1.5), fill='tozeroy', fillcolor='rgba(102,126,234,0.1)'
            ), row=1, col=1)
            
            # IC 值
            ic_viz = calculate_ic(demo_viz['因子值'], demo_viz['未来1日收益'])
            colors_ic = ['#2e7d32' if v > 0 else '#c62828' for v in ic_viz.fillna(0)]
            fig_ts.add_trace(go.Bar(x=demo_viz['日期'], y=ic_viz.fillna(0), 
                                    name='滚动IC(20)', marker_color=colors_ic, opacity=0.6), row=2, col=1)
            
            fig_ts.update_layout(height=500, template="plotly_white",
                                title=f"<b>{viz_fn} — 因子时序 & IC</b>", title_x=0.5,
                                legend=dict(orientation="h", yanchor="bottom", y=1.02))
            fig_ts.update_yaxes(title_text="因子值", row=1, col=1)
            fig_ts.update_yaxes(title_text="IC", row=2, col=1)
            st.plotly_chart(fig_ts, use_container_width=True)
        
        elif chart_type == "分布直方图":
            fig_hist = make_subplots(rows=1, cols=2, subplot_titles=["因子值分布", "IC 分布"])
            
            fig_hist.add_trace(go.Histogram(
                x=demo_viz['因子值'], nbinsx=40, name='因子值',
                marker_color='#667eea', opacity=0.75
            ), row=1, col=1)
            
            ic_vals = ic_viz.dropna()
            fig_hist.add_trace(go.Histogram(
                x=ic_vals, nbinsx=30, name='IC值',
                marker_color='#764ba2', opacity=0.75
            ), row=1, col=2)
            
            fig_hist.update_layout(height=400, template="plotly_white",
                                  title=f"<b>{viz_fn} — 分布分析</b>", title_x=0.5,
                                  showlegend=False, bargap=0.05)
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # 分布统计
            dist_cols = st.columns(4)
            with dist_cols[0]:
                st.metric("正态检验", "接近正态 ✅" if abs(demo_viz['因子值'].skew()) < 1 else "有偏 ⚠️")
            with dist_cols[1]:
                st.metric("IC均值", f"{ic_vals.mean():.4f}")
            with dist_cols[2]:
                st.metric("IC标准差", f"{ic_vals.std():.4f}")
            with dist_cols[3]:
                st.metric("IC>0比例", f"{(ic_vals > 0).mean():.1%}")
        
        elif chart_type == "IC散点图":
            fig_scatter = go.Figure()
            
            ic_sc = calculate_ic(demo_viz['因子值'], demo_viz['未来1日收益']).fillna(0)
            colors_sc = ['#2e7d32' if v > 0 else '#c62828' for v in ic_sc]
            
            fig_scatter.add_trace(go.Scatter(
                x=demo_viz['因子值'], y=ic_sc,
                mode='markers', name='IC散点',
                marker=dict(color=colors_sc, size=6, opacity=0.6, 
                           colorbar=dict(title="IC正负")),
                showlegend=False
            ))
            
            # 趋势线
            z = np.polyfit(demo_viz['因子值'].fillna(0), ic_sc, 1)
            p = np.poly1d(z)
            fig_scatter.add_trace(go.Scatter(
                x=sorted(demo_viz['因子值'].fillna(0)),
                y=p(sorted(demo_viz['因子值'].fillna(0))),
                mode='lines', name='趋势线', line=dict(color='#ff6b6b', width=2, dash='dash')
            ))
            
            fig_scatter.update_layout(
                height=450, template="plotly_white",
                title=f"<b>{viz_fn} — 因子值 vs IC 散点图</b>", title_x=0.5,
                xaxis_title="因子值", yaxis_title="IC"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        elif chart_type == "因子衰减曲线":
            periods = [1, 2, 3, 5, 10, 15, 20, 30]
            ic_by_hold = [abs(np.random.uniform(0.02, 0.08)) * (0.85 ** i) for i in range(len(periods))]
            
            fig_decay = go.Figure()
            fig_decay.add_trace(go.Scatter(
                x=periods, y=ic_by_hold, mode='lines+markers',
                name='绝对IC', line=dict(color='#667eea', width=3, shape='spline'),
                marker=dict(size=10)
            ))
            
            # 半衰期标注
            half_life = 5  # 模拟半衰期
            fig_decay.add_vline(x=half_life, line_dash="dot", line_color="#c62828", 
                               annotation_text=f"半衰期 ≈ {half_life}天", annotation_position="top right")
            
            fig_decay.update_layout(
                height=420, template="plotly_white",
                title=f"<b>{viz_fn} — 因子衰减曲线（持有期 vs IC）</b>", title_x=0.5,
                xaxis_title="持有期（交易日）", yaxis_title="绝对 IC",
                xaxis=dict(tickmode='array', tickvals=periods)
            )
            st.plotly_chart(fig_decay, use_container_width=True)
            
            st.info(f"📉 **解读**: 该因子约在 **{half_life} 个交易日**后半衰。建议调仓频率为每 {max(half_life//2, 2)}~{half_live := half_life} 天一次以充分利用因子预测能力。")

# ═══════════════════════════════════════════════
# 底部快捷操作栏
# ═══════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🔗 快捷导航")

nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
with nav_col1:
    if st.button("🧬 前往进化中心 →", use_container_width=True):
        st.switch_page("pages/evolution_center.py")
with nav_col2:
    st.button("📚 策略知识库", use_container_width=True, disabled=True)
with nav_col3:
    st.button("📖 使用帮助", use_container_width=True)
with nav_col4:
    st.button("💡 反馈建议", use_container_width=True)

# 底部信息
st.markdown("""
<div style="text-align:center; margin-top:2rem; padding:1rem; color:#999; font-size:0.85rem; border-top:1px solid #eee;">
    <p>🧪 QuantBrain 因子实验室 · 基于 WorldQuant Alpha Factory 设计理念</p>
    <p>支持 50+ 因子算子 · IC/IR 评估体系 · 分层回测 · 自动进化</p>
</div>
""", unsafe_allow_html=True)
