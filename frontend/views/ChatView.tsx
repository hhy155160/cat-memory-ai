"use client";

/**
 * AI 对话视图
 * =====================
 * 功能：聊天输入框 + 消息窗口，调用后端 POST /chat 流式展示回答
 *
 * 流式说明：
 * - 后端返回 text/plain 的流式响应（StreamingResponse）
 * - 浏览器端 axios 不支持读取流（responseType: "stream" 仅 Node.js 可用），
 *   因此这里用原生 fetch + ReadableStream 逐段读取，其余请求仍走 axios
 *
 * TODO(二期)：多轮对话上下文；消息历史本地缓存
 */

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, getErrorMessage } from "@/lib/api";
import MessageBubble, { type ChatMessage } from "@/components/MessageBubble";

/** 欢迎语：首次进入页面时展示 */
const WELCOME_MESSAGE: ChatMessage = {
  role: "assistant",
  content: "你好呀～我是猫咪记忆 AI，问我任何关于你家猫咪的事吧！",
};

export default function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");       // 输入框内容
  const [asking, setAsking] = useState(false);  // 是否正在生成回答（流式进行中）

  // 消息窗口底部锚点：每次消息变化时滚动到底部
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** 发送问题并流式接收回答 */
  async function handleSend() {
    const question = input.trim();
    if (!question || asking) return; // 空消息 / 正在生成中时不发送

    // 1) 先把用户消息和一条"空的 AI 回复"追加进列表，
    //    之后流式内容不断填充最后一条消息
    setMessages([...messages, { role: "user", content: question }, { role: "assistant", content: "" }]);
    setInput("");
    setAsking(true);

    try {
      // 2) 发起流式请求（后端 /chat 返回 text/plain 流）
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!response.ok || !response.body) {
        // 非 2xx 时尝试读取后端的 detail 错误信息
        const detail = await response.json().catch(() => null);
        throw new Error(detail?.detail ?? `请求失败（${response.status}）`);
      }

      // 3) 逐块读取流，实时拼接到最后一条 AI 消息
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;
      while (!done) {
        const { value, done: finished } = await reader.read();
        done = finished;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          // 函数式更新：基于最新 state 追加，避免闭包拿到旧值
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              role: "assistant",
              content: next[next.length - 1].content + chunk,
            };
            return next;
          });
        }
      }
    } catch (err) {
      // 出错时把错误信息写入最后一条 AI 消息，保留上下文
      const text = err instanceof Error ? err.message : getErrorMessage(err);
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", content: `生成失败：${text}` };
        return next;
      });
    } finally {
      setAsking(false);
    }
  }

  /** 回车发送（Shift+Enter 换行） */
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-[calc(100vh-8.5rem)] flex-col space-y-4">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-semibold text-stone-800">和 AI 聊聊你的猫</h1>
        <p className="mt-1 text-sm text-stone-500">
          回答基于你保存过的记忆，没有记录的事情 AI 会如实告诉你。
        </p>
      </div>

      {/* 消息展示窗口：占满剩余高度，超出滚动 */}
      <section className="flex-1 overflow-y-auto rounded-2xl border border-orange-100 bg-white p-4 shadow-sm">
        <div className="space-y-3">
          {messages.map((msg, index) => (
            <MessageBubble
              key={index}
              message={msg}
              // 只有"最后一条 AI 消息"且正在生成时，才显示打字占位
              generating={asking && index === messages.length - 1 && msg.role === "assistant"}
            />
          ))}
          {/* 滚动锚点 */}
          <div ref={bottomRef} />
        </div>
      </section>

      {/* 输入区：textarea + 发送按钮 */}
      <section className="flex items-end gap-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          maxLength={2000}
          placeholder="问问它今天干了什么…（Enter 发送，Shift+Enter 换行）"
          className="flex-1 resize-none rounded-2xl border border-orange-100 bg-white px-4 py-3 text-sm text-stone-700 shadow-sm placeholder:text-stone-400 focus:border-orange-300 focus:outline-none focus:ring-2 focus:ring-orange-200"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={asking || !input.trim()}
          className="rounded-2xl bg-orange-400 px-6 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-orange-500 disabled:cursor-not-allowed disabled:bg-orange-200"
        >
          {asking ? "回忆中…" : "发送"}
        </button>
      </section>
    </div>
  );
}
