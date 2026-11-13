# -*- coding: utf-8 -*-
"""
向量存储服务
============
ChromaDB 记忆集合的**唯一**操作入口：增、删、改、查全部定义在本文件，
路由层与其他服务只调用这里的函数，不直接接触 memory_collection，
便于统一维护（换库、加字段、改索引策略都只动这里）。

二期猫咪习惯图谱可基于 metadata（时间、来源）做结构化统计。
"""

import uuid
from datetime import datetime

import chromadb
from chromadb.utils import embedding_functions

from config import CHROMA_DIR, COLLECTION_NAME

# 1) 文本向量化模型：ChromaDB 内置的 all-MiniLM-L6-v2
#    （模型文件缓存在 ~/.cache/chroma，首次使用会自动下载）
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# 2) ChromaDB 持久化客户端：数据自动落盘到 CHROMA_DIR
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# 3) 记忆集合：一期只存 note 文本，metadata 预留时间/图片来源等字段
memory_collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn,
)


# ===================== 增 =====================

def add_memory(note: str, image_path: str | None = None, photo_time: str | None = None) -> str:
    """
    新增一条猫咪记忆：note 文本自动向量化入库，并附带元数据。
    photo_time 为照片 EXIF 拍摄时间（缺失则存创建时间）。
    返回本次记忆的 id（供前端关联展示，二期记忆列表可用）。
    """
    memory_id = uuid.uuid4().hex
    memory_collection.add(
        ids=[memory_id],
        documents=[note],
        metadatas=[{
            "source": "user_note",
            "image_path": image_path or "",
            "photo_time": photo_time or datetime.now().isoformat(timespec="seconds"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }],
    )
    return memory_id


# ===================== 删 =====================

def delete_memory(memory_id: str) -> bool:
    """
    按 id 删除一条记忆。
    返回是否真的删除了（id 不存在时返回 False）。
    """
    existed = memory_collection.get(ids=[memory_id])["ids"]
    if not existed:
        return False
    memory_collection.delete(ids=[memory_id])
    return True


# ===================== 改 =====================

def update_memory(memory_id: str, note: str) -> bool:
    """
    修改记忆文本：重新向量化覆盖原文（元数据保持不变）。
    返回是否存在该 id。
    TODO(二期)：如需修改元数据（如补图片），在此扩展参数。
    """
    existed = memory_collection.get(ids=[memory_id])["ids"]
    if not existed:
        return False
    memory_collection.update(ids=[memory_id], documents=[note])
    return True


# ===================== 查 =====================

def search_memories(question: str, top_k: int) -> list[str]:
    """语义检索：按相似度召回最相关的 top_k 条记忆文本（供 RAG 使用）"""
    if memory_collection.count() == 0:
        return []
    result = memory_collection.query(
        query_texts=[question],
        n_results=min(top_k, memory_collection.count()),
    )
    documents = result.get("documents") or []
    return documents[0] if documents else []


def list_memories(limit: int = 50, offset: int = 0) -> list[dict]:
    """
    分页列出全部记忆（供二期记忆列表页使用）。
    返回结构：[{"id", "note", "image_path", "photo_time", "created_at"}]，按创建时间倒序。
    """
    result = memory_collection.get(include=["documents", "metadatas"], limit=limit, offset=offset)
    items = []
    for memory_id, note, meta in zip(result["ids"], result["documents"], result["metadatas"]):
        meta = meta or {}
        items.append({
            "id": memory_id,
            "note": note,
            "image_path": meta.get("image_path", ""),
            "photo_time": meta.get("photo_time", ""),
            "created_at": meta.get("created_at", ""),
        })
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items


def count_memories() -> int:
    """当前记忆总条数（健康检查 / 记忆列表分页用）"""
    return memory_collection.count()
