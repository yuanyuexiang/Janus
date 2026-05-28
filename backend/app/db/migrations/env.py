import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 解析配置文件里的 Python logging 配置；这一行实际上是把 logger 装起来。
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.config import get_settings
from app.db.models import Base

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", get_settings().database_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """以「离线」模式跑迁移。

    这种模式只用 URL 配置 context，不真正建连接（建也行，只是没必要）。
    跳过 Engine 创建后甚至不需要本地装 DBAPI。

    `context.execute()` 在这里把 SQL 字符串输出到 stdout / 脚本里。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """这种模式下必须创建 Engine 并把连接挂到 alembic context 上。"""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """以「在线」模式跑迁移：真正建立数据库连接。"""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
