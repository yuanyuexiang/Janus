# Backend —— FastAPI + Anthropic + MCP servers
# 不需要 amd64 限定，跑啥架构都行（不依赖 Choice SDK）
FROM python:3.12-slim

# PyPI 镜像（国内连 ghcr.io / pypi.org 常超时）。海外构建可传
# --build-arg PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 不装 apt（deb.debian.org 在国内常被代理拦）：
# python:slim 自带 ca-certificates；healthcheck 改用镜像自带的 python 发请求，不需要 curl。
# 不从 ghcr.io 拷 uv（国内连不上），改用 pip 从镜像装；uv sync 也走该镜像。
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} uv
ENV UV_DEFAULT_INDEX=${PIP_INDEX_URL}

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
