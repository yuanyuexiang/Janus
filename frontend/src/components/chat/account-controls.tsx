"use client";

import { useEffect, useState } from "react";

import { changePassword, isAuthRequired, logout } from "@/lib/auth";

export function AccountControls() {
  const [show, setShow] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    isAuthRequired().then((req) => {
      if (alive) setShow(req);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!show) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setDialogOpen(true)}
        title="修改访问密码"
        aria-label="修改访问密码"
        className="flex flex-col items-center gap-1 rounded-sm py-2.5 text-walnut-100 transition-colors hover:bg-parchment-200/50 hover:text-walnut-500 dark:text-parchment-200/60 dark:hover:bg-walnut-700/40 dark:hover:text-gilt-300"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]">
          <rect x="5" y="10.5" width="14" height="9" rx="2" />
          <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" strokeLinecap="round" />
        </svg>
        <span className="font-display text-[10px] tracking-wide">改密码</span>
      </button>

      <button
        type="button"
        onClick={logout}
        title="退出登录"
        aria-label="退出登录"
        className="flex flex-col items-center gap-1 rounded-sm py-2.5 text-walnut-100 transition-colors hover:bg-vermillion-500/10 hover:text-vermillion-500 dark:text-parchment-200/60 dark:hover:text-vermillion-300"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]">
          <path d="M14 5H6v14h8M14 12H10M19 12l-3-3M19 12l-3 3M19 12h-9" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="font-display text-[10px] tracking-wide">退出</span>
      </button>

      {dialogOpen && <ChangePasswordDialog onClose={() => setDialogOpen(false)} />}
    </>
  );
}

function ChangePasswordDialog({ onClose }: { onClose: () => void }) {
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setErr(null);
    if (next.length < 4) {
      setErr("新密码至少 4 位");
      return;
    }
    if (next !== confirm) {
      setErr("两次输入的新密码不一致");
      return;
    }
    setBusy(true);
    const msg = await changePassword(cur, next);
    setBusy(false);
    if (msg === null) {
      setDone(true);
      setTimeout(onClose, 1200);
    } else {
      setErr(msg);
    }
  }

  const inputCls =
    "w-full rounded-lg border border-parchment-300/70 bg-parchment-50 px-3 py-2 font-display text-[14px] text-ink-900 placeholder:text-walnut-50/50 focus:border-gilt-500/70 focus:outline-none focus:ring-2 focus:ring-gilt-500/20 dark:border-walnut-300/35 dark:bg-walnut-700/50 dark:text-parchment-100 dark:placeholder:text-parchment-200/40";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button
        type="button"
        onClick={onClose}
        aria-label="关闭"
        className="absolute inset-0 bg-walnut-900/40 backdrop-blur-sm"
      />
      <div className="relative w-full max-w-sm rounded-2xl border border-parchment-300/70 bg-parchment-50 p-6 shadow-paper-lg dark:border-walnut-300/30 dark:bg-walnut-900">
        <h2 className="mb-1 font-display text-lg font-medium text-walnut-500 dark:text-parchment-100">
          修改访问密码
        </h2>
        <p className="mb-5 font-display text-[12px] text-ink-400 dark:text-parchment-200/50">
          修改后所有已登录设备需用新密码重新进入。
        </p>

        {done ? (
          <p className="py-6 text-center font-display text-[14px] text-sage-700 dark:text-sage-300">
            ✓ 密码已更新
          </p>
        ) : (
          <form onSubmit={submit} className="flex flex-col gap-3">
            <input
              type="password"
              value={cur}
              onChange={(e) => { setCur(e.target.value); setErr(null); }}
              autoFocus
              placeholder="当前密码"
              aria-label="当前密码"
              className={inputCls}
            />
            <input
              type="password"
              value={next}
              onChange={(e) => { setNext(e.target.value); setErr(null); }}
              placeholder="新密码（至少 4 位）"
              aria-label="新密码"
              className={inputCls}
            />
            <input
              type="password"
              value={confirm}
              onChange={(e) => { setConfirm(e.target.value); setErr(null); }}
              placeholder="确认新密码"
              aria-label="确认新密码"
              className={inputCls}
            />
            {err && (
              <p className="font-display text-[12px] text-vermillion-700 dark:text-vermillion-300">{err}</p>
            )}
            <div className="mt-1 flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-parchment-300/70 px-4 py-2 font-display text-[13px] tracking-wider text-walnut-100 transition-colors hover:border-walnut-500 hover:text-walnut-500 dark:border-walnut-300/30 dark:text-parchment-200/70 dark:hover:text-parchment-100"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={busy || !cur || !next || !confirm}
                className="rounded-lg bg-walnut-500 px-4 py-2 font-display text-[13px] tracking-wider text-parchment-100 transition-colors hover:bg-walnut-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-gilt-500 dark:text-walnut-900 dark:hover:bg-gilt-300 nasdaq:bg-gilt-500 nasdaq:text-parchment-50 nasdaq:hover:bg-gilt-300"
              >
                {busy ? "提交中…" : "确认修改"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
