FROM node:20-alpine AS base

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
COPY web/package.json web/package.json
COPY packages/types/package.json packages/types/package.json

RUN npm ci

FROM base AS development

CMD ["npm", "-w", "web", "run", "dev"]

FROM base AS builder

ARG NEXT_PUBLIC_API_BASE_URL=""
ARG NEXT_PUBLIC_WS_BASE_URL=""
ARG NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID=""

COPY web web
COPY packages/types packages/types
COPY api/uploads api/uploads

ENV NEXT_OUTPUT_MODE=standalone
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_WS_BASE_URL=${NEXT_PUBLIC_WS_BASE_URL}
ENV NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID}

RUN npm -w web run build

FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3500 \
    HOSTNAME=0.0.0.0

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /app/web/.next/standalone ./
COPY --from=builder /app/web/.next/static ./web/.next/static
COPY --from=builder /app/web/public ./web/public
COPY --from=builder /app/api/uploads ./api/uploads

USER app

EXPOSE 3500

CMD ["node", "server.js"]
