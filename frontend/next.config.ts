import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  // 容器部署用 standalone 产物（只带运行所需文件，镜像更小）
  output: "standalone",
};

export default nextConfig;
