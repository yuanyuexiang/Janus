"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export type MarkdownProps = {
  children: string;
  className?: string;
};

/**
 * Streaming-safe markdown renderer. Uses GFM (tables, strikethrough, task lists).
 * Tailwind utilities are applied per-element instead of via `@tailwind/typography`
 * to keep bundle small and styling consistent with the rest of the chat UI.
 */
export function Markdown({ children, className }: MarkdownProps) {
  return (
    <div className={`text-sm leading-relaxed text-zinc-800 dark:text-zinc-200 ${className ?? ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="mt-3 mb-2 text-base font-semibold" {...p} />,
          h2: (p) => <h2 className="mt-3 mb-2 text-base font-semibold" {...p} />,
          h3: (p) => <h3 className="mt-3 mb-1.5 text-sm font-semibold" {...p} />,
          h4: (p) => <h4 className="mt-2 mb-1 text-sm font-medium" {...p} />,
          p: (p) => <p className="my-1.5" {...p} />,
          ul: (p) => <ul className="my-1.5 ml-5 list-disc space-y-0.5" {...p} />,
          ol: (p) => <ol className="my-1.5 ml-5 list-decimal space-y-0.5" {...p} />,
          li: (p) => <li className="leading-relaxed" {...p} />,
          strong: (p) => <strong className="font-semibold text-zinc-900 dark:text-zinc-100" {...p} />,
          em: (p) => <em className="italic" {...p} />,
          code: ({ children, ...rest }) => (
            <code
              className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-[0.85em] text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200"
              {...rest}
            >
              {children}
            </code>
          ),
          pre: (p) => (
            <pre
              className="my-2 overflow-x-auto rounded bg-zinc-100 p-2 text-xs dark:bg-zinc-800"
              {...p}
            />
          ),
          blockquote: (p) => (
            <blockquote
              className="my-2 border-l-2 border-zinc-300 pl-3 italic text-zinc-600 dark:border-zinc-700 dark:text-zinc-400"
              {...p}
            />
          ),
          table: (p) => (
            <div className="my-2 overflow-x-auto">
              <table className="w-full border-collapse text-xs" {...p} />
            </div>
          ),
          thead: (p) => <thead className="bg-zinc-100 dark:bg-zinc-800" {...p} />,
          th: (p) => (
            <th
              className="border border-zinc-200 px-2 py-1 text-left font-medium dark:border-zinc-700"
              {...p}
            />
          ),
          td: (p) => <td className="border border-zinc-200 px-2 py-1 dark:border-zinc-700" {...p} />,
          a: (p) => (
            <a className="text-amber-700 underline hover:text-amber-800 dark:text-amber-400" {...p} />
          ),
          hr: () => <hr className="my-3 border-zinc-200 dark:border-zinc-700" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
