import asyncpg
import os

# PostgreSQL Connection
dbPool = None

async def init_database():
    global dbPool
    dbPool = await asyncpg.create_pool(
        database  =   os.getenv("DB_NAME"),
        user      =   os.getenv("DB_USERNAME"),
        password  =   os.getenv("DB_PWD"),
        host      =   os.getenv("DB_HOST"),
        port      =   int(os.getenv("DB_PORT")),
        min_size  =   1,
        max_size  =   15,
        timeout   =   30
    )
