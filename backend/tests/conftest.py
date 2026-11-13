# -*- coding: utf-8 -*-
"""
pytest 公共夹具
================
1. isolated_store：把向量库指向独立的测试集合（cat_memories_test），
   测试数据与真实记忆库完全隔离，测试结束自动删除；
2. 提供生成测试图片等公共工具。
"""

import chromadb
import pytest

from config import CHROMA_DIR
from services import vector_store

# 测试专用集合名，与真实集合 cat_memories 隔离
TEST_COLLECTION = "cat_memories_test"


@pytest.fixture
def isolated_store(monkeypatch):
    """
    每个测试用例拿到一个干净独立的向量库集合：
    - 测试前：删除残留的测试集合并重建
    - 测试中：monkeypatch 掉 vector_store.memory_collection，所有 CRUD 都落在测试集合
    - 测试后：自动删除测试集合
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(TEST_COLLECTION)
    except Exception:
        pass  # 集合不存在时忽略
    collection = client.get_or_create_collection(
        name=TEST_COLLECTION,
        embedding_function=vector_store.embedding_fn,
    )
    monkeypatch.setattr(vector_store, "memory_collection", collection)
    yield collection
    client.delete_collection(TEST_COLLECTION)
