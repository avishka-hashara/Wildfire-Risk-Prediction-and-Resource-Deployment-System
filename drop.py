import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def drop_table():
    engine = create_async_engine('postgresql+asyncpg://postgres:12345@localhost:5432/wildfiredb')
    async with engine.begin() as conn:
        await conn.execute(text('DROP TABLE IF EXISTS telemetry_logs'))
        print('Dropped telemetry_logs table to allow schema recreation.')
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(drop_table())
