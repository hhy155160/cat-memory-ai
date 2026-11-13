import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  /**
   * 开发代理：前端所有 /api/* 请求由 Next 服务器转发到本地 FastAPI 后端。
   * 好处：
   *   1. 浏览器只看到同源请求，彻底规避跨域（CORS）；
   *   2. 手机/局域网设备访问时，只需能连到前端地址，
   *      转发由 Next 服务器在本机完成，不受 127.0.0.1 回环限制。
   * 修改本文件后需重启 npm run dev 生效。
   */
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
