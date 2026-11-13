/**
 * axios 统一配置
 * =====================
 * API_BASE_URL 为空字符串（同源请求）：前端请求 /api/*，
 * 由 Next 服务器代理转发到本地 FastAPI 后端（见 next.config.ts 的 rewrites）。
 *
 * 好处：手机/局域网调试时不受浏览器 127.0.0.1 回环限制，也无需处理跨域。
 * 若后续部署到独立域名/服务器，把这里改成后端完整地址即可，如：
 *   export const API_BASE_URL = "https://api.example.com";
 */
import axios from "axios";

/** 后端 API 前缀：/api 由 Next 代理转发到 FastAPI（见 next.config.ts 的 rewrites） */
export const API_BASE_URL = "/api";

/** 预留扩展位：后续可按模块拆分 api（如 memories、chat、habits） */
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 15s 超时，防止后端无响应时前端一直等待
  headers: { "Content-Type": "application/json" },
});

/** 统一错误提示提取：后端返回 { detail: string }（FastAPI 默认格式） */
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    return err.message;
  }
  return "未知错误，请稍后重试";
}
