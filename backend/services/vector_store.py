"""ChromaDB 语义记忆层 — 单一 Collection + user_id 强制过滤（数据铁律 3.3）

架构：单一 Collection `user_memory`，metadata.type 区分内容类型。
所有检索必须带 str(user_id) 过滤，禁止跨用户访问。
"""
import json
import os
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import CHROMA_DIR

COLLECTION_USER_MEMORY = "user_memory"

MEMORY_TYPE_AI_MEMORY = "ai_memory"
MEMORY_TYPE_JOURNAL = "journal"
MEMORY_TYPE_EVENT = "event"
MEMORY_TYPE_CHAT = "chat"
MEMORY_TYPE_REPORT = "report"

_client: Optional[chromadb.PersistentClient] = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _get_collection():
    return _get_client().get_or_create_collection(name=COLLECTION_USER_MEMORY)


def add_entry(
    entry_id: str,
    user_id: int,
    content: str,
    memory_type: str,
    metadata: Optional[dict] = None,
):
    """写入一条语义记忆（单一入口，user_id 强制 str 化）"""
    meta = {"user_id": str(user_id), "type": memory_type}
    if metadata:
        for k, v in metadata.items():
            meta[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
    _get_collection().add(ids=[str(entry_id)], documents=[content], metadatas=[meta])


def add_ai_memory(memory_id: int, user_id: int, content: str, metadata: Optional[dict] = None):
    add_entry(f"ai_memory:{memory_id}", user_id, content, MEMORY_TYPE_AI_MEMORY, metadata)


def add_journal(journal_id: int, user_id: int, content: str, metadata: Optional[dict] = None):
    add_entry(f"journal:{journal_id}", user_id, content, MEMORY_TYPE_JOURNAL, metadata)


def add_event(event_id: int, user_id: int, content: str, metadata: Optional[dict] = None):
    add_entry(f"event:{event_id}", user_id, content, MEMORY_TYPE_EVENT, metadata)


def add_chat_message(msg_id: int, user_id: int, content: str, metadata: Optional[dict] = None):
    add_entry(f"chat:{msg_id}", user_id, content, MEMORY_TYPE_CHAT, metadata)


def search(
    user_id: int,
    query: str,
    n_results: int = 10,
    memory_types: Optional[list[str]] = None,
) -> list[dict]:
    """语义检索用户记忆 — 只查当前用户（user_id 过滤）"""
    where = {"user_id": str(user_id)}
    if memory_types:
        where["type"] = {"$in": memory_types}

    results = _get_collection().query(query_texts=[query], n_results=n_results, where=where)
    if not results["ids"] or not results["ids"][0]:
        return []
    return [
        {
            "id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            "distance": results["distances"][0][i] if results["distances"] else None,
        }
        for i in range(len(results["ids"][0]))
    ]


def search_by_type(user_id: int, query: str, memory_type: str, n_results: int = 5) -> list[dict]:
    return search(user_id, query, n_results, memory_types=[memory_type])


def delete_user_data(user_id: int):
    """账户注销时删除用户全部向量"""
    try:
        _get_collection().delete(where={"user_id": str(user_id)})
    except Exception:
        pass


def count_user_entries(user_id: int) -> int:
    try:
        result = _get_collection().get(where={"user_id": str(user_id)})
        return len(result["ids"]) if result and result["ids"] else 0
    except Exception:
        return 0
