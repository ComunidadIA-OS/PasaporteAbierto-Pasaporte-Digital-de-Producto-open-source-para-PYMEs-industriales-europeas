FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:20-alpine AS builder
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Next inlinea variables NEXT_PUBLIC_* en el bundle del cliente al hacer
# `pnpm build`. Se pasan como ARG desde docker-compose (build.args) y se
# convierten en ENV para que Next las vea. Cambiar su valor exige rebuild.
ARG NEXT_PUBLIC_DEMO_MODE=false
ENV NEXT_PUBLIC_DEMO_MODE=$NEXT_PUBLIC_DEMO_MODE
# Nombre de la cookie de sesión que el proxy de Next comprueba para gatear
# /wizard y /panel. Debe coincidir con AUTH_COOKIE_NAME del backend.
ARG NEXT_PUBLIC_AUTH_COOKIE_NAME=pa_session
ENV NEXT_PUBLIC_AUTH_COOKIE_NAME=$NEXT_PUBLIC_AUTH_COOKIE_NAME
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000 > /dev/null || exit 1
CMD ["pnpm", "start"]
