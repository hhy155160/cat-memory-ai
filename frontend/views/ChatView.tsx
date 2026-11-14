"use client";

/**
 * AI 对话视图（SSE 版）
 * =====================
 * 功能：聊天输入框 + 消息窗口，基于 EventSource 监听后端 GET /chat/stream 的 SSE 流，
 *      逐字渲染大模型回答。
 *
 * 为什么用 EventSource 而不是 fetch：
 * - EventSource 是浏览器原生的 SSE 客户端，API 简单（onmessage 回调）；
 * - 自带断线感知（onerror + readyState），配合后端 [DONE] 结束标记实现可控的流；
 * - 注意：原生 EventSource 只支持 GET，所以后端提供了 GET /chat/stream 接口，
 *   问题文本通过 query 参数传递（encodeURIComponent 防止特殊字符破坏 URL）。
 *
 * 异常处理策略（三层）：
 * 1. 自动重连：连接意外断开时 EventSource 浏览器会自动重试（readyState=CONNECTING），
 *    前端限制最多自动重连 MAX_RETRIES 次，期间显示"正在重连"提示；
 * 2. 超时兜底：若超过 RECV_TIMEOUT_MS 没收到任何分片（模型卡死/网络黑洞），
 *    主动断开并进入错误状态；
 * 3. 报错兜底 UI：彻底失败后展示错误气泡 + "重试"按钮，用户可手动重发。
 *
 * TODO(二期)：多轮对话上下文；消息历史本地缓存
 */

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import MessageBubble, { type ChatMessage } from "@/components/MessageBubble";

/** 欢迎语：首次进入页面时展示 */
const WELCOME_MESSAGE: ChatMessage = {
  role: "assistant",
  content: "你好呀～我是猫咪记忆 AI，问我任何关于你猫咪的事吧！",
};

/** 自动重连上限：超过后停止重连，转入手动重试 */
const MAX_AUTO_RETRIES = 3;
/** 接收超时：两个分片之间最多允许的静默间隔（模型长时间不吐字视为故障） */
const RECV_TIMEOUT_MS = 30_000;

