"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AccountControls } from "@/components/chat/account-controls";
import { ThemeToggle } from "@/components/chat/theme-toggle";

type RailItemDef = {
  href: string;
  label: string;
  icon: React.ReactNode;
};

// 极简线性图标，stroke=currentColor，跟古典调性不冲突
const ChatIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-5 w-5">
    <path d="M4 5.5h16v10H9l-4 3.5v-3.5H4z" strokeLinejoin="round" />
  </svg>
);

const StatusIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-5 w-5">
    <path d="M3 13h3.5l2-6 3.5 12 2.5-7 1.5 3H21" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// 模型配置：滑块/调节，象征「调模型」
const ModelIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-5 w-5">
    <path d="M5 8h9M17 8h2M5 16h2M10 16h9" strokeLinecap="round" />
    <circle cx="15" cy="8" r="2" />
    <circle cx="8.5" cy="16" r="2" />
  </svg>
);

const ITEMS: RailItemDef[] = [
  { href: "/chat", label: "对话", icon: ChatIcon },
  { href: "/status", label: "服务状态", icon: StatusIcon },
  { href: "/settings", label: "模型配置", icon: ModelIcon },
];

export function NavRail() {
  const pathname = usePathname();

  return (
    <nav className="flex w-[76px] shrink-0 flex-col items-center border-r border-parchment-300/60 bg-parchment-50/70 py-4 dark:border-walnut-300/20 dark:bg-walnut-900/50">
      {/* 桌字金印 */}
      <Link
        href="/"
        title="返回首页"
        className="relative mb-6 flex h-11 w-11 items-center justify-center no-underline"
      >
        <span className="absolute inset-0 rounded-full border border-gilt-500/50" />
        <span className="absolute inset-[5px] rounded-full border border-gilt-500/30" />
        <span className="font-display text-lg text-gilt-700 dark:text-gilt-300">桌</span>
      </Link>

      {/* 导航项 */}
      <div className="flex flex-col items-stretch gap-1 self-stretch px-2">
        {ITEMS.map((it) => {
          const on = pathname === it.href || pathname.startsWith(it.href + "/");
          return (
            <Link
              key={it.href}
              href={it.href}
              aria-current={on ? "page" : undefined}
              title={it.label}
              className={`relative flex flex-col items-center gap-1 rounded-sm py-2.5 no-underline transition-colors ${
                on
                  ? "bg-gilt-500/[0.12] text-gilt-700 dark:bg-gilt-500/15 dark:text-gilt-200"
                  : "text-walnut-100 hover:bg-parchment-200/50 hover:text-walnut-500 dark:text-parchment-200/60 dark:hover:bg-walnut-700/40 dark:hover:text-gilt-300"
              }`}
            >
              {/* 选中：左侧金箔细条 */}
              {on && <span className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-gilt-500" />}
              {it.icon}
              <span className="font-display text-[10px] tracking-wide">{it.label}</span>
            </Link>
          );
        })}
      </div>

      {/* 底部：主题切换 + 账户控制 */}
      <div className="mt-auto flex flex-col items-stretch self-stretch px-2 pt-2">
        <div className="mx-auto mb-2 h-px w-8 bg-parchment-300/60 dark:bg-walnut-300/30" />
        <ThemeToggle />
        <AccountControls />
      </div>
    </nav>
  );
}
