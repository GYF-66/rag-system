FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN sed -i 's#https://registry\\.npmmirror\\.com/#https://registry.npmjs.org/#g' package-lock.json \
    && npm config set registry https://registry.npmjs.org/ \
    && npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm config set prefer-online true \
    && npm config set audit false \
    && npm config set fund false \
    && npm ci --legacy-peer-deps --no-audit --fund=false

COPY . .
RUN npm run build

FROM nginx:alpine AS production

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
