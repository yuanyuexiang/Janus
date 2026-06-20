"use client";

import { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { getAccessKey, isAuthRequired } from "@/lib/auth";

/**
 * 控制台门卫：进入 /chat、/status、/settings 等页面前确认已解锁。
 * - 本地已有访问密钥 → 乐观放行（密钥失效时 API 调用会 401 → handleUnauthorized 跳回首页）。
 * - 没有密钥但后端要求鉴权 → 直接跳回首页解锁，避免先发一串 401。
 * - 后端未启用密码 → 放行。
 * 布局只在进入 console 区时挂载一次，不会每次子路由切换都重跑。
 */
export function ConsoleGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    if (getAccessKey()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setOk(true);
      return;
    }
    let alive = true;
    (async () => {
      const required = await isAuthRequired();
      if (!alive) return;
      if (required) router.replace("/");
      else setOk(true);
    })();
    return () => {
      alive = false;
    };
  }, [router]);

  if (!ok) {
    return (
      <div className="flex h-full flex-1 items-center justify-center">
        <div className="h-10 w-32 animate-pulse rounded-lg bg-parchment-200/60 dark:bg-walnut-300/20" />
      </div>
    );
  }
  return <>{children}</>;
}
