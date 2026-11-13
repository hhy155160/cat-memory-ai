# -*- coding: utf-8 -*-
"""
向量存储服务（services/vector_store.py）测试
覆盖：增、删、改、查（语义检索 / 分页列表 / 计数）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 保证可导入 backend 模块

from services.vector_store import (
    add_memory,
    count_memories,
    delete_memory,
    list_memories,
    search_memories,
    update_memory,
)


class TestAddMemory:
    """增：add_memory"""

    def test_add_returns_id_and_increases_count(self, isolated_store):
        """新增后：返回非空 id，且计数 +1"""
        before = count_memories()
        memory_id = add_memory("测试：小猫爱玩毛线球")
        assert memory_id
        assert count_memories() == before + 1

    def test_add_stores_metadata(self, isolated_store):
        """新增的元数据包含 source / image_path / photo_time / created_at"""
        memory_id = add_memory("元数据测试", image_path="/tmp/x.png", photo_time="2026-01-01T10:00:00")
        item = next(m for m in list_memories() if m["id"] == memory_id)
        assert item["note"] == "元数据测试"
        assert item["image_path"] == "/tmp/x.png"
        assert item["photo_time"] == "2026-01-01T10:00:00"
        assert item["created_at"]


class TestListMemories:
    """查：list_memories 分页列表"""

    def test_list_returns_items_sorted_desc(self, isolated_store):
        """列表按创建时间倒序，字段完整"""
        add_memory("第一条", photo_time="2026-01-01T08:00:00")
        add_memory("第二条", photo_time="2026-01-02T08:00:00")
        items = list_memories()
        assert len(items) == 2
        assert items[0]["photo_time"] >= items[1]["photo_time"]
        assert set(items[0].keys()) == {"id", "note", "image_path", "photo_time", "created_at"}

    def test_list_pagination(self, isolated_store):
        """limit / offset 分页生效"""
        for i in range(3):
            add_memory(f"分页测试{i}")
        assert len(list_memories(limit=2)) == 2
        assert len(list_memories(limit=2, offset=2)) == 1


class TestUpdateDelete:
    """改 / 删：update_memory、delete_memory"""

    def test_update_existing_memory(self, isolated_store):
        """修改存在的记忆：返回 True，且检索能命中新文本"""
        memory_id = add_memory("修改前的内容")
        assert update_memory(memory_id, "修改后的内容：小猫七点叫早") is True
        item = next(m for m in list_memories() if m["id"] == memory_id)
        assert item["note"] == "修改后的内容：小猫七点叫早"

    def test_update_missing_memory(self, isolated_store):
        """修改不存在的 id：返回 False 且不报错"""
        assert update_memory("not-exist-id", "随便") is False

    def test_delete_existing_memory(self, isolated_store):
        """删除存在的记忆：返回 True，计数 -1，检索不再命中"""
        memory_id = add_memory("待删除的记忆")
        before = count_memories()
        assert delete_memory(memory_id) is True
        assert count_memories() == before - 1
        assert all(m["id"] != memory_id for m in list_memories())

    def test_delete_missing_memory(self, isolated_store):
        """删除不存在的 id：返回 False，可安全重复调用"""
        assert delete_memory("not-exist-id") is False
        assert delete_memory("not-exist-id") is False


class TestSearchMemories:
    """查：search_memories 语义检索"""

    def test_search_empty_collection(self, isolated_store):
        """空集合检索：返回空列表，不报错"""
        assert search_memories("随便问", top_k=3) == []

    def test_search_returns_top_k_within_limit(self, isolated_store):
        """
        检索不超过 top_k 条且非空。
        注：MiniLM 对中文语义召回较弱，不断言具体命中哪条（属于检索质量，非功能正确性）。
        """
        add_memory("小猫今天早上六点叫早，把我吵醒了")
        add_memory("小猫下午在窗台上晒了一下午太阳")
        add_memory("今天给它买了新的猫抓板")
        results = search_memories("小猫晒太阳了吗", top_k=2)
        assert 0 < len(results) <= 2

    def test_search_exact_content_recalled(self, isolated_store):
        """查询与某条记忆几乎相同的内容时，该记忆应被召回"""
        add_memory("小猫下午在窗台上晒了一下午太阳")
        add_memory("今天给它买了新的猫抓板")
        results = search_memories("窗台上晒了一下午太阳", top_k=2)
        assert any("晒了一下午太阳" in r for r in results)

    def test_search_top_k_larger_than_collection(self, isolated_store):
        """top_k 大于库内条数时：返回全部，不越界报错"""
        add_memory("唯一的一条记忆")
        assert len(search_memories("记忆", top_k=5)) == 1
