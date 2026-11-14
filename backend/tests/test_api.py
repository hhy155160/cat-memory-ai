# -*- coding: utf-8 -*-
"""
API 接口测试（main.py + routers/）
使用 FastAPI TestClient，不启动真实服务。
大模型调用全部 mock，测试不依赖网络与 API Key。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from tests.helpers import make_png
from main import app

client = TestClient(app)


class TestSystemRoutes:
    """系统级路由"""

    def test_index_health(self):
        """GET / → 200，返回 code=0 与记忆条数"""
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert isinstance(body["memories"], int)

    def test_favicon_204(self):
        """GET /favicon.ico → 204（占位，消除浏览器 404）"""
        assert client.get("/favicon.ico").status_code == 204


class TestUploadMemory:
    """POST /upload-memory：记忆入库"""

    def test_upload_success(self, isolated_store):
        """合法图片 + 备注 → 200，返回 id/图片路径/拍摄时间"""
        before = isolated_store.count()
        resp = client.post(
            "/upload-memory",
            files={"file": ("cat.png", make_png(), "image/png")},
            data={"note": "接口测试：小猫在玩毛线球"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["id"]
        assert body["data"]["photo_time"]  # EXIF 缺失时回退当前时间
        assert isolated_store.count() == before + 1  # 确认真实入库

    def test_upload_blank_note_rejected(self):
        """纯空白备注 → 400"""
        resp = client.post(
            "/upload-memory",
            files={"file": ("cat.png", make_png(), "image/png")},
            data={"note": "   "},
        )
        assert resp.status_code == 400
        assert "不能为空" in resp.json()["detail"]

    def test_upload_invalid_image_rejected(self):
        """伪装图片 → 400"不是有效图片\""""
        resp = client.post(
            "/upload-memory",
            files={"file": ("fake.png", b"junk-bytes", "image/png")},
            data={"note": "备注"},
        )
        assert resp.status_code == 400
        assert "有效图片" in resp.json()["detail"]

    def test_upload_empty_file_rejected(self):
        """空文件 → 400"上传文件为空\""""
        resp = client.post(
            "/upload-memory",
            files={"file": ("empty.png", b"", "image/png")},
            data={"note": "备注"},
        )
        assert resp.status_code == 400
        assert "上传文件为空" in resp.json()["detail"]

    def test_upload_missing_note_rejected(self):
        """缺少 note 字段 → 422（FastAPI 参数校验）"""
        resp = client.post(
            "/upload-memory",
            files={"file": ("cat.png", make_png(), "image/png")},
        )
        assert resp.status_code == 422


class TestChatStreamSSE:
    """GET /chat/stream：SSE 协议流式问答（大模型调用 mock，不联网）"""

    def test_sse_without_api_key_returns_503(self, monkeypatch):
        """未配置大模型客户端 → 503（SSE 握手前就失败，前端 EventSource 触发 onerror）"""
        from routers import chat as chat_router
        monkeypatch.setattr(chat_router, "llm_client", None)
        resp = client.get("/chat/stream", params={"question": "你好"})
        assert resp.status_code == 503

    def test_sse_stream_format(self, isolated_store, monkeypatch):
        """
        mock 流式生成 → 校验 SSE 帧格式：
        - 每帧 data: 前缀 + 空行分隔
        - 内容完整拼接
        - 以 data: [DONE] 结束
        """
        from routers import chat as chat_router

        def fake_stream(question, memories):
            assert any("毛线球" in m for m in memories)  # RAG 检索上下文生效
            yield "小猫"
            yield "爱玩\n毛线球"  # 含换行：验证多行被拆成多个 data: 行

        monkeypatch.setattr(chat_router, "stream_answer", fake_stream)

        client.post(
            "/upload-memory",
            files={"file": ("cat.png", make_png(), "image/png")},
            data={"note": "小猫爱玩毛线球"},
        )

        resp = client.get("/chat/stream", params={"question": "小猫爱玩什么"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        raw = resp.text
        assert raw.endswith("data: [DONE]\n\n")           # 结束标记
        assert "data: 小猫\n\n" in raw                     # 单行帧
        assert "data: 爱玩\ndata: 毛线球\n\n" in raw        # 多行拆帧
        assert "[DONE]" not in raw.replace("data: [DONE]", "")  # DONE 只出现一次

    def test_sse_empty_question_rejected(self):
        """空问题 → 422（Query min_length 校验）"""
        resp = client.get("/chat/stream", params={"question": ""})
        assert resp.status_code == 422


class TestChat:
    """POST /chat：流式问答（大模型调用 mock，不联网）"""

    def test_chat_without_api_key_returns_503(self, monkeypatch):
        """未配置大模型客户端 → 503 明确提示"""
        from routers import chat as chat_router
        monkeypatch.setattr(chat_router, "llm_client", None)
        resp = client.post("/chat", json={"question": "你好"})
        assert resp.status_code == 503
        assert "DEEPSEEK_API_KEY" in resp.json()["detail"]

    def test_chat_streams_mocked_answer(self, isolated_store, monkeypatch):
        """mock 流式生成 → 200，text/plain，内容为分段拼接的完整回答"""
        from routers import chat as chat_router

        def fake_stream(question, memories):
            # 模拟真实行为：逐段产出 + 上下文里带召回的记忆
            assert any("毛线球" in m for m in memories)  # 检索上下文生效
            yield "小猫"
            yield "在玩毛线球"

        monkeypatch.setattr(chat_router, "stream_answer", fake_stream)

        # 先入库一条记忆，验证 RAG 检索链路
        client.post(
            "/upload-memory",
            files={"file": ("cat.png", make_png(), "image/png")},
            data={"note": "小猫在玩毛线球"},
        )

        resp = client.post("/chat", json={"question": "小猫在干什么"})
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert resp.text == "小猫在玩毛线球"

    def test_chat_question_validation(self):
        """空问题 → 422（min_length=1 校验）"""
        resp = client.post("/chat", json={"question": ""})
        assert resp.status_code == 422
