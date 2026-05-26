import { HealthStatus } from "@/components/health-status";

export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <div className="mx-auto max-w-2xl px-6 py-24">
        <header className="mb-12">
          <p className="text-sm uppercase tracking-widest text-amber-700 dark:text-amber-400">
            Atlas Council
          </p>
          <h1 className="mt-2 text-4xl font-semibold text-zinc-900 dark:text-zinc-50">
            圆桌投研
          </h1>
          <p className="mt-3 text-base text-zinc-600 dark:text-zinc-400">
            一桌专家智囊团，陪你看清每一笔投资
          </p>
        </header>

        <section className="rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-zinc-500">
            M0 · Skeleton
          </h2>
          <HealthStatus />
        </section>

        <footer className="mt-12 text-xs text-zinc-500">
          MVP scaffolding · 后端 FastAPI · 前端 Next.js 15
        </footer>
      </div>
    </main>
  );
}
