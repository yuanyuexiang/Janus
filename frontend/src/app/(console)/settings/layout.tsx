"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SUB = [
  { href: "/settings/models", label: "模型设置", desc: "可用模型 / 凭据" },
  { href: "/settings/roles", label: "角色设置", desc: "执棋 / 顾问 / 路由 用哪个" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">
      {/* 二级子导航（微信「设置」式中间列）*/}
      <aside className="flex w-[170px] shrink-0 flex-col border-r border-parchment-300/60 bg-parchment-50/60 md:w-[200px] dark:border-walnut-300/20 dark:bg-walnut-900/40">
        <div className="border-b border-parchment-300/60 px-4 py-[18px] dark:border-walnut-300/20">
          <h1 className="font-display text-lg font-medium text-walnut-500 dark:text-parchment-100">
            设置
          </h1>
        </div>
        <nav className="flex flex-col gap-0.5 p-2">
          {SUB.map((s) => {
            const on = pathname === s.href || pathname.startsWith(s.href + "/");
            return (
              <Link
                key={s.href}
                href={s.href}
                aria-current={on ? "page" : undefined}
                className={`relative rounded-lg px-3 py-2.5 no-underline transition-colors ${
                  on
                    ? "bg-gilt-500/[0.12] dark:bg-gilt-500/15"
                    : "hover:bg-parchment-200/50 dark:hover:bg-walnut-700/40"
                }`}
              >
                {on && <span className="absolute inset-y-2 left-0 w-[2px] rounded-full bg-gilt-500" />}
                <span
                  className={`block font-display text-[13.5px] ${
                    on
                      ? "text-gilt-700 dark:text-gilt-200"
                      : "text-walnut-500 dark:text-parchment-100"
                  }`}
                >
                  {s.label}
                </span>
                <span className="mt-0.5 block font-display text-[10.5px] text-ink-400 dark:text-parchment-200/45">
                  {s.desc}
                </span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* 内容（第三列）*/}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{children}</div>
    </div>
  );
}
