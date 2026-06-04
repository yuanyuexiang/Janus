# Frontend —— Next.js 16，多阶段构建，standalone 产物
# 注意：NEXT_PUBLIC_API_BASE 是「构建时」注入（浏览器端代码里被内联），
# 必须在 build 阶段传入对公网可达的后端地址，例如 https://你的域名/api 所在主机。

# node 版本要 ≥ 22.13（pnpm 11 的要求）。corepack 按 package.json 的
# packageManager 字段（pnpm@11.2.2）选版本，不会乱拉最新。

# ---- 依赖 ----
FROM node:22-alpine AS deps
WORKDIR /app
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
# pnpm-workspace.yaml 带着 allowBuilds 设置（放行 sharp / unrs-resolver 的编译）
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# ---- 构建 ----
FROM node:22-alpine AS builder
WORKDIR /app
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# 构建时注入公网 API 地址
ARG NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# ---- 运行 ----
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# 非 root 运行
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
