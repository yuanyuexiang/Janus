import type { Metadata } from "next";
import { Inter, Noto_Serif_SC } from "next/font/google";

import "./globals.css";

const inter = Inter({
  variable: "--font-sans-inter",
  subsets: ["latin"],
  display: "swap",
});

const notoSerifSC = Noto_Serif_SC({
  variable: "--font-serif-sc",
  weight: ["400", "500", "600", "700", "900"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "圆桌投研 · Atlas Council",
  description: "一桌专家智囊团，陪你看清每一笔投资",
};

// 这是运行时环境变量（非 NEXT_PUBLIC），由容器在启动时提供。
// 每次请求在服务端读取，所以在 docker-compose 的 environment 里配即可，无需重新构建。
export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // 解析期同步执行：绘制前从 localStorage / 系统偏好定下 data-theme，避免主题闪烁
  const themeInit = `(function(){try{var t=localStorage.getItem('atlas-theme');if(t!=='light'&&t!=='dark'&&t!=='nasdaq'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme='light';}})();`;

  // 运行时把容器环境变量 API_BASE 注入浏览器（client 代码读 window.__API_BASE__）。
  // 留空 = 相对路径 /api（同源 Traefik 部署推荐）。
  const apiBase = process.env.API_BASE ?? "";
  const apiBaseInit = `window.__API_BASE__=${JSON.stringify(apiBase)};`;

  return (
    <html
      lang="zh-CN"
      className={`${inter.variable} ${notoSerifSC.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: apiBaseInit }} />
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
