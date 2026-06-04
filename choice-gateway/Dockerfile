# Choice Gateway —— 强制 linux/amd64，因为 SDK .so 只编了 x86_64
# 在 Apple Silicon 上 docker-compose 会自动用 Rosetta 转译（慢一点，能跑）。
FROM --platform=linux/amd64 python:3.12-slim

# PyPI 镜像（国内连 ghcr.io / pypi.org 常超时）。海外构建可传
# --build-arg PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 不装 apt（deb.debian.org 在国内常被代理拦）：
# python:slim 自带 ca-certificates；healthcheck 改用镜像自带的 python 发请求，不需要 curl。
# 不从 ghcr.io 拷 uv（国内连不上），改用 pip 从镜像装；uv sync 也走该镜像。
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} uv
ENV UV_DEFAULT_INDEX=${PIP_INDEX_URL}

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
