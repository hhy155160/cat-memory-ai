/**
 * 首页路由（薄壳）
 * =====================
 * Next.js App Router 约定：路由必须定义在 app/ 目录下，
 * 页面级业务代码统一放在同级 views/ 目录，保持路由文件干净。
 */

import HomeView from "@/views/HomeView";

export default function Page() {
  return <HomeView />;
}
