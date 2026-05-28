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
  return (
    <html lang="zh-CN" className={`${inter.variable} ${notoSerifSC.variable} h-full`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
