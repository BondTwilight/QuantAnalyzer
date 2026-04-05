"""
📚 策略知识库 - 量化策略体系与因子知识
基于安达量化、牧之林、Dirac、易涨EasyUp/OpenClaw 等实战经验整理
"""

import streamlit as st

def render():
    st.markdown("""
    <div style="text-align:center; padding:20px 0 10px;">
        <h1 style="font-size:2.5em; margin:0;">📚 策略知识库</h1>
        <p style="color:#888; font-size:1.1em;">量化策略体系 · 因子知识 · 实战经验</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 策略体系", "🧬 因子分类", "💡 实战技巧", "🦞 OpenClaw生态", "📖 来源说明"])

    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 超跌反弹策略")
            st.markdown("""
            **核心逻辑**: 价格超跌后均值回归
            
            **关键因子**:
            - **超跌程度**: RSI < 30、偏离均线幅度 > -10%
            - **恐慌信号**: 连续大跌3天以上、放量下跌
            - **反转信号**: 下影线长、成交量萎缩后放大
            
            **适用场景**:
            - ✅ 震荡市/熊市底部
            - ✅ ETF/指数（不会归零）
            - ❌ 单边下跌趋势（容易接飞刀）
            
            **风控要点**:
            - 必须设止损线（-5%~-8%）
            - 分批建仓，不要一把梭
            - 关注市场整体情绪（VIX恐慌指数）
            """)

            st.markdown("### 📊 动量趋势策略")
            st.markdown("""
            **核心逻辑**: 强者恒强，趋势延续
            
            **关键因子**:
            - **价格动量**: 20日/60日涨幅排名
            - **均线系统**: 多头排列、金叉信号
            - **趋势强度**: ADX > 25 表示趋势明确
            
            **适用场景**:
            - ✅ 结构性行情
            - ✅ 行业轮动明显时
            - ❌ 震荡市（频繁假突破）
            """)

        with col2:
            st.markdown("### 🔄 均值回归策略")
            st.markdown("""
            **核心逻辑**: 价格偏离均值后会回归
            
            **关键因子**:
            - **统计偏差**: Z-Score > 2 或 < -2
            - **布林带**: 触及上轨卖出/下轨买入
            - **协整关系**: 配对交易的价差回归
            
            **适用场景**:
            - ✅ 高频数据、日内交易
            - ✅ 配对交易（相关性高的品种）
            - ❌ 趋势强烈的行情
            """)

            st.markdown("### 📈 量价配合策略")
            st.markdown("""
            **核心逻辑**: 成交量确认价格信号
            
            **关键因子**:
            - **量价背离**: 价格新高但量未确认 = 危险
            - **缩量回调**: 健康的回调，可以加仓
            - **放量突破**: 真实突破的概率高
            
            **黄金法则**:
            - "量在价先" — 先看量再看价
            - "缩量阴"比"放量阳"更值得关注
            """)

    with tab2:
        st.markdown("## 🧬 因子分类大全")
        
        # 因子分类表格
        factor_data = {
            "类别": ["价格类", "价格类", "价格类", "动量类", "动量类", 
                    "波动率类", "量价类", "量价类", "统计类", "情绪类"],
            "因子名称": ["MA偏离度", "布林带位置", "高低点比率", "RSI", "MACD",
                       "ATR波动率", "量价比", "换手率变化", "Z-Score", "涨跌家数比"],
            "计算方式": ["(收盘-MA20)/MA20", "(下轨-收盘)/带宽", "最高/最低-1",
                       "14日RSI值", "DIF-DEA差值", "14日平均波幅",
                       "成交额/市值", "今日换手-5日均量", "(值-均值)/标准差",
                       "上涨家数/下跌家数"],
            "预期方向": ["均值回归", "均值回归", "趋势", "反转", "趋势跟随",
                        "反向", "正向", "反转", "均值回归", "情绪指标"],
            "常用场景": ["震荡市", "区间交易", "趋势判断", "超买超卖", "趋势确认",
                       "仓位管理", "选股", "短线", "配对交易", "大盘判断"]
        }
        st.dataframe(factor_data, use_container_width=True, hide_index=True)
        
        st.markdown("### 🔥 高价值因子 Top 5")
        top_factors = [
            ("🥇 IC最高的因子", "成交量变化率 + RSI反转组合", "IC ≈ 0.06~0.08"),
            ("🥈 最稳定的因子", "均线偏离度的Z-Score", "月胜率 > 55%"),
            ("🥉 最实用的因子", "放量突破信号", "假突破率低"),
            ("4️⃣ 最被低估的因子", "日内振幅(ATR)变化", "波动率聚类效应"),
            ("5️⃣ 最有潜力的因子", "北向资金流向变化", "聪明钱效应"),
        ]
        for name, desc, note in top_factors:
            st.markdown(f"**{name}**: {desc} *({note})*")

    with tab3:
        st.markdown("## 💡 实战经验总结")
        
        st.markdown("### ⚠️ 新手必踩的坑")
        pitfalls = [
            ("过拟合陷阱", "回测完美但实盘亏损", "用样本外数据验证、减少参数数量"),
            ("幸存者偏差", "只研究成功的股票", "纳入退市股票、考虑破产风险"),
 ("前视偏差", "用了未来信息", "严格按时间顺序、只用当时可得的数据"),
            ("手续费忽视", "高频策略利润被吃光", "真实计算双边佣金+滑点"),
 ("容量限制", "小资金可行大资金不行", "测试不同资金规模的冲击成本"),
        ]
        for title, problem, solution in pitfalls:
            with st.expander(f"❌ {title}: {problem}"):
                st.markdown(f"**解决方案**: {solution}")
        
        st.markdown("### ✅ 高手习惯")
        habits = [
            ("每天记录交易决策", "写下为什么买/卖，月底复盘时非常有价值"),
            ("固定时间运行策略", "避免情绪化操作，让规则说了算"),
            ("永远设止损", "单笔亏损不超过总资金的2%"),
            ("多策略分散", "不要把所有鸡蛋放一个篮子里"),
            ("持续学习进化", "市场在变，策略也要跟上——这就是AlphaForge存在的意义！"),
        ]
        for title, desc in habits:
            st.success(f"**{title}**: {desc}")

    with tab4:
        st.markdown("## 🦞 OpenClaw × 易涨EasyUp 工作流精粹")
        st.markdown("""> **来源**: 抖音博主「易涨EasyUp🦞」(10万粉丝) + OpenClaw 开源AI Agent框架 (GitHub 69.7k Stars)
        """)
        
        st.markdown("### 🔥 核心工作流架构")
        st.code("""
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  大模型层     │───▶│ Agent调度层  │───▶│  交易执行层  │
│ (阿里云百炼) │    │ (OpenClaw)   │    │ (QMT-MCP)   │
└──────────────┘    └──────┬───────┘    └──────────────┘
                           │
                 ┌─────────▼─────────┐
                 │   数据层 (Skill)   │ ← 98个标准化接口
                 │ akshare-data Skill │
                 │ tushare-data Skill │
                 │ eastmoney Skill    │
                 └─────────┬─────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                   ▼
   ┌──────────┐      ┌──────────┐       ┌──────────┐
   │  AKShare  │      │ Tushare  │       │ BaoStock  │
   │ 免费/无Token│    │ 免费积分制│       │ 免费/稳定 │
   └──────────┘      └──────────┘       └──────────┘
        """, language="text")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 开源三件套")
            st.markdown("""
            | 组件 | 项目 | 功能 |
            |------|------|------|
            | **数据源** | AKShare/Tushare/BaoStock | 原材料 |
            | **加工厂** | Qlib (微软开源) | 特征工程+回测 |
            | **智能质检** | RD-Agent | AI因子挖掘 |
            
            **实测效果**: 回测年化59%收益率（需谨慎看待过拟合风险）
            """)
            
            st.markdown("### 💡 易涨的数据哲学")
            st.success("""
            > **"好几个和在一起用、一个不行"** 
            > —— 易涨EasyUp 在评论区的回复
            
            - ❌ 不依赖单一数据源
            - ✅ 多源聚合 + 自动降级
            - ✅ 免费优先 + 付费兜底
            - ✅ 稳定性 > 实时性（对于回测场景）
            """)
        
        with col2:
            st.markdown("### 🛠️ 数据源对比（易涨推荐）")
            data_source_data = {
                "数据源": ["AKShare ⭐", "东方财富", "Tushare Pro", "BaoStock", "长桥SDK"],
                "费用": ["免费", "免费", "免费积分", "免费", "需注册"],
                "特点": ["98+接口多源聚合", "实时行情强", "数据规范", "A股日线稳定", "港股/美股"],
                "适用场景": ["主力数据源", "实时监控", "量化研究", "历史回测", "跨市场"],
            }
            st.dataframe(data_source_data, use_container_width=True, hide_index=True)
            
            st.markdown("### 🚀 部署方案")
            st.markdown("""
            | 环境 | 方案 | 成本 |
            |------|------|------|
            | **阿里云ECS** | 预装镜像, 放行18789端口 | ~50元/月 |
            | **Windows 11** | PowerShell + npm install -g openclaw | 免费 |
            | **Docker** | 容器化部署 | 免费 |
            | **HuggingFace** | Spaces Docker | 免费 |
            """)

        st.markdown("### 📚 EasyUp 核心视频作品")
        easyup_videos = [
            ("🎬 AGENT 数据层揭秘", "2026-03-16", "#openclaw #量化编程"),
            ("🛠️ SKILL分享之东财篇", "2026-03-14", "2144赞 #openclaw #skills"),
            ("💰 免费数据源解析", "2026-03-23", "4954赞 #openclaw #aiagent"),
            ("🎉 v1.0.0 RELEASED！", "2026-03-22", "4663赞 #ai #agent #量化交易"),
            ("🤖 AI交易搭档Day1", "2026-03", "竞价→盘中→收盘→飞书推送"),
            ("📈 板块联动量化 AI Agent开发实录", "2026-03-30", "#openclaw #量化交易策略"),
        ]
        for title, date, tags in easyup_videos:
            st.markdown(f"**{title}** ({date}) — `{tags}`")

        st.markdown("### 🔗 关键资源链接")
        resources = [
            ("🦞 OpenClaw GitHub (69.7k⭐)", "https://github.com/openclaw/openclaw", "AI Agent框架核心项目"),
            ("📦 ClawHub 技能市场", "https://github.com/openclaw/clawhub", "Skill目录与发现平台"),
            ("🌐 SkillsBot 中文站", "https://www.skillsbot.cn/", "中文技能库与教程"),
            ("📊 Qlib 微软量化", "https://github.com/microsoft/qlib", "AI-oriented量化投资平台"),
            ("🧬 RD-Agent 因子挖掘", "https://quant-wiki.com/", "LLM自动化因子挖掘工具"),
            ("📈 AKShare 数据接口", "https://github.com/akfamily/akshare", "Python金融数据接口库"),
            ("🔗 QMT-MCP 交易桥接", "https://github.com/guangxiangdebizi/QMT-MCP", "OpenClaw→QMT交易执行"),
            ("🎬 EasyUp 抖音主页", "https://v.douyin.com/2zV2myrh1Eg/", "博主主页"),
        ]
        for name, url, desc in resources:
            st.markdown(f"- **{name}**: [{url}]({url}) — {desc}")

        st.info("💡 **提示**: 本页面内容来自对「易涨EasyUp」公开视频和网络资料的研究整理，仅供学习参考。")

    with tab5:
        st.markdown("## 📖 知识来源与致谢")
        
        st.markdown("""
        本知识库整合了以下来源的经验和研究成果：
        """)
        
        sources = [
            ("🦞 易涨EasyUp（抖音）", "10万粉丝，开源量化AI Agent实践者", 
             "https://v.douyin.com/2zV2myrh1Eg/",
             "OpenClaw数据层架构、多源聚合策略、akshare-data Skill(98接口)、Qlib+RD-Agent三件套、免费数据源解析、板块联动量化、东方财富Skill、飞书自动化推送"),
            ("🔴 安达量化（小红书）", "32篇笔记，6大策略体系", 
             "https://www.xiaohongshu.com/user/profile/58a8f6d36e23de2b9810b9b7",
             "超跌反弹、多因子选股、动量趋势、均线系统、量价分析、波动率策略"),
            ("🟠 牧之林（小红书）", "7篇核心笔记，8699赞藏", 
             "https://xhslink.com/m/3L64RhKhyN7",
             "量化策略研究系统设计、AI辅助量化、Databento数据处理、IBKR实盘接口"),
            ("🟡 Dirac（小红书）", "31篇实战笔记，1.2万赞藏 ⭐", 
             "https://xhslink.com/m/1ulKs8082VS",
             "多因子策略设计(110赞)、经典红利低波小市值(149赞)、量化私募经历(296赞)\n因子清洗与正规化、失效因子分析、ETF轮动策略、基座架构设计、实盘风控"),
            ("🟢 WorldQuant BRAIN", "Alpha101 因子库", 
             "https://platform.worldquantbrain.com/learn/documentation/discover-brain/formula-methodology",
             "101个经典因子表达式、因子评估方法论"),
            ("🔵 学术论文", "AlphaAgent (KDD 2025)", 
             "arxiv.org/abs/2507.xxxxx",
             "遗传编程自动因子挖掘、表达式树优化"),
            ("⚪ OpenClaw 生态", "GitHub 69.7k Stars AI Agent框架", 
             "https://github.com/openclaw/openclaw",
             "MCP协议集成、自然语言驱动交易、多智能体协作、Skill插件生态"),
        ]
        
        for name, desc, url, content in sources:
            st.markdown(f"""---
            ### {name}
            **简介**: {desc}  
            **链接**: [{url}]({url})  
            **贡献内容**: {content}
            """)
        
        st.info("💡 **提示**: 策略知识会持续更新。如果你发现好的量化资源，可以在 GitHub 提 PR 或 Issue 建议添加！")

    # ── Dirac 实战经验专区（额外标签）──
    with st.expander("🌟 Dirac 实战精华（1.2万赞藏 · 31篇笔记）", expanded=False):
        st.markdown("""
        **博主背景**: 后端工程师 @ 四川大学，两段量化私募经历，实盘验证者
        """)
        
        st.markdown("#### 🔥 最受欢迎的笔记 Top 5")
        dirac_top = [
            ("🏆 谈谈我的两段量化私募经历", "296赞", "量化私募内部运作、策略开发流程、团队协作"),
            ("📊 经典红利低波小市值策略", "149赞", "风格因子组合：红利+低波+小市值的实证回测"),
            ("🧬 多因子策略设计思路", "110赞", "从因子池构建到组合优化的完整方法论"),
            ("🛡️ 回避不是放弃，而是为了苟住！", "79赞", "市场极端行情下的风控与仓位管理"),
            ("❌ 又是一个失效的因子", "59赞", "因子失效案例分析：过拟合、风格切换"),
        ]
        for title, likes, desc in dirac_top:
            st.markdown(f"**{title}** ({likes}): {desc}")
        
        st.markdown("#### 💎 核心观点提炼")
        st.markdown("""
        | 观点 | 来源笔记 | 要点 |
        |------|---------|------|
        | **基座的正确性决定生死** | (36赞) | 数据质量 > 模型复杂度；错误的回测框架会让一切归零 |
        | **因子必须清洗和正规化** | 因子清洗与正规化(16赞) | 去极值、标准化、中性化是因子有效的前提 |
        | **放弃暴富，控制仓位** | (15赞) | 仓位管理比选股更重要；凯利公式决定仓位上限 |
        | **3小时判断策略不值得深究** | (37赞) | 快速证伪能力 = 高效研究者；不要在烂策略上浪费时间 |
        | **一个没有失效的因子** | (40赞) | 寻找有经济逻辑支撑的因子；纯统计的因子迟早失效 |
        
        #### 🛠️ 技术栈推荐（来自 Dirac 笔记）
        - **语言**: Python（核心）、SQL（数据处理）
        - **回测框架**: 自建基座（强调正确性）或 Backtrader
        - **数据源**: AKShare / Tushare / 本地数据库
        - **AI辅助**: Cursor（20美元写量化）+ DeepSeek 分析
        - **部署**: 实盘前至少6个月模拟盘验证
        """)

if __name__ == "__main__":
    render()
