import asyncio
from sqlalchemy import text
from app.core.db import engine


async def main():
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "select data_type, udt_name "
                "from information_schema.columns "
                "where table_name='supplies' and column_name='status'"
            )
        )
        print("STATUS_COLUMN =", r.first())


asyncio.run(main())
