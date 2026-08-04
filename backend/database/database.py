"""异步数据库引擎与会话"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import CHROMA_DIR, DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI 依赖：请求级会话"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """建表 + 清理 ChromaDB 中已删除用户的孤儿向量"""
    import backend.database.models  # noqa: F401 — 注册全部模型

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _cleanup_orphan_chroma()


async def _cleanup_orphan_chroma():
    """删除 user 已不存在但仍留在向量库中的条目"""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        # 设置必须与 services/vector_store.py 完全一致，否则同进程内二次创建会被拒绝
        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR), settings=ChromaSettings(anonymized_telemetry=False)
        )
        collection = client.get_or_create_collection("user_memory")
        async with AsyncSessionLocal() as session:
            valid_ids = (await session.execute(text("SELECT id FROM users"))).scalars().all()
        valid = {str(i) for i in valid_ids}
        orphan_uids = set()
        for meta in collection.get()["metadatas"] or []:
            uid = str(meta.get("user_id", ""))
            if uid and uid not in valid:
                orphan_uids.add(uid)
        for uid in orphan_uids:
            collection.delete(where={"user_id": uid})
    except Exception:
        pass  # Chroma 不可用/空库时静默
