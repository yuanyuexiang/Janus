import { API_BASE } from "@/lib/api";

const KEY = "atlas-access-key";

export function getAccessKey(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setAccessKey(key: string) {
  try {
    localStorage.setItem(KEY, key);
  } catch {
    /* 忽略 */
  }
}

export function clearAccessKey() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* 忽略 */
  }
}

/** 把访问密钥拼进请求头（有才拼）。 */
export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const k = getAccessKey();
  return { ...(extra ?? {}), ...(k ? { "X-Access-Key": k } : {}) };
}

/** 后端是否要求访问密钥。 */
export async function isAuthRequired(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/status`, { cache: "no-store" });
    if (!res.ok) return false;
    const body = (await res.json()) as { required: boolean };
    return !!body.required;
  } catch {
    return false;
  }
}

/** 用给定密钥向后端验证；正确返回 true。 */
export async function verifyAccessKey(key: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/check`, {
      cache: "no-store",
      headers: { "X-Access-Key": key },
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** 退出：清掉本地密钥并回首页解锁。 */
export function logout() {
  clearAccessKey();
  if (typeof window !== "undefined") window.location.href = "/";
}

/** 改密码：校验当前密码 → 落盘新密码。成功后本地密钥更新为新密码。
 * 返回 null 表示成功，否则返回错误信息。 */
export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/change`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    if (res.ok) {
      setAccessKey(newPassword); // 让当前会话继续有效
      return null;
    }
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    return body?.detail ?? `修改失败（${res.status}）`;
  } catch {
    return "网络错误，请重试";
  }
}
