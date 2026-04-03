FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl && \
    rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

# HF Spaces 固定端口 7860
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLECORS=false
ENV STREAMLIT_SERVER_ENABLEXSRF=false

# 健康检查
HEALTHCHECK CMD curl -f http://localhost:7860/_stcore/health || exit 1

# 暴露端口
EXPOSE 7860

# 启动 (enhanced_app.py 是 v4.0 主入口)
CMD ["streamlit", "run", "enhanced_app.py", "--server.port=7860", "--server.headless=true", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