export default function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");           // 输入框内容
  const [asking, setAsking] = useState(false);      // SSE 连接/接收进行中
  const [reconnecting, setReconnecting] = useState(false); // 断线自动重连中
  const [lastError, setLastError] = useState<string>("");  // 彻底失败的原因（非空时展示重试按钮）

  // 消息窗口底部锚点：消息变化时滚动到底部
  const bottomRef = useRef<HTMLDivElement>(null);

  // ---- 流式会话相关的 ref（跨回调共享、不触发重渲染）----
  const esRef = useRef<EventSource | null>(null);   // 当前 EventSource 实例
  const retryCountRef = useRef(0);                  // 已自动重连次数
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null); // 接收超时计时器
  const lastQuestionRef = useRef("");               // 最近一次提问（供"重试"按钮复用）

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** 组件卸载时关闭连接、清掉计时器，防止内存泄漏和后台僵尸流 */
  useEffect(() => {
    return () => {
      esRef.current?.close();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  /** 重置接收超时计时器：每收到一个分片都调用一次（滑动窗口） */
  function resetRecvTimer() {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      // 超时：主动断开，进入错误兜底
      handleClose("回答超时，服务器长时间没有响应");
    }, RECV_TIMEOUT_MS);
  }

  /** 把错误写入"最后一条 AI 气泡"并结束加载态（兜底 UI 的一部分） */
  function showErrorAsBubble(text: string) {
    setMessages((prev) => {
      const next = [...prev];
      next[next.length - 1] = { role: "assistant", content: `生成失败：${text}` };
      return next;
    });
    setLastError(text);
    setAsking(false);
    setReconnecting(false);
  }

  /** 主动关闭连接并进入错误兜底（超时 / 重连次数用尽时调用） */
  function handleClose(reason: string) {
    esRef.current?.close();
    esRef.current = null;
    if (timerRef.current) clearTimeout(timerRef.current);
    showErrorAsBubble(reason);
  }

  /** 追加文本到最后一条 AI 消息（流式逐字渲染的核心） */
  function appendToLastAssistant(chunk: string) {
    setMessages((prev) => {
      const next = [...prev];
      next[next.length - 1] = {
        role: "assistant",
        content: next[next.length - 1].content + chunk,
      };
      return next;
    });
  }

  /**
   * 建立一条 SSE 连接并处理全部事件。
   * 抽成独立函数是为了"重试"时能对同一个 question 再次调用。
   */
  function openStream(question: string) {
    // 若已有连接先关掉，保证同一时刻只有一条流
    esRef.current?.close();

    const es = new EventSource(
      `${API_BASE_URL}/chat/stream?question=${encodeURIComponent(question)}`,
    );
    esRef.current = es;

    // ---- 连接建立 ----
    es.onopen = () => {
      retryCountRef.current = 0;      // 连上后重置重连计数
      setReconnecting(false);
      resetRecvTimer();               // 开始计算"首字节超时"
      // 重连场景下后端会重新生成回答：清空半截内容，避免新旧内容拼接重复
      setMessages((prev) => {
        const next = [...prev];
        if (retryCountRef.current === 0) return prev;
        next[next.length - 1] = { role: "assistant", content: "" };
        return next;
      });
    };

    // ---- 收到分片 ----
    es.onmessage = (event) => {
      resetRecvTimer(); // 每收到数据都续期超时计时器

      if (event.data === "[DONE]") {
        // 流正常结束：必须手动 close！
        // 否则 EventSource 默认会"重新发起 GET"造成后端重复生成
        es.close();
        esRef.current = null;
        if (timerRef.current) clearTimeout(timerRef.current);
        setAsking(false);
        setLastError("");
        return;
      }
      // 正常文本分片：拼接到最后一条 AI 消息（逐字渲染）
      appendToLastAssistant(event.data);
    };

    // ---- 连接出错 ----
    es.onerror = () => {
      if (timerRef.current) clearTimeout(timerRef.current);

      if (es.readyState === EventSource.CLOSED) {
        // 服务端拒绝（如 503）或连接彻底失败：浏览器不会自动重试，
        // 直接进入手动重试兜底
        showErrorAsBubble("连接失败，请检查后端服务是否运行");
        return;
      }

      // readyState === CONNECTING：浏览器正在自动重连
      retryCountRef.current += 1;
      if (retryCountRef.current > MAX_AUTO_RETRIES) {
        // 自动重连次数用尽：停止等待，交给用户手动重试
        handleClose(`连接中断（已自动重试 ${MAX_AUTO_RETRIES} 次）`);
        return;
      }
      setReconnecting(true); // UI 显示"正在重连"，EventSource 会自动重发同一 URL
    };
  }

  /** 发送问题：追加用户气泡 + 空的 AI 气泡，然后建立 SSE 流 */
  function handleSend(questionOverride?: string) {
    const question = (questionOverride ?? input).trim();
    if (!question || asking) return; // 空消息 / 正在生成时不发送

    lastQuestionRef.current = question; // 记录提问，供重试按钮使用
    setMessages((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: "" }]);
    if (!questionOverride) setInput(""); // 点击"重试"时不重复清空输入框
    setLastError("");
    setAsking(true);
    retryCountRef.current = 0;
    openStream(question);
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
          {/* 自动重连提示条 */}
          {reconnecting && (
            <p className="text-center text-xs text-amber-600">
              连接中断，正在自动重连…
            </p>
          )}
          {/* 报错兜底 UI：彻底失败后允许一键重试（重发上一次的问题） */}
          {lastError && !asking && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-xs text-stone-400">上一次回答未能完成</p>
              <button
                type="button"
                onClick={() => handleSend(lastQuestionRef.current)}
                className="rounded-full border border-orange-300 bg-orange-50 px-4 py-1.5 text-xs text-orange-600 transition-colors hover:bg-orange-100"
              >
                重试回答
              </button>
            </div>
          )}
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
          onClick={() => handleSend()}
          disabled={asking || !input.trim()}
          className="rounded-2xl bg-orange-400 px-6 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-orange-500 disabled:cursor-not-allowed disabled:bg-orange-200"
        >
          {asking ? "回忆中…" : "发送"}
        </button>
      </section>
    </div>
  );
}
