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
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 改密码哈希等运行时数据落在这里，compose 挂卷持久化
RUN mkdir -p /app/data

EXPOSE 8000

# 启动时先迁移再起服务
CMD ["/app/docker-entrypoint.sh"]
