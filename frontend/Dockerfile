# Frontend —— Next.js 16，多阶段构建，standalone 产物
# API 地址不在这里烤死：改成「运行时」由容器环境变量 API_BASE 注入
# （见 src/app/layout.tsx），所以一个镜像可部署到任意域名，compose 里配即可。

# node 版本要 ≥ 22.13（pnpm 11 的要求）。corepack 按 package.json 的
# packageManager 字段（pnpm@11.2.2）选版本，不会乱拉最新。
# NPM_REGISTRY：corepack 下载 pnpm + pnpm 装依赖都走这个源。
# 默认国内镜像（npmjs.org 在国内常超时）；海外构建可传 --build-arg NPM_REGISTRY=https://registry.npmjs.org

# ---- 依赖 ----
FROM node:22-alpine AS deps
WORKDIR /app
ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV COREPACK_NPM_REGISTRY=${NPM_REGISTRY}
ENV npm_config_registry=${NPM_REGISTRY}
RUN corepack enable
# pnpm-workspace.yaml 带着 allowBuilds 设置（放行 sharp / unrs-resolver 的编译）
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
# --registry 显式钉死镜像（env/npmrc 在 pnpm 里有时不生效，flag 优先级最高）
RUN pnpm install --frozen-lockfile --registry=${NPM_REGISTRY}

# ---- 构建 ----
FROM node:22-alpine AS builder
WORKDIR /app
ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV COREPACK_NPM_REGISTRY=${NPM_REGISTRY}
ENV npm_config_registry=${NPM_REGISTRY}
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
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
