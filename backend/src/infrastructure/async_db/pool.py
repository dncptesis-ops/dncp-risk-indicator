import asyncpg
from src.config import settings


async def create_async_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        ssl=settings.db_sslmode,
        min_size=2,
        max_size=20,
        command_timeout=60,
    )
