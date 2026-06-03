import { NavRail } from "@/components/chat/nav-rail";

/**
 * 控制台外壳：最左导航栏（对话 / 服务状态 + 主题切换）常驻，
 * 右侧内容区由具体路由（/chat、/status）填充。
 */
export default function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen">
      <NavRail />
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {children}
      </div>
    </div>
  );
}
