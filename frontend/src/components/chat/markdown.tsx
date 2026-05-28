"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export type MarkdownProps = {
  children: string;
  className?: string;
};

/**
 * 流式安全的 Markdown 渲染器，配色对齐 Atlas Council 视觉系统
 *（羊皮纸 / 胡桃木 / 金箔）。
 * 直接逐元素覆盖样式，不引入 @tailwind/typography，目的是控制 bundle 体积
 * 和保留样式自主权。
 */
export function Markdown({ children, className }: MarkdownProps) {
  return (
    <div
      className={`text-[14px] leading-7 text-ink-900 dark:text-parchment-100 ${className ?? ""}`}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => (
            <h1
              className="mt-4 mb-2 font-display text-base font-medium text-walnut-500 dark:text-parchment-100"
              {...p}
            />
          ),
          h2: (p) => (
            <h2
              className="mt-4 mb-2 font-display text-base font-medium text-walnut-500 dark:text-parchment-100"
              {...p}
            />
          ),
          h3: (p) => (
            <h3
              className="mt-3 mb-1.5 font-display text-[14px] font-medium text-walnut-500 dark:text-parchment-100"
              {...p}
            />
          ),
          h4: (p) => (
            <h4
              className="mt-3 mb-1 font-display text-[13.5px] font-medium text-walnut-500 dark:text-parchment-100"
              {...p}
            />
          ),
          p: (p) => <p className="my-1.5" {...p} />,
          ul: (p) => (
            <ul
              className="my-1.5 ml-5 list-[square] marker:text-gilt-700 space-y-0.5 dark:marker:text-gilt-300"
              {...p}
            />
          ),
          ol: (p) => (
            <ol
              className="my-1.5 ml-5 list-decimal marker:font-display marker:text-gilt-700 space-y-0.5 dark:marker:text-gilt-300"
              {...p}
            />
          ),
          li: (p) => <li className="leading-relaxed" {...p} />,
          strong: (p) => (
            <strong
              className="font-semibold text-walnut-500 dark:text-parchment-100"
              {...p}
            />
          ),
          em: (p) => <em className="font-display italic" {...p} />,
          code: ({ children, ...rest }) => (
            <code
              className="rounded-sm border border-parchment-300/60 bg-parchment-100/60 px-1 py-px font-mono text-[0.85em] text-walnut-500 dark:border-walnut-300/30 dark:bg-walnut-700/40 dark:text-parchment-100"
              {...rest}
            >
              {children}
            </code>
          ),
          pre: (p) => (
            <pre
              className="my-2 overflow-x-auto rounded-sm border border-parchment-300/60 bg-parchment-50/80 p-3 font-mono text-[11px] text-ink-600 dark:border-walnut-300/30 dark:bg-walnut-900/40 dark:text-parchment-200/80"
              {...p}
            />
          ),
          blockquote: (p) => (
            <blockquote
              className="my-2 border-l-2 border-gilt-500/60 pl-3 font-display not-italic text-ink-600 dark:text-parchment-200/80"
              {...p}
            />
          ),
          table: (p) => (
            <div className="my-3 overflow-x-auto">
              <table className="w-full border-collapse text-[12.5px]" {...p} />
            </div>
          ),
          thead: (p) => (
            <thead
              className="bg-parchment-200/60 font-display dark:bg-walnut-700/50"
              {...p}
            />
          ),
          th: (p) => (
            <th
              className="border border-parchment-300/70 px-2.5 py-1.5 text-left font-medium text-walnut-500 dark:border-walnut-300/30 dark:text-parchment-100"
              {...p}
            />
          ),
          td: (p) => (
            <td
              className="border border-parchment-300/70 px-2.5 py-1.5 dark:border-walnut-300/30"
              {...p}
            />
          ),
          a: (p) => (
            <a
              className="text-walnut-500 underline decoration-gilt-500 underline-offset-2 hover:text-gilt-700 dark:text-gilt-300 dark:decoration-gilt-700 dark:hover:text-gilt-100"
              {...p}
            />
          ),
          hr: () => (
            <hr className="my-4 border-t border-parchment-300/60 dark:border-walnut-300/30" />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
