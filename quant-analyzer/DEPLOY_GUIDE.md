# QuantBrain 云部署指南

## ✅ 已完成的准备工作

1. ✅ 代码已推送到 GitHub: `https://github.com/BondTwilight/QuantAnalyzer`
2. ✅ Dockerfile 已适配 HuggingFace Spaces (端口7860)
3. ✅ GitHub Cloud Storage 模块已实现 (跨会话数据持久化)
4. ✅ Streamlit 配置已优化
5. ✅ Cloudflare Workers 反代脚本已准备

---

## 📋 你需要完成的操作（3步，约15分钟）

### 第1步：创建 HuggingFace Space（5分钟）

1. **注册/登录** HuggingFace: https://huggingface.co/join
2. 点击右上角头像 → **New Space**
3. 填写信息:
   - **Space name**: `quantbrain`
   - **License**: MIT
   - **SDK**: 选择 **Docker**
   - **Visibility**: Public
4. 创建完成后，进入 Space 的 **Settings** 选项卡:
   - 找到 **Repository** 区域
   - 点击 **Connect to GitHub** 或 **Clone from GitHub**
   - 输入仓库地址: `https://github.com/BondTwilight/QuantAnalyzer.git`
   - **子目录**: `quant-analyzer`（重要！代码在子目录里）
5. 在 **Settings → Variables and secrets** 中添加:
   - **Secret** → `GITHUB_TOKEN` = 你的 GitHub Personal Access Token
   - **Secret** → `GITHUB_STORAGE_REPO` = `BondTwilight/QuantAnalyzer`

**获取 GitHub Token**: 
- 打开 https://github.com/settings/tokens
- Generate new token (classic)
- 勾选 `repo` 权限
- 复制生成的 token

6. 等待构建完成（约5-10分钟），你会得到一个地址:
   `https://bondtwilight-quantbrain.hf.space`

---

### 第2步：配置 Cloudflare Workers 反代（5分钟，国内直连用）

1. **登录** Cloudflare: https://dash.cloudflare.com
2. 进入 **Workers & Pages** → **Create Worker**
3. 给 Worker 起个名字（如 `quantbrain-proxy`）
4. 点击 **Edit Code** → 清空默认代码 → 粘贴 `cloudflare-worker.js` 的内容
5. 修改第8行的 URL 为你的实际 Space 地址:
   ```javascript
   const HF_SPACE_URL = "https://bondtwilight-quantbrain.hf.space";
   ```
6. 点击 **Save and Deploy**
7. 你会得到一个 Workers 地址，如:
   `https://quantbrain-proxy.你的用户名.workers.dev`

**可选 - 绑定自定义域名**:
- Workers 设置 → Triggers → Custom Domains
- 添加你的域名（如 `quant.yourdomain.com`）

---

### 第3步：更新 cloudflare-worker.js 中的 URL（1分钟）

拿到 HuggingFace Space 地址后，更新仓库中的反代脚本并推送:
```bash
cd QuantAnalyzer/quant-analyzer
# 编辑 cloudflare-worker.js 第8行
git add cloudflare-worker.js
git commit -m "update: CF worker target URL"
git push origin master
```

---

## 🔗 最终访问地址

| 方式 | 地址 | 特点 |
|------|------|------|
| HuggingFace 直连 | `https://bondtwilight-quantbrain.hf.space` | 海外快，国内可能慢 |
| Cloudflare Workers 反代 | `https://quantbrain-proxy.xxx.workers.dev` | 国内直连快 |
| 自定义域名 | `https://quant.yourdomain.com` | 最专业 |

---

## 💾 数据持久化说明

通过 GitHub Contents API 实现:
- 信号数据 → `cloud_data/signals.json`
- 持仓数据 → `cloud_data/portfolio.json`
- 策略知识库 → `cloud_data/strategy_knowledge.json`
- 学习日志 → `cloud_data/learning_log.json`

这些文件存储在你的 GitHub 仓库 `BondTwilight/QuantAnalyzer` 的 `cloud_data/` 目录中，
每次数据变更时自动同步，容器重启不丢失。

---

## ⚠️ 注意事项

1. **BaoStock 数据源**: HuggingFace 服务器在海外，BaoStock 是国内服务，可能会有延迟。
   如遇数据获取问题，可在 HF Secrets 中设置 HTTP 代理。
2. **首次冷启动**: Space 长时间无人访问会休眠，首次打开需等 5-15 秒。
3. **API 限流**: GitHub API 限流 5000次/小时（认证用户），日常使用足够。
4. **GLM API Key**: 已硬编码在 config.py 中，HF Spaces 可直接使用。
