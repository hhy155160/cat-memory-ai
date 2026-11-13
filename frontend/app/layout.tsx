import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "猫咪记忆 AI",
  description: "记录猫咪生活的每一条记忆，随时和 AI 聊聊它的小习惯",
};

/**
 * 全局导航：
 * - 一期只有「记录记忆」和「AI 对话」两个页面
 * - 预留扩展位：记忆列表 /memories、习惯图谱 /habits（二期实现）
 */
const NAV_LINKS = [
  { href: "/", label: "记录记忆" },
  { href: "/chat", label: "AI 对话" },
  // { href: "/memories", label: "记忆列表" },   // TODO(二期)：记忆列表页面
  // { href: "/habits", label: "习惯图谱" },     // TODO(二期)：习惯图谱页面
];

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        {/* 顶部导航栏 */}
        <header className="border-b border-orange-100 bg-white/70 backdrop-blur">
          <nav className="mx-auto flex h-14 max-w-3xl items-center gap-6 px-4">
            <Link href="/" className="text-lg font-semibold text-orange-600">
              🐱 猫咪记忆 AI
            </Link>
            <div className="flex gap-4">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-sm text-stone-600 transition-colors hover:text-orange-600"
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </nav>
        </header>

        {/* 页面主体 */}
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
          {children}
        </main>

        <footer className="py-4 text-center text-xs text-stone-400">
          猫咪记忆 AI · 用 RAG 记住它的每一天
        </footer>
      </body>
    </html>
  );
}
