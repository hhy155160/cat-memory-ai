"use client";

/**
 * 首页视图：记录猫咪记忆
 * =====================
 * 功能：选择图片 + 填写备注 → 调用后端 POST /upload-memory
 * 后端行为：图片落盘到 uploads/，备注文本写入 ChromaDB 向量库
 *
 * TODO(二期)：图片 AI 自动识别生成备注；接入记忆列表展示历史记录
 */

import { useRef, useState } from "react";
import Link from "next/link";
import { api, getErrorMessage } from "@/lib/api";

export default function HomeView() {
  const [file, setFile] = useState<File | null>(null); // 选中的图片
  const [preview, setPreview] = useState<string>("");  // 本地预览地址
  const [note, setNote] = useState("");                // 备注文本
  const [saving, setSaving] = useState(false);         // 保存 loading 状态
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  /** 选择图片后生成本地预览（不经过后端） */
  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    // 释放上一次预览的内存，避免图片多了以后内存泄漏
    if (preview) URL.revokeObjectURL(preview);
    setPreview(selected ? URL.createObjectURL(selected) : "");
    setFeedback(null);
  }

  /** 提交记忆到后端 */
  async function handleSave() {
    // 前端先做一层简单校验，减少无效请求
    if (!file) {
      setFeedback({ type: "error", text: "请先选择一张猫咪图片" });
      return;
    }
    if (!note.trim()) {
      setFeedback({ type: "error", text: "备注不能为空" });
      return;
    }

    setSaving(true);
    setFeedback(null);
    try {
      // 上传用 FormData（multipart/form-data），与后端 File + Form 参数对应
      const formData = new FormData();
      formData.append("file", file);
      formData.append("note", note.trim());
      await api.post("/upload-memory", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setFeedback({ type: "success", text: "记忆保存成功 🎉" });
      // 保存成功后清空表单
      setFile(null);
      setPreview("");
      setNote("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setFeedback({ type: "error", text: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* 页面标题区 */}
      <section>
        <h1 className="text-2xl font-semibold text-stone-800">记录一条猫咪记忆</h1>
        <p className="mt-1 text-sm text-stone-500">
          上传照片并写下此刻的备注，AI 会帮你记住并随时回忆。
        </p>
      </section>

      {/* 表单卡片 */}
      <section className="rounded-2xl border border-orange-100 bg-white p-6 shadow-sm">
        {/* 图片选择框：用 label 原生关联 file input，点击弹窗由浏览器触发（兼容 Safari） */}
        <label className="block text-sm font-medium text-stone-700">猫咪图片</label>
        <div className="mt-2 flex items-center gap-4">
          <label
            htmlFor="cat-image"
            className="cursor-pointer rounded-xl border border-dashed border-orange-300 bg-orange-50 px-4 py-3 text-sm text-orange-600 transition-colors hover:bg-orange-100"
          >
            {file ? "重新选择图片" : "点击选择图片"}
          </label>
          {/* sr-only 而非 hidden：input 保留在布局中，避免 Safari 对 display:none 输入框的点击拦截 */}
          <input
            id="cat-image"
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif,image/bmp"
            onChange={handleFileChange}
            className="sr-only"
          />
          {preview && (
            // 本地预览缩略图
            // eslint-disable-next-line @next/next/no-img-element —— 预览的是本地 blob，无需 next/image 优化
            <img
              src={preview}
              alt="猫咪图片预览"
              className="h-16 w-16 rounded-xl border border-orange-100 object-cover"
            />
          )}
        </div>
        {file && <p className="mt-1 text-xs text-stone-400">{file.name}</p>}

        {/* 备注输入框 */}
        <label htmlFor="note" className="mt-6 block text-sm font-medium text-stone-700">
          备注（AI 会依据这条记忆回答问题）
        </label>
        <textarea
          id="note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={4}
          maxLength={500}
          placeholder="例如：今天早上它把水碗打翻了，然后一脸无辜地看着我……"
          className="mt-2 w-full resize-none rounded-xl border border-orange-100 bg-orange-50/40 px-4 py-3 text-sm text-stone-700 placeholder:text-stone-400 focus:border-orange-300 focus:outline-none focus:ring-2 focus:ring-orange-200"
        />

        {/* 保存按钮：saving 时禁用并显示加载中 */}
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="mt-4 w-full rounded-xl bg-orange-400 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-orange-500 disabled:cursor-not-allowed disabled:bg-orange-200"
        >
          {saving ? "保存中…" : "保存这条记忆"}
        </button>

        {/* 操作反馈：成功 / 失败提示 */}
        {feedback && (
          <p
            className={`mt-3 text-center text-sm ${
              feedback.type === "success" ? "text-emerald-600" : "text-red-500"
            }`}
          >
            {feedback.text}
          </p>
        )}
      </section>

      {/* 引导跳转到对话页 */}
      <p className="text-center text-sm text-stone-500">
        已经有记忆了？去{" "}
        <Link href="/chat" className="text-orange-500 hover:underline">
          和 AI 聊聊你的猫
        </Link>
      </p>
    </div>
  );
}
