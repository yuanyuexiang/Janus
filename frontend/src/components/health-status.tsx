"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type ChoiceStatus = { configured: boolean; reachable: boolean; logged_in: boolean };
type Health = {
  status: string;
  db: boolean;
  data_source?: { chain: string[]; choice: ChoiceStatus };
};

// 数据源链里 provider 名 → 中文显示
const PROVIDER_LABEL: Record<string, string> = {
  choice: "东方财富 Choice",
  tushare: "Tushare",
  mock: "内置样例",
};

// Choice 子状态 → 文案 + 是否正常
function choiceNote(c: ChoiceStatus): { note: string; ok: boolean } {
  if (!c.configured) return { note: "未启用", ok: false };
  if (!c.reachable) return { note: "网关离线", ok: false };
  if (!c.logged_in) return { note: "待激活", ok: false };
  return { note: "已就绪", ok: true };
}

export function HealthStatus() {
  const [data, setData] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Health>("/api/health")
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) {
    return (
      <p className="font-display text-[13px] italic text-vermillion-500 dark:text-vermillion-300">
        后端无响应：{error}
      </p>
    );
  }

  if (!data) {
    return (
      <p className="font-display text-[13px] italic text-walnut-50/70 dark:text-parchment-200/50">
        正在确认…
      </p>
    );
  }

  const ds = data.data_source;
  const choice = ds?.choice;

  return (
    <ul className="space-y-2 text-[13px]">
      <Row label="API" ok={data.status === "ok"} note={data.status} />
      <Row label="Postgres" ok={data.db} note={data.db ? "connected" : "down"} />
      {choice && (
        <Row label="Choice 数据" {...choiceNote(choice)} />
      )}
      {ds && ds.chain.length > 0 && (
        <li className="flex items-center justify-between gap-3 pt-1">
          <span className="font-display text-walnut-50 dark:text-parchment-200/60">数据链路</span>
          <span className="font-mono text-[11px] text-ink-600 dark:text-parchment-200/60">
            {ds.chain.map((p) => PROVIDER_LABEL[p] ?? p).join(" → ")}
          </span>
        </li>
      )}
    </ul>
  );
}

function Row({ label, ok, note }: { label: string; ok: boolean; note: string }) {
  return (
    <li className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2">
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            ok ? "bg-sage-500" : "bg-vermillion-500"
          }`}
        />
        <span className="font-display text-walnut-500 dark:text-parchment-100">{label}</span>
      </span>
      <code className="font-mono text-[11px] text-ink-600 dark:text-parchment-200/60">
        {note}
      </code>
    </li>
  );
}
