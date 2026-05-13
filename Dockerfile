FROM python:3.12-slim AS python-builder

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt


FROM node:22-slim AS webapp-builder

WORKDIR /webapp

COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY bot/app/web/frontend ./bot/app/web/frontend
COPY bot/app/web/templates ./bot/app/web/templates
COPY scripts/build_subscription_webapp_js.mjs ./scripts/build_subscription_webapp_js.mjs

RUN npm run build:webapp


FROM python:3.12-slim

WORKDIR /app

ARG APP_VERSION=""
ARG APP_REVISION=""

LABEL org.opencontainers.image.source="https://github.com/3252a8/remnawave-minishop" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${APP_REVISION}"

RUN useradd -u 10001 -m appuser

COPY --from=python-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends git

COPY . .

# Replace template assets with freshly built ones
RUN rm -f bot/app/web/templates/subscription_webapp.css \
          bot/app/web/templates/subscription_webapp.js \
          bot/app/web/templates/subscription_webapp.min.*.js
COPY --from=webapp-builder /webapp/bot/app/web/templates/subscription_webapp.css \
                           bot/app/web/templates/subscription_webapp.css
COPY --from=webapp-builder /webapp/bot/app/web/templates/subscription_webapp.js \
                           bot/app/web/templates/subscription_webapp.js
COPY --from=webapp-builder /webapp/bot/app/web/templates/subscription_webapp.min.*.js \
                           bot/app/web/templates/

RUN set -eux; \
    if [ -n "$APP_VERSION" ]; then \
      printf '%s\n' "$APP_VERSION" > .build-version; \
    elif [ -d .git ]; then \
      tag="$(git describe --tags --abbrev=0 2>/dev/null || true)"; \
      sha="$(git rev-parse --short HEAD 2>/dev/null || true)"; \
      dirty=""; \
      if ! git diff --quiet --ignore-submodules HEAD 2>/dev/null; then dirty="-dirty"; fi; \
      if [ -n "$tag" ] && [ -n "$sha" ]; then \
        count="$(git rev-list "${tag}..HEAD" --count 2>/dev/null || true)"; \
        if [ -n "$count" ] && [ "$count" != "0" ]; then \
          printf '%s+%s.g%s%s\n' "$tag" "$count" "$sha" "$dirty" > .build-version; \
        else \
          printf '%s%s\n' "$tag" "$dirty" > .build-version; \
        fi; \
      elif [ -n "$sha" ]; then \
        printf 'dev+g%s%s\n' "$sha" "$dirty" > .build-version; \
      else \
        printf 'dev+container\n' > .build-version; \
      fi; \
    else \
      printf 'dev+container\n' > .build-version; \
    fi; \
    if [ -n "$APP_REVISION" ]; then \
      printf '%s\n' "$APP_REVISION" > .build-revision; \
    elif [ -d .git ]; then \
      git rev-parse HEAD > .build-revision 2>/dev/null || printf 'unknown\n' > .build-revision; \
    else \
      printf 'unknown\n' > .build-revision; \
    fi; \
    apt-get purge -y --auto-remove git; \
    rm -rf .git /root/.cache

RUN mkdir -p /app/logs /app/data && chown -R appuser:appuser /app/logs /app/data

USER appuser

CMD ["python", "main.py"]
