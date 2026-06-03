"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark" | "nasdaq";

const ORDER: Theme[] = ["light", "dark", "nasdaq"];

const META: Record<Theme, { label: string; icon: React.ReactNode }> = {
  light: {
    label: "古典",
    // 太阳
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" strokeLinecap="round" />
      </svg>
    ),
  },
  dark: {
    label: "夜读",
    // 月亮
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]">
        <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" strokeLinejoin="round" />
      </svg>
    ),
  },
  nasdaq: {
    label: "终端",
    // K 线柱
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]">
        <path d="M5 4v16M5 8h3M5 14h3M12 4v16M12 7h3M12 16h3M19 4v16M19 10h-3M19 13h-3" strokeLinecap="round" />
      </svg>
    ),
  },
};

function readTheme(): Theme {
  if (typeof document === "undefined") return "light";
  const t = document.documentElement.dataset.theme;
  return t === "dark" || t === "nasdaq" ? t : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  // 挂载后与 <html data-theme>（由 layout 内联脚本在水合前设好）同步 ——
  // 这是把外部 DOM 状态读进 React 的一次性同步，非级联渲染。
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(readTheme());
  }, []);

  function cycle() {
    const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("atlas-theme", next);
    } catch {
      /* localStorage 不可用也无妨 */
    }
    setTheme(next);
  }

  const meta = META[theme];

  return (
    <button
      type="button"
      onClick={cycle}
      title={`主题：${meta.label}（点击切换）`}
      aria-label={`切换主题，当前 ${meta.label}`}
      className="flex flex-col items-center gap-1 rounded-sm py-2.5 text-walnut-100 transition-colors hover:bg-parchment-200/50 hover:text-walnut-500 dark:text-parchment-200/60 dark:hover:bg-walnut-700/40 dark:hover:text-gilt-300"
    >
      {meta.icon}
      <span className="font-display text-[10px] tracking-wide">{meta.label}</span>
    </button>
  );
}
