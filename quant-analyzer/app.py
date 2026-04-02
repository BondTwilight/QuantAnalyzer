"""
QuantAnalyzer — 量化策略分析平台
单文件主入口（集成所有页面路由）
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

# ── 项目路径 ──
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from config import PAGE_CONFIG, AI_PROVIDERS, THEME_COLORS, REPORTS_DIR

# ── 页面配置 ──
st.set_page_config(**PAGE_CONFIG)

# ── 暗色主题CSS ──
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .kpi-label { color: #8b949e; font-size: 11px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
    .alert-danger { background: #da363322; border-left: 4px solid #f85149; padding: 12px 16px; border-radius: 4px; margin-bottom: 10px; color: #f85149; }
    .alert-warning { background: #9e6a0322; border-left: 4px solid #d29922; padding: 12px 16px; border-radius: 4px; margin-bottom: 10px; color: #d29922; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
    .badge-green { background: #23863633; color: #3fb950; }
    .badge-red { background: #da363333; color: #f85149; }
    .badge-yellow { background: #9e6a0333; color: #d29922; }
    .badge-blue { background: #1f6feb33; color: #58a6ff; }
    .dataframe th { background: #21262d !important; color: #58a6ff !important; }
    [data-testid="stSidebar"] { background: #0d1117; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# Session State
# ═══════════════════════════════════════════
if "db" not in st.session_state:
    from data.fetcher import db as _db
    st.session_state.db = _db
if "ai_provider" not in st.session_state:
    st.session_state.ai_provider = "deepseek"


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════
def get_rating_badge(score):
    if score >= 70: return '<span class="badge badge-green">A</span>'
    elif score >= 50: return '<span class="badge badge-blue">B</span>'
    elif score >= 30: return '<span class="badge badge-yellow">C</span>'
    else: return '<span class="badge badge-red">D</span>'

def compute_score(r):
    ar = r.get("annual_return", 0)
    mdd = abs(r.get("max_drawdown", 0))
    sr = r.get("sharpe_ratio", 0)
    wr = r.get("win_rate", 0)
    plr = r.get("profit_loss_ratio", 0)
    return min(30, max(0, ar*200)) + max(0, 20-mdd*100) + min(20, max(0, sr*10)) + wr*15 + min(15, max(0, plr*5))

def render_alerts(alerts):
    for a in alerts:
        cls = f"alert-{a['type']}"
        icon = {"danger":"🔴","warning":"🟡","info":"🔵"}.get(a["type"],"ℹ️")
        st.markdown(f'<div class="{cls}"><strong>{icon} {a["strategy"]}</strong> — {a["msg"]}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("## 📊 QuantAnalyzer\n**量化策略分析平台**\n---")
        pages = ["📊 策略总览","⚔️ 策略对比","📈 策略详情","🤖 AI 分析","📋 回测报告","⚙️ 系统设置"]
        selected = st.radio("导航", pages, label_visibility="collapsed")
        st.markdown("---")
        st.markdown("### 🤖 AI 模型")
        providers = {k: v["name"] for k, v in AI_PROVIDERS.items()}
        prov = st.selectbox("选择模型", list(providers.keys()), format_func=lambda x: providers[x])
        st.session_state.ai_provider = prov
        api_key = AI_PROVIDERS[prov].get("api_key", "")
        st.markdown("✅ API已配置" if api_key else "⚠️ 未配置API Key")
        st.markdown("---")
        st.markdown("### ⚡ 操作")
        if st.button("🔄 运行全部回测", use_container_width=True, type="primary"):
            with st.spinner("回测运行中..."):
                try:
                    from core.scheduler import run_once
                    run_once()
                    st.session_state.last_refresh = datetime.now().strftime("%H:%M:%S")
                    st.success("回测完成!"); st.rerun()
                except Exception as e: st.error(f"失败: {e}")
        if st.button("📄 生成日报", use_container_width=True):
            with st.spinner("生成中..."):
                try:
                    from utils.report import generate_daily_report
                    results = st.session_state.db.get_latest_results().to_dict("records")
                    if results:
                        p = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d')}.html"
                        generate_daily_report(results, p); st.success("日报已生成!")
                    else: st.warning("无数据")
                except Exception as e: st.error(f"失败: {e}")
        st.markdown("---")
        st.markdown('<div style="text-align:center;color:#8b949e;font-size:11px;">QuantAnalyzer v1.0<br>仅供学习，不构成投资建议</div>', unsafe_allow_html=True)
    return selected


# ═══════════════════════════════════════════
# 页面1: 策略总览
# ═══════════════════════════════════════════
def page_overview():
    st.title("📊 策略总览")
    st.caption(f"*最后更新: {st.session_state.get('last_refresh','暂无数据')}*")
    db = st.session_state.db
    try: results_df = db.get_latest_results()
    except Exception as e: st.error(f"数据库错误: {e}"); return
    if results_df.empty:
        st.markdown('<div style="text-align:center;padding:80px 20px;"><h2 style="color:#58a6ff;">🚀 欢迎使用 QuantAnalyzer</h2><p style="color:#8b949e;max-width:500px;margin:20px auto;">暂无回测数据。请点击左侧「运行全部回测」按钮开始首次分析。</p></div>', unsafe_allow_html=True)
        return

    results = results_df.to_dict("records")
    # 预警
    try:
        from utils.report import check_alerts
        alerts = check_alerts(results)
        if alerts:
            st.markdown("### ⚠️ 预警"); render_alerts(alerts); st.markdown("---")
    except: pass

    best = max(results, key=lambda x: x.get("annual_return",0))
    avg_sharpe = np.mean([r.get("sharpe_ratio",0) for r in results])
    avg_mdd = np.mean([abs(r.get("max_drawdown",0)) for r in results])
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("策略总数", len(results))
    with c2: st.metric("最佳年化", f"{best.get('annual_return',0):.1%}"); st.caption(best.get("strategy_name","")[:20])
    with c3: st.metric("平均夏普", f"{avg_sharpe:.2f}")
    with c4: st.metric("平均回撤", f"{avg_mdd:.1%}")
    with c5: st.metric("最差年化", f"{min(r.get('annual_return',0) for r in results):.1%}")
    st.markdown("---")

    for r in results: r["_score"] = compute_score(r)
    ranked = sorted(results, key=lambda x: x.get("_score",0), reverse=True)

    st.markdown("### 🏆 策略排名")
    rows = []
    for i, r in enumerate(ranked):
        ar = r.get("annual_return",0)
        rows.append({"#":i+1,"策略":r.get("strategy_name",""),"评级":get_rating_badge(r["_score"]),
            "年化收益":f"{'+' if ar>=0 else ''}{ar:.2%}","最大回撤":f"{abs(r.get('max_drawdown',0)):.2%}",
            "夏普":f"{r.get('sharpe_ratio',0):.2f}","Sortino":f"{r.get('sortino_ratio',0):.2f}" if r.get('sortino_ratio') else "-",
            "胜率":f"{r.get('win_rate',0):.1%}","盈亏比":f"{r.get('profit_loss_ratio',0):.2f}","交易":r.get("total_trades",0)})
    st.markdown(pd.DataFrame(rows).to_html(escape=False, index=False), unsafe_allow_html=True)
    st.markdown("---")

    # 净值曲线
    st.markdown("### 📈 净值曲线对比")
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        colors = ["#3fb950","#58a6ff","#d29922","#f778ba","#bc8cff"]
        for idx, r in enumerate(ranked[:5]):
            name = r.get("strategy_name","")
            try:
                daily = db.get_daily_values(name)
                if not daily.empty:
                    fig.add_trace(go.Scatter(x=daily.index, y=daily["portfolio_value"], name=name, line=dict(color=colors[idx%len(colors)],width=2)))
            except: pass
        try:
            sample = db.get_daily_values(ranked[0].get("strategy_name",""))
            if not sample.empty and "benchmark_value" in sample.columns:
                fig.add_trace(go.Scatter(x=sample.index, y=sample["benchmark_value"], name="沪深300", line=dict(color="#8b949e",width=1.5,dash="dash")))
        except: pass
        fig.update_layout(template="plotly_dark", height=420, legend=dict(orientation="h",yanchor="bottom",y=1.02))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e: st.warning(f"图表: {e}")

    # 散点图
    st.markdown("### 🎯 风险-收益分布")
    try:
        import plotly.graph_objects as go
        fig2 = go.Figure()
        for r in ranked:
            ar=r.get("annual_return",0); mdd=abs(r.get("max_drawdown",0)); sr=r.get("sharpe_ratio",0)
            color="#3fb950" if sr>1.0 else ("#d29922" if sr>0.5 else "#f85149")
            fig2.add_trace(go.Scatter(x=[mdd*100],y=[ar*100],name=r.get("strategy_name",""),
                text=[f"夏普:{sr:.1f}"],mode="markers+text",marker=dict(color=color,size=12,opacity=0.8),
                textposition="top center",textfont=dict(size=9)))
        fig2.update_layout(template="plotly_dark",height=380,xaxis_title="最大回撤(%)",yaxis_title="年化收益(%)")
        st.plotly_chart(fig2, use_container_width=True)
    except: pass


# ═══════════════════════════════════════════
# 页面2: 策略对比
# ═══════════════════════════════════════════
def page_compare():
    st.title("⚔️ 策略对比分析")
    db = st.session_state.db
    try: all_r = db.get_latest_results()
    except: st.error("数据库错误"); return
    if all_r.empty: st.info("暂无数据"); return
    results = all_r.to_dict("records")
    names = sorted(set(r.get("strategy_name","") for r in results))
    selected = st.multiselect("选择策略", names, default=names[:3])
    if not selected: st.warning("请选择策略"); return
    filtered = [r for r in results if r.get("strategy_name","") in selected]

    rows = []
    for r in filtered:
        rows.append({"策略":r.get("strategy_name",""),"年化收益":r.get("annual_return",0),
            "最大回撤":abs(r.get("max_drawdown",0)),"夏普比率":r.get("sharpe_ratio",0),
            "Sortino":r.get("sortino_ratio") or 0,"胜率":r.get("win_rate",0),
            "盈亏比":r.get("profit_loss_ratio",0),"波动率":r.get("volatility",0),"Beta":r.get("beta") or 0})
    df_c = pd.DataFrame(rows).set_index("策略")
    styled = df_c.style.format({"年化收益":"{:.2%}","最大回撤":"{:.2%}","夏普比率":"{:.2f}","Sortino":"{:.2f}","胜率":"{:.1%}","盈亏比":"{:.2f}","波动率":"{:.2%}","Beta":"{:.2f}"})
    st.dataframe(styled, use_container_width=True)

    import plotly.graph_objects as go
    # 雷达图
    st.markdown("### 🕸️ 综合能力雷达图")
    categories = ["年化收益","夏普比率","胜率","盈亏比","低回撤","稳定性"]
    colors = ["#3fb950","#58a6ff","#d29922","#f778ba","#bc8cff"]
    fig = go.Figure()
    for idx, r in enumerate(filtered):
        vals = [min(10,max(0,r.get("annual_return",0)*100)),min(10,max(0,r.get("sharpe_ratio",0)*5)),
            r.get("win_rate",0)*10,min(10,max(0,r.get("profit_loss_ratio",0)*5)),
            min(10,max(0,(1-abs(r.get("max_drawdown",0)))*10)),min(10,max(0,(1-r.get("volatility",0))*10))]
        fig.add_trace(go.Scatterpolar(r=vals+[vals[0]],theta=categories+[categories[0]],fill="toself",
            name=r.get("strategy_name",""),line_color=colors[idx%len(colors)],opacity=0.5))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,10])),showlegend=True,template="plotly_dark",height=450)
    st.plotly_chart(fig, use_container_width=True)

    # 净值叠加
    st.markdown("### 📈 净值曲线叠加")
    fig2 = go.Figure()
    for idx, r in enumerate(filtered):
        try:
            daily = db.get_daily_values(r.get("strategy_name",""))
            if not daily.empty:
                first = daily["portfolio_value"].iloc[0]
                norm = daily["portfolio_value"]/first if first>0 else daily["portfolio_value"]
                fig2.add_trace(go.Scatter(x=daily.index,y=norm,name=r.get("strategy_name",""),line=dict(color=colors[idx%len(colors)],width=2)))
        except: pass
    fig2.update_layout(template="plotly_dark",height=400,yaxis_title="归一化净值")
    st.plotly_chart(fig2, use_container_width=True)

    # 回撤
    st.markdown("### 📉 回撤对比")
    fig3 = go.Figure()
    for idx, r in enumerate(filtered):
        try:
            daily = db.get_daily_values(r.get("strategy_name",""))
            if not daily.empty and "drawdown" in daily.columns:
                fig3.add_trace(go.Scatter(x=daily.index,y=daily["drawdown"]*100,name=r.get("strategy_name",""),
                    fill="tozeroy",line=dict(color=colors[idx%len(colors)],width=1)))
        except: pass
    fig3.update_layout(template="plotly_dark",height=320,yaxis_title="回撤(%)")
    st.plotly_chart(fig3, use_container_width=True)


# ═══════════════════════════════════════════
# 页面3: 策略详情
# ═══════════════════════════════════════════
def page_detail():
    st.title("📈 策略详情分析")
    db = st.session_state.db
    try: all_r = db.get_latest_results()
    except: st.error("数据库错误"); return
    if all_r.empty: st.info("暂无数据"); return
    results = all_r.to_dict("records")
    names = sorted(set(r.get("strategy_name","") for r in results))
    sel = st.selectbox("选择策略", names)
    r = next((x for x in results if x.get("strategy_name")==sel), None)
    if not r: return

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("年化收益",f"{r.get('annual_return',0):.2%}")
    with c2: st.metric("最大回撤",f"{abs(r.get('max_drawdown',0)):.2%}")
    with c3: st.metric("夏普比率",f"{r.get('sharpe_ratio',0):.2f}")
    with c4: st.metric("胜率",f"{r.get('win_rate',0):.1%}")
    c5,c6,c7,c8 = st.columns(4)
    with c5: st.metric("Sortino",f"{r.get('sortino_ratio',0):.2f}" if r.get("sortino_ratio") else "N/A")
    with c6: st.metric("Calmar",f"{r.get('calmar_ratio',0):.2f}" if r.get("calmar_ratio") else "N/A")
    with c7: st.metric("盈亏比",f"{r.get('profit_loss_ratio',0):.2f}")
    with c8: st.metric("总交易",r.get("total_trades",0))
    st.markdown("---")

    import plotly.graph_objects as go
    ca,cb = st.columns(2)
    with ca:
        st.markdown("### 净值曲线")
        try:
            daily = db.get_daily_values(sel)
            if not daily.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=daily.index,y=daily["portfolio_value"],name="策略",line=dict(color="#3fb950",width=2),fill="tozeroy",fillcolor="rgba(63,185,80,0.08)"))
                if "benchmark_value" in daily.columns:
                    fig.add_trace(go.Scatter(x=daily.index,y=daily["benchmark_value"],name="沪深300",line=dict(color="#8b949e",width=1.5,dash="dash")))
                fig.update_layout(template="plotly_dark",height=340)
                st.plotly_chart(fig, use_container_width=True)
        except: pass
    with cb:
        st.markdown("### 回撤曲线")
        try:
            if not daily.empty and "drawdown" in daily.columns:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=daily.index,y=daily["drawdown"]*100,fill="tozeroy",line=dict(color="#f85149",width=1.5)))
                fig2.update_layout(template="plotly_dark",height=340,yaxis_title="回撤(%)")
                st.plotly_chart(fig2, use_container_width=True)
        except: pass

    st.markdown("### 📊 日收益率分布")
    try:
        if not daily.empty:
            rets = daily["portfolio_value"].pct_change().dropna()
            fig3 = go.Figure()
            fig3.add_trace(go.Histogram(x=rets*100,nbinsx=50,marker_color="#58a6ff",opacity=0.8))
            fig3.add_vline(x=0,line_dash="dash",line_color="#f85149",opacity=0.5)
            fig3.update_layout(template="plotly_dark",height=280,xaxis_title="日收益率(%)")
            st.plotly_chart(fig3, use_container_width=True)
    except: pass

    st.markdown("---")
    if st.button("🤖 AI 深度分析此策略", type="primary"):
        with st.spinner("分析中..."):
            try:
                from core.ai_analyzer import AIAnalyzer
                analyzer = AIAnalyzer(st.session_state.get("ai_provider","deepseek"))
                st.session_state["ai_detail"] = analyzer.analyze_strategy(r)
            except Exception as e: st.error(f"失败: {e}")
    if "ai_detail" in st.session_state:
        st.markdown("### 🤖 AI 分析报告")
        st.markdown(st.session_state["ai_detail"])


# ═══════════════════════════════════════════
# 页面4: AI 分析
# ═══════════════════════════════════════════
def page_ai():
    st.title("🤖 AI 智能分析")
    tab1,tab2,tab3 = st.tabs(["📊 策略分析","🌍 市场解读","🧬 自学习进化"])
    db = st.session_state.db
    try: all_r = db.get_latest_results()
    except: all_r = pd.DataFrame()
    results = all_r.to_dict("records") if not all_r.empty else []

    with tab1:
        if results:
            names = sorted(set(r.get("strategy_name","") for r in results))
            mode = st.radio("模式",["单策略","多策略对比"],horizontal=True)
            if mode=="单策略":
                sel = st.selectbox("选择策略",names)
                r = next((x for x in results if x.get("strategy_name")==sel),None)
                if r and st.button("开始分析",type="primary"):
                    with st.spinner("AI分析中..."):
                        try:
                            from core.ai_analyzer import AIAnalyzer
                            st.markdown(AIAnalyzer(st.session_state.get("ai_provider","deepseek")).analyze_strategy(r))
                        except Exception as e: st.error(f"失败: {e}")
            else:
                sel = st.multiselect("选择",names,default=names[:3])
                if sel and st.button("开始对比",type="primary"):
                    with st.spinner("分析中..."):
                        try:
                            from core.ai_analyzer import AIAnalyzer
                            filtered = [x for x in results if x.get("strategy_name") in sel]
                            st.markdown(AIAnalyzer(st.session_state.get("ai_provider","deepseek")).compare_strategies(filtered))
                        except Exception as e: st.error(f"失败: {e}")
        else: st.info("暂无数据")

    with tab2:
        if st.button("🌍 分析市场环境",type="primary"):
            with st.spinner("分析中..."):
                try:
                    from core.ai_analyzer import AIAnalyzer
                    st.markdown(AIAnalyzer(st.session_state.get("ai_provider","deepseek")).market_analysis())
                except Exception as e: st.error(f"失败: {e}")
        try:
            import baostock as bs
            import pandas as pd
            with st.spinner("获取市场数据..."):
                lg = bs.login()
                rs = bs.query_history_k_data_plus("sh.000001", "date,close,volume",
                    start_date=datetime.now().strftime("%Y%m%d"), end_date=datetime.now().strftime("%Y%m%d"),
                    frequency="d", adjustflag="3")
                rows = []
                while rs.error_code == "0" and rs.next():
                    rows.append(rs.get_row_data())
                bs.logout()
            if rows:
                st.info("上证指数今日数据获取成功（BaoStock）")
            else:
                st.info("今日数据暂未更新（非交易时间）")
        except Exception as e:
            st.warning(f"数据获取失败: {e}")

    with tab3:
        st.markdown("### 🧬 AI 自学习进化引擎")
        st.markdown('<div style="padding:15px;background:#161b22;border-radius:8px;border:1px solid #30363d;margin-bottom:15px;"><p style="color:#8b949e;">AI引擎分析历史回测数据，识别策略退化、发现参数优化方向、建议新策略。每周日自动运行。</p></div>',unsafe_allow_html=True)
        if st.button("🔬 触发自学习",type="primary"):
            with st.spinner("学习中..."):
                try:
                    from core.ai_analyzer import AIAnalyzer
                    st.markdown(AIAnalyzer(st.session_state.get("ai_provider","deepseek")).auto_learn(results))
                except Exception as e: st.error(f"失败: {e}")


# ═══════════════════════════════════════════
# 页面5: 回测报告
# ═══════════════════════════════════════════
def page_reports():
    st.title("📋 回测报告")
    db = st.session_state.db
    c1,c2 = st.columns(2)
    with c1:
        if st.button("📄 生成日报",type="primary",use_container_width=True):
            try:
                from utils.report import generate_daily_report
                results = db.get_latest_results().to_dict("records")
                if results:
                    p = REPORTS_DIR/f"report_{datetime.now().strftime('%Y%m%d')}.html"
                    generate_daily_report(results,p); st.success(f"已生成: {p}")
                else: st.warning("无数据")
            except Exception as e: st.error(f"失败: {e}")
    with c2:
        if st.button("📥 导出Excel",use_container_width=True):
            try:
                import io
                results = db.get_latest_results()
                buf = io.BytesIO()
                with pd.ExcelWriter(buf,engine="openpyxl") as w: results.to_excel(w,sheet_name="回测结果",index=False)
                st.download_button("下载Excel",buf.getvalue(),file_name=f"quant_{datetime.now().strftime('%Y%m%d')}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e: st.error(f"失败: {e}")
    st.markdown("---")
    try:
        all_r = db.get_backtest_results()
        if not all_r.empty:
            st.markdown("### 历史记录")
            st.dataframe(all_r[["strategy_name","start_date","end_date","annual_return","max_drawdown","sharpe_ratio","created_at"]].sort_values("created_at",ascending=False).head(50),hide_index=True,use_container_width=True)
    except: pass
    st.markdown("---")
    st.markdown("### 日报预览")
    try:
        results = db.get_latest_results().to_dict("records")
        if results:
            from utils.report import generate_daily_report
            st.components.v1.html(generate_daily_report(results),height=700,scrolling=True)
    except Exception as e: st.warning(f"预览失败: {e}")


# ═══════════════════════════════════════════
# 页面6: 系统设置
# ═══════════════════════════════════════════
def page_settings():
    st.title("⚙️ 系统设置")
    tab1,tab2,tab3 = st.tabs(["🔑 API配置","📝 自定义策略","📊 数据管理"])

    with tab1:
        st.markdown("### AI 模型 API Key")
        from config import AI_PROVIDERS
        for key,cfg in AI_PROVIDERS.items():
            new_key = st.text_input(f"{cfg['name']} API Key",value=cfg.get("api_key",""),key=f"key_{key}",type="password")
            if new_key and new_key != cfg.get("api_key",""):
                env_path = ROOT_DIR/".env"
                env_lines = []
                if env_path.exists(): env_lines = env_path.read_text(encoding="utf-8").splitlines()
                env_key = f"{key.upper()}_API_KEY"
                found = False
                for i,line in enumerate(env_lines):
                    if line.startswith(f"{env_key}="): env_lines[i]=f"{env_key}={new_key}"; found=True; break
                if not found: env_lines.append(f"{env_key}={new_key}")
                env_path.write_text("\n".join(env_lines),encoding="utf-8")
                import os; os.environ[env_key]=new_key; cfg["api_key"]=new_key
                st.success(f"{cfg['name']} 已保存")
        st.markdown("---")
        st.markdown("""### 获取API Key\n- **DeepSeek**: https://platform.deepseek.com/api_keys (推荐)\n- **智谱AI**: https://open.bigmodel.cn/\n- **OpenAI**: https://platform.openai.com/api-keys""")

    with tab2:
        st.markdown("### 上传自定义策略")
        uploaded = st.file_uploader("选择.py文件",type=["py"])
        if uploaded:
            st.code(uploaded.read().decode("utf-8"),language="python")
            save_path = ROOT_DIR/"uploads"/uploaded.name
            with open(save_path,"wb") as f: f.write(uploaded.getvalue())
            st.success(f"已保存: {save_path}")

    with tab3:
        st.markdown("### 数据管理")
        c1,c2,c3 = st.columns(3)
        with c1:
            if st.button("🗑️ 清空回测",use_container_width=True):
                try:
                    conn=st.session_state.db._get_conn()
                    conn.execute("DELETE FROM backtest_results");conn.execute("DELETE FROM daily_values");conn.execute("DELETE FROM trade_records");conn.commit();st.success("已清空")
                except Exception as e: st.error(str(e))
        with c2:
            if st.button("🗑️ 清空AI报告",use_container_width=True):
                try:
                    conn=st.session_state.db._get_conn();conn.execute("DELETE FROM ai_reports");conn.commit();st.success("已清空")
                except Exception as e: st.error(str(e))
        with c3:
            if st.button("⚠️ 重置数据库",use_container_width=True):
                try:
                    from config import DB_PATH
                    if DB_PATH.exists(): DB_PATH.unlink(); st.success("已重置"); st.rerun()
                except Exception as e: st.error(str(e))

        st.markdown("---")
        st.markdown("### 公网部署")
        st.code("""# Cloudflare Tunnel (推荐)
cloudflared tunnel --url http://localhost:8501

# ngrok
ngrok http 8501

# Docker
docker build -t quant-analyzer .
docker run -p 8501:8501 quant-analyzer

# Streamlit Cloud (免费)
# 推送GitHub后连接 streamlit.io/cloud""", language="bash")


# ═══════════════════════════════════════════
# 主路由
# ═══════════════════════════════════════════
page = render_sidebar()
page_map = {
    "📊 策略总览": page_overview,
    "⚔️ 策略对比": page_compare,
    "📈 策略详情": page_detail,
    "🤖 AI 分析": page_ai,
    "📋 回测报告": page_reports,
    "⚙️ 系统设置": page_settings,
}
page_map.get(page, page_overview)()
