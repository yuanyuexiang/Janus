# Backend —— FastAPI + Anthropic + MCP servers
# 不需要 amd64 限定，跑啥架构都行（不依赖 Choice SDK）
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 缓存层：先装依赖
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev || uv sync

# 应用代码
COPY app /app/app
COPY alembic.ini /app/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
