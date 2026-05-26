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
      <p className="text-sm text-red-600 dark:text-red-400">
        Backend unreachable: {error}
      </p>
    );
  }

  if (!data) {
    return <p className="text-sm text-zinc-500">Checking backend…</p>;
  }

  return (
    <ul className="space-y-2 text-sm">
      <li>
        <Badge ok={data.status === "ok"} /> API:{" "}
        <code className="text-zinc-600 dark:text-zinc-400">{data.status}</code>
      </li>
      <li>
        <Badge ok={data.db} /> Postgres:{" "}
        <code className="text-zinc-600 dark:text-zinc-400">
          {data.db ? "connected" : "down"}
        </code>
      </li>
    </ul>
  );
}

function Badge({ ok }: { ok: boolean }) {
  return (
    <span
      className={`mr-2 inline-block h-2 w-2 rounded-full ${
        ok ? "bg-emerald-500" : "bg-red-500"
      }`}
    />
  );
}
