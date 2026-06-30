FROM python:3.11-slim
WORKDIR /app

# 安装 PostgreSQL 客户端库（psycopg 依赖 libpq）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制所有代码
COPY . .

# 安装依赖
RUN pip install --no-cache-dir .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/')" || exit 1

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]