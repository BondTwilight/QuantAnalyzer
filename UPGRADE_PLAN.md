# QuantAnalyzer v3.0 升级规划

## ✅ 已完成升级 (2026-04-02)

### Phase 1: 策略库补全
- [x] 补全缺失的 10 个策略实现
- [x] 新增策略总数: **20个**
- [x] 所有策略均可正常导入回测

**新增策略列表:**
| 策略 | 分类 | 难度 |
|------|------|------|
| ma_cross | 趋势跟踪 | ⭐ |
| macd | 趋势跟踪 | ⭐⭐ |
| bollinger | 均值回归 | ⭐⭐ |
| rsi_strategy | 均值回归 | ⭐ |
| momentum | 动量因子 | ⭐ |
| turtle | 趋势跟踪 | ⭐⭐ |
| dual_thrust | 趋势跟踪 | ⭐⭐ |
| ichimoku | 趋势跟踪 | ⭐⭐⭐ |
| multi_factor | 多因子 | ⭐⭐⭐ |
| sector_rotation | 动量因子 | ⭐⭐ |

### Phase 2: 量化平台对比页面
- [x] 新增 **量化平台对比** 页面 (🌐 导航)
- [x] 对比 12+ 主流量化平台
- [x] 包含: Backtrader/vn.py/QuantConnect/聚宽/QMT 等
- [x] 提供使用场景推荐

### Phase 3: AI模型精简
- [x] 从 17 个精简到 **7 个精选模型**
- [x] 保留最强免费模型:
  - 🔥 Cerebras (完全免费无限制)
  - ⭐ 智谱 GLM-4-Flash (国产首选)
  - ⚡ Groq (超快推理)
  - 🇨🇳 SiliconFlow (国内聚合)
  - 🧠 DeepSeek (推理能力强)

### Phase 4: 文件上传功能
- [x] 支持直接上传 .py 策略文件
- [x] 自动检测 Backtrader 策略类
- [x] 一键回测上传的策略
- [x] 粘贴代码功能可用

---

## 🎯 升级目标
从"回测工具"升级为**量化策略AI学习平台**，核心能力：
1. 自动采集开源策略 → 策略库丰富
2. 粘贴任意策略代码 → AI自动分析
3. 多模型协同分析 → 免费AI大脑
4. 每日自动运行 → 持续学习进化

---

## 📐 架构设计

### 新增模块

```
quant-analyzer/
├── core/
│   ├── ai_analyzer.py      # 🔧 重构: 多模型路由+协同
│   ├── engine.py           # 保持不变
│   ├── metrics.py          # 保持不变
│   ├── scheduler.py        # 保持不变
│   └── strategy_parser.py  # 🆕 策略代码解析器
├── strategy_library/       # 🆕 内置策略库 (从GitHub采集)
│   ├── __init__.py
│   ├── registry.json       # 策略元数据索引
│   ├── ma_cross.py
│   ├── macd.py
│   ├── rsi.py
│   ├── bollinger.py
│   ├── dual_thrust.py      # 聚宽经典
│   ├── turtle.py           # 海龟交易
│   ├── momentum.py
│   ├── mean_reversion.py   # 均值回归
│   ├── pair_trading.py     # 配对交易
│   ├── vwap.py             # VWAP策略
│   ├── factor_timing.py    # 因子择时
│   ├── sector_momentum.py  # 板块动量
│   ├── vol_breakout.py     # 波动率突破
│   └── ... (持续扩展)
├── app.py                  # 🔧 重构: 新增策略库+解析页面
└── config.py               # 🔧 重构: AI多模型配置
```

### AI 多模型架构

```python
# 三层模型架构
AI_MODELS = {
    # 第一层: 快速分析 (免费无限制)
    "tier1_fast": ["glm-4-flash", "gemini-1.5-flash", "groq-llama3-70b"],
    
    # 第二层: 深度分析 (免费有限额) 
    "tier2_deep": ["deepseek-chat", "qwen-turbo", "moonshot-v1-8k"],
    
    # 第三层: 专家分析 (用户自备Key)
    "tier3_expert": ["gpt-4o", "claude-3.5-sonnet", "glm-4-plus"],
}

# 协同分析流程:
# 1. 策略代码解析 → tier1_fast (3个模型并行)
# 2. 回测结果深度分析 → tier2_deep (2个模型)
# 3. 投资建议综合 → tier1_fast (最终整合)
# 4. 如有tier3 key → 额外专家评审
```

### 策略代码解析器

```python
# 支持解析的策略格式:
# 1. Backtrader Strategy 类 (直接导入)
# 2. 聚宽研究平台代码 (自动转换为Backtrader)
# 3. 果仁网策略描述 (AI辅助转换为代码)
# 4. 任意Python交易逻辑 (AST解析+沙盒回测)
# 5. 伪代码/自然语言描述 (AI生成Backtrader策略)
```

---

## 📋 详细任务清单

### Phase 1: AI多模型引擎 (优先级最高)
- [ ] 1.1 接入 Google Gemini (免费, 无需信用卡)
- [ ] 1.2 接入 Groq (免费, 超快推理)
- [ ] 1.3 接入 DeepSeek (免费额度)
- [ ] 1.4 接入 通义千问/Qwen (免费额度)
- [ ] 1.5 接入 Moonshot/Kimi (免费额度)
- [ ] 1.6 接入 Cerebras (免费推理)
- [ ] 1.7 接入 SiliconFlow (免费国内大模型聚合)
- [ ] 1.8 多模型协同分析框架
- [ ] 1.9 模型自动故障转移
- [ ] 1.10 模型健康监控面板

### Phase 2: 策略代码解析器
- [ ] 2.1 Backtrader策略直接加载
- [ ] 2.2 AST语法分析器 (检测策略结构)
- [ ] 2.3 AI辅助策略代码理解 (识别买卖逻辑)
- [ ] 2.4 策略代码安全沙盒
- [ ] 2.5 聚宽代码转换器
- [ ] 2.6 策略代码评分 (可回测性、风险等级)

### Phase 3: 内置策略库扩展
- [ ] 3.1 从GitHub采集高质量开源策略
- [ ] 3.2 策略元数据索引 (registry.json)
- [ ] 3.3 策略分类体系 (趋势/反转/均值回归/多因子...)
- [ ] 3.4 策略搜索和筛选
- [ ] 3.5 一键回测任意策略
- [ ] 3.6 策略详情页 (代码+说明+历史表现)

### Phase 4: 智能分析升级
- [ ] 4.1 策略代码自动解读
- [ ] 4.2 多维度AI分析报告
- [ ] 4.3 策略对比AI评审
- [ ] 4.4 市场环境AI解读
- [ ] 4.5 自学习进化引擎

### Phase 5: UI/UX升级
- [ ] 5.1 策略库浏览页面
- [ ] 5.2 策略代码编辑器 (粘贴+编辑)
- [ ] 5.3 AI分析面板 (多模型并行展示)
- [ ] 5.4 模型状态监控
- [ ] 5.5 策略收藏夹

### Phase 6: 部署与测试
- [ ] 6.1 HF Space部署测试
- [ ] 6.2 性能优化
- [ ] 6.3 文档更新
