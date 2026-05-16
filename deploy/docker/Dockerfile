FROM python:3.12-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

RUN useradd -u 10001 -m appuser

COPY backend/requirements.txt backend/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY locales ./locales
COPY data ./data
RUN mkdir -p /app/logs /app/data && chown -R appuser:appuser /app/logs /app/data

USER appuser


FROM python-base AS backend

LABEL org.opencontainers.image.source="https://github.com/3252a8/remnawave-minishop" \
      org.opencontainers.image.title="remnawave-minishop-backend" \
      org.opencontainers.image.description="Remnawave Minishop backend (Telegram bot API, web app, webhooks)." \
      org.opencontainers.image.licenses="MIT"

EXPOSE 8080 8081
CMD ["python", "backend/main_backend.py"]


FROM python-base AS worker

LABEL org.opencontainers.image.source="https://github.com/3252a8/remnawave-minishop" \
      org.opencontainers.image.title="remnawave-minishop-worker" \
      org.opencontainers.image.description="Remnawave Minishop background worker (scheduled jobs, async tasks)." \
      org.opencontainers.image.licenses="MIT"

CMD ["python", "backend/main_worker.py"]


FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend ./
COPY backend/bot/app/web/templates ../backend/bot/app/web/templates

RUN npm run build:webapp


FROM nginx:1.27-alpine AS frontend

LABEL org.opencontainers.image.source="https://github.com/3252a8/remnawave-minishop" \
      org.opencontainers.image.title="remnawave-minishop-frontend" \
      org.opencontainers.image.description="Remnawave Minishop frontend (nginx serving the subscription Mini App)." \
      org.opencontainers.image.licenses="MIT"

COPY deploy/docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker/frontend/00-startup-banner.sh /docker-entrypoint.d/00-startup-banner.sh
COPY backend/bot/app/web/templates/subscription_webapp.html /usr/share/nginx/html/index.html
COPY --from=frontend-builder /app/backend/bot/app/web/templates/subscription_webapp.css /usr/share/nginx/html/subscription_webapp.css
COPY --from=frontend-builder /app/backend/bot/app/web/templates/subscription_webapp.js /usr/share/nginx/html/subscription_webapp.js
COPY --from=frontend-builder /app/backend/bot/app/web/templates/subscription_webapp.min.*.js /usr/share/nginx/html/

RUN sed -i \
      -e '/WEBAPP_I18N_SCRIPT/d' \
      -e '/WEBAPP_CONFIG_SCRIPT/d' \
      -e '/WEBAPP_JS_SCRIPT/c\  <script src="/subscription_webapp.js" type="module"></script>' \
      -e '/WEBAPP_DEV_MOCK_START/d' \
      -e '/WEBAPP_DEV_MOCK_END/d' \
      -e '/subscription_webapp.js" defer/d' \
      /usr/share/nginx/html/index.html \
    && chmod +x /docker-entrypoint.d/00-startup-banner.sh

EXPOSE 80
