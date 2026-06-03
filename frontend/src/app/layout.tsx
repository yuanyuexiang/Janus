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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // 解析期同步执行：绘制前从 localStorage / 系统偏好定下 data-theme，避免主题闪烁
  const themeInit = `(function(){try{var t=localStorage.getItem('atlas-theme');if(t!=='light'&&t!=='dark'&&t!=='nasdaq'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme='light';}})();`;

  return (
    <html lang="zh-CN" className={`${inter.variable} ${notoSerifSC.variable} h-full`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
