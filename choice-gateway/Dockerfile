# Choice Gateway —— 强制 linux/amd64，因为 SDK .so 只编了 x86_64
# 在 Apple Silicon 上 docker-compose 会自动用 Rosetta 转译（慢一点，能跑）。
FROM --platform=linux/amd64 python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# uv 跨平台官方镜像（同源）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 1) 先装 Python 依赖（缓存友好）
COPY pyproject.toml ./
RUN uv sync --no-dev

# 2) 应用代码
COPY app /app/app

# 3) SDK：拷到固定路径 /sdk
#    PYTHONPATH=/sdk 让 `from EmQuantAPI import c` 能找到模块；
#    SDK 内部用 `__file__` 自定位 libs/linux/x64/.so，cwd 不重要。
#    libs/linux/x64/ 还是 userInfo 文件的写入目录 —— 挂卷在 compose 里。
COPY vendor/EmQuantAPI /sdk
ENV PYTHONPATH=/sdk

EXPOSE 9001

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9001"]
