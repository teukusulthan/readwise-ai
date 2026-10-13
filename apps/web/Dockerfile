# syntax=docker/dockerfile:1.7
# Readwise AI web (Vite build served by nginx). Build context: apps/web/
#   docker build -t readwise-web apps/web

# ---- build -----------------------------------------------------------------
FROM node:22.23.2-bookworm-slim AS build
WORKDIR /app

# patch-package runs as the postinstall hook, so patches/ must exist before `npm ci`.
COPY package.json package-lock.json ./
COPY patches ./patches
RUN --mount=type=cache,target=/root/.npm npm ci

# VITE_* values are compiled into the bundle, so they are build arguments, not runtime settings.
# The Mapbox token is a public client-side token: it ships inside the JS bundle by design.
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_AUTH_ENABLED=false
# hadolint ignore=DL3064
ARG VITE_MAPBOX_TOKEN=
# hadolint ignore=DL3064
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_AUTH_ENABLED=$VITE_AUTH_ENABLED \
    VITE_MAPBOX_TOKEN=$VITE_MAPBOX_TOKEN

COPY . .
RUN npx vite build

# ---- runtime: unprivileged nginx (listens on 8080, runs as user nginx) -------
FROM nginxinc/nginx-unprivileged:1.27.5-alpine AS runtime

# Runtime settings, substituted into the template by the image's envsubst step:
#   BACKEND_UPSTREAM        where /api/v1/apps/ is proxied (prefix stripped, like the Vite dev proxy)
#   ICON_CDN_PROXY_TARGET   icon font CDN behind /cdn-assets/ (empty = location answers 404)
ENV BACKEND_UPSTREAM=http://backend:8020 \
    ICON_CDN_PROXY_TARGET=

COPY docker/default.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=755 docker/15-cdn-assets.sh /docker-entrypoint.d/15-cdn-assets.sh
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
