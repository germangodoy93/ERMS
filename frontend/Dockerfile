# syntax=docker/dockerfile:1
# ERMS web client. `dev` target for docker compose, `prod` target for Railway.

FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- Development: Vite dev server with HMR, source mounted as a volume -------
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"]

# --- Build static assets -----------------------------------------------------
FROM deps AS build
COPY . .
RUN npm run build

# --- Production: Caddy serves the SPA and reverse-proxies /api to the backend --
FROM caddy:2.10-alpine AS prod
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 8080
