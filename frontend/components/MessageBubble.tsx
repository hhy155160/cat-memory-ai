"use client";

/**
 * 聊天气泡组件
 * =====================
 * 展示单条聊天消息：用户消息靠右（橙色气泡），AI 消息靠左（浅色气泡）。
 * 生成中且内容为空时显示"正在回忆…"占位提示。
 *
 * 可复用性：二期记忆列表等页面的消息/文本条目也可以复用此气泡样式
 */

/** 单条聊天消息的数据结构（与后端交互的角色类型） */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface MessageBubbleProps {
  message: ChatMessage;
  /** 该条消息是否正在流式生成中（只有最后一条 AI 消息可能为 true） */
  generating?: boolean;
}

export default function MessageBubble({ message, generating = false }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "rounded-br-sm bg-orange-400 text-white"
            : "rounded-bl-sm bg-orange-50 text-stone-700"
        }`}
      >
        {message.content}
        {/* 流式生成中且当前内容为空时显示打字指示 */}
        {generating && !message.content && (
          <span className="animate-pulse text-orange-400">正在回忆…</span>
        )}
      </div>
    </div>
  );
}
