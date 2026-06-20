import { NavRail } from "@/components/chat/nav-rail";
import { ConsoleGuard } from "@/components/console-guard";

/**
 * 控制台外壳：最左导航栏（对话 / 服务状态 + 主题切换）常驻，
 * 右侧内容区由具体路由（/chat、/status、/settings）填充。
 * ConsoleGuard 在进入前确认已解锁，避免未登录直接深链时先发一串 401。
 */
export default function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ConsoleGuard>
      <div className="flex h-screen">
        <NavRail />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {children}
        </div>
      </div>
    </ConsoleGuard>
  );
}
