"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getAccessKey, isAuthRequired, setAccessKey, verifyAccessKey } from "@/lib/auth";

type Gate = "checking" | "locked" | "open";

const ENTER_BTN =
  "group inline-flex items-center gap-2 rounded-lg border border-walnut-500 bg-walnut-500 px-5 py-2.5 font-display text-[13px] tracking-wider text-parchment-100 no-underline shadow-paper transition-all hover:border-walnut-700 hover:bg-walnut-700 hover:shadow-paper-lg dark:border-gilt-500 dark:bg-gilt-500 dark:text-walnut-900 dark:hover:bg-gilt-300 nasdaq:border-gilt-500 nasdaq:bg-gilt-500 nasdaq:text-parchment-50 nasdaq:hover:bg-gilt-300";

export function EntryGate() {
  const router = useRouter();
  const [gate, setGate] = useState<Gate>("checking");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      const required = await isAuthRequired();
      if (!alive) return;
      if (!required) {
        setGate("open");
        return;
      }
      const k = getAccessKey();
      if (k && (await verifyAccessKey(k))) {
        if (alive) setGate("open");
      } else if (alive) {
        setGate("locked");
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function unlock(e: React.FormEvent) {
    e.preventDefault();
    const key = pw.trim();
    if (!key || busy) return;
    setBusy(true);
    setErr(null);
    const ok = await verifyAccessKey(key);
    setBusy(false);
    if (ok) {
      setAccessKey(key);
      router.push("/chat");
    } else {
      setErr("密码不正确");
      setPw("");
    }
  }

  if (gate === "checking") {
    return <div className="h-10 w-32 animate-pulse rounded-lg bg-parchment-200/60 dark:bg-walnut-300/20" />;
  }

  if (gate === "open") {
    return (
      <Link href="/chat" className={ENTER_BTN}>
        进入对话
        <span className="text-base leading-none transition-transform group-hover:translate-x-0.5">→</span>
      </Link>
    );
  }

  // locked：密码解锁
  return (
    <form onSubmit={unlock} className="flex w-full max-w-sm flex-col items-center gap-2.5">
      <div className="flex w-full items-center gap-2 rounded-xl border border-parchment-300/70 bg-parchment-50 py-2 pl-4 pr-2 shadow-paper transition focus-within:border-gilt-500/70 focus-within:ring-2 focus-within:ring-gilt-500/20 dark:border-walnut-300/35 dark:bg-walnut-700/50 dark:focus-within:border-gilt-300/60 dark:focus-within:ring-gilt-300/20">
        {/* 锁图标 */}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4 shrink-0 text-walnut-50/60 dark:text-parchment-200/40">
          <rect x="5" y="10.5" width="14" height="9" rx="2" />
          <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" strokeLinecap="round" />
        </svg>
        <input
          type="password"
          value={pw}
          onChange={(e) => {
            setPw(e.target.value);
            setErr(null);
          }}
          autoFocus
          placeholder="输入访问密码"
          aria-label="访问密码"
          className="min-w-0 flex-1 bg-transparent py-1 font-display text-[14px] text-ink-900 placeholder:text-walnut-50/50 focus:outline-none dark:text-parchment-100 dark:placeholder:text-parchment-200/40"
        />
        <button
          type="submit"
          disabled={busy || !pw.trim()}
          className="inline-flex h-8 shrink-0 items-center rounded-lg bg-walnut-500 px-4 font-display text-[12px] tracking-wider text-parchment-100 transition-colors hover:bg-walnut-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-gilt-500 dark:text-walnut-900 dark:hover:bg-gilt-300 nasdaq:bg-gilt-500 nasdaq:text-parchment-50 nasdaq:hover:bg-gilt-300"
        >
          {busy ? "验证中…" : "解锁"}
        </button>
      </div>
      {err && (
        <p className="font-display text-[12px] text-vermillion-700 dark:text-vermillion-300">{err}</p>
      )}
      <p className="font-display text-[11px] italic text-ink-400 dark:text-parchment-200/40">
        本应用仅限受邀使用，需访问密码方可进入。
      </p>
    </form>
  );
}
