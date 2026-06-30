FROM python:3.11-slim
WORKDIR /app

# 先复制依赖文件并安装
COPY pyproject.toml .
COPY src/ src/
RUN pip install -e .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT/')" || exit 1

CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}