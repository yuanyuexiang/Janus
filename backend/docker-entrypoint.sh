#!/bin/sh
# 容器启动：先把数据库迁移到最新，再起服务。
# 迁移失败直接退出（set -e），不让一个没有表的库带病启动。
set -e

echo "[entrypoint] 执行数据库迁移 alembic upgrade head ..."
uv run alembic upgrade head

echo "[entrypoint] 启动 uvicorn ..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
