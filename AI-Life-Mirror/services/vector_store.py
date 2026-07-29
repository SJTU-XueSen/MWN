"""
Chroma 向量存储服务 — AI人生镜像的「人生记忆」层

架构决策：单一 Collection (user_memory) + metadata.type 区分内容类型。

原因：用户查询"我适合创业吗？"需要同时跨日记、事件、对话、
AI记忆检索，合并到一个 Collection 避免多路搜索 + merge + rerank。

与 SQLite 的分工：
  SQLite  → 结构化事实（谁、什么时候、什么事件、什么分数）
  Chroma  → 语义记忆（这件事意味着什么、用户的感受、隐含的价值观）
"""

import os
import json
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import BASE_DIR

CHROMA_DATA_DIR = os.path.join(BASE_DIR, "data", "chroma")
COLLECTION_USER_MEMORY = "user_memory"

# metadata.type 枚举
MEMORY_TYPE_AI_MEMORY = "ai_memory"
MEMORY_TYPE_JOURNAL = "journal"
MEMORY_TYPE_EVENT = "event"
MEMORY_TYPE_CHAT = "chat"
MEMORY_TYPE_REPORT = "report"

_client: Optional[chromadb.PersistentClient] = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(CHROMA_DATA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=CHROMA_DATA_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _get_collection():
    return _get_client().get_or_create_collection(name=COLLECTION_USER_MEMORY)


# ── 写入 API ─────────────────────────────────────────

def add_entry(
    entry_id: str,
    user_id: int,
    content: str,
    memory_type: str,
    metadata: Optional[dict] = None,
):
    """
    向 Chroma 写入一条语义记忆（单一入口）。

    Args:
        entry_id: 唯一 ID，建议格式 "{memory_type}:{db_id}" → "ai_memory:42"
        user_id: 用户 ID
        content: 需要 Embedding 的文本
        memory_type: ai_memory / journal / event / chat / report
        metadata: 附加元数据 {importance, time, tags, source_id, ...}
    """
    collection = _get_collection()
    meta = {
        "user_id": str(user_id),
        "type": memory_type,
    }
    if metadata:
        for k, v in metadata.items():
            meta[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v

    collection.add(
        ids=[str(entry_id)],
        documents=[content],
        metadatas=[meta],
    )


def add_ai_memory(memory_id: int, user_id: int, content: str, metadata: Optional[dict] = None):
    """快捷：写入 AI 提取的长期记忆"""
    add_entry(f"ai_memory:{memory_id}", user_id, content, MEMORY_TYPE_AI_MEMORY, metadata)


def add_journal(journal_id: int, user_id: int, content: str, metadata: Optional[dict] = None):
    """快捷：写入原始日记"""
    add_entry(f"journal:{journal_id}", user_id, content, MEMORY_TYPE_JOURNAL, metadata)


def add_event(event_id: int, user_id: int, content: str, metadata: Optional[dict] = None):
    """快捷：写入人生事件描述"""
    add_entry(f"event:{event_id}", user_id, content, MEMORY_TYPE_EVENT, metadata)


def add_chat_message(msg_id: int, user_id: int, content: str, metadata: Optional[dict] = None):
    """快捷：写入对话记录"""
    add_entry(f"chat:{msg_id}", user_id, content, MEMORY_TYPE_CHAT, metadata)


# ── 检索 API ─────────────────────────────────────────

def search(
    user_id: int,
    query: str,
    n_results: int = 10,
    memory_types: Optional[list[str]] = None,
) -> list[dict]:
    """
    语义搜索用户的人生记忆（单一 Collection，所有类型统一检索）。

    用于 RAG：人格建模、模拟生成、AI 对话时召回相关经历。

    Args:
        user_id: 当前用户 ID
        query: 自然语言查询，如 "我为什么适合创业？"
        n_results: 返回条数
        memory_types: 可选过滤，如 ["ai_memory", "event"]

    Returns:
        [{id, content, metadata, distance}, ...]
    """
    collection = _get_collection()
    where = {"user_id": str(user_id)}
    if memory_types:
        where["type"] = {"$in": memory_types}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
    )

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


def search_by_type(
    user_id: int,
    query: str,
    memory_type: str,
    n_results: int = 5,
) -> list[dict]:
    """按类型过滤搜索"""
    return search(user_id, query, n_results, memory_types=[memory_type])


# ── 管理 API ─────────────────────────────────────────

def delete_user_data(user_id: int):
    """删除用户的所有向量数据（账户注销时调用）"""
    try:
        collection = _get_collection()
        collection.delete(where={"user_id": str(user_id)})
    except Exception:
        pass


def count_user_entries(user_id: int) -> int:
    """统计用户的记忆条数"""
    try:
        collection = _get_collection()
        result = collection.get(where={"user_id": str(user_id)})
        return len(result["ids"]) if result and result["ids"] else 0
    except Exception:
        return 0
