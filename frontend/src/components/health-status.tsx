"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type Health = { status: string; db: boolean };

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

  return (
    <ul className="space-y-2 text-[13px]">
      <Row label="API" ok={data.status === "ok"} note={data.status} />
      <Row label="Postgres" ok={data.db} note={data.db ? "connected" : "down"} />
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
