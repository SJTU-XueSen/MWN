"""数据库连接管理"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_URL

async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 清理 ChromaDB 中任何与当前 DB 用户不匹配的孤立向量
    try:
        from services.vector_store import _get_collection
        col = _get_collection()
        # 获取 SQLite 中存在的所有 user_id
        from database.models import User
        from sqlalchemy import select as sa_select
        async with AsyncSessionLocal() as s:
            users = (await s.execute(sa_select(User.id))).scalars().all()
        valid_ids = {str(u) for u in users}
        # 获取 ChromaDB 中所有 user_id
        all_chroma = col.get()
        if all_chroma and all_chroma.get("metadatas"):
            orphan_ids = set()
            for meta in all_chroma["metadatas"]:
                uid = meta.get("user_id", "")
                if uid and uid not in valid_ids:
                    orphan_ids.add(uid)
            # 删除孤立数据
            for oid in orphan_ids:
                try:
                    col.delete(where={"user_id": oid})
                except Exception:
                    pass
    except Exception:
        pass  # ChromaDB 可能未初始化，忽略
