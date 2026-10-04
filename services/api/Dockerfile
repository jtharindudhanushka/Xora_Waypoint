# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS deps
COPY services/api/pyproject.toml ./
COPY packages/engine /packages/engine
RUN mkdir app && touch app/__init__.py && pip install --prefix=/install .

FROM base AS runtime
RUN useradd --create-home --uid 10001 xora
COPY --from=deps /install /usr/local
COPY packages/engine /packages/engine
COPY services/api .
RUN pip install --no-deps . && chown -R xora:xora /app
USER xora
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health').status==200 else 1)"
# Migrations + seed run first (docker/entrypoint.sh), then the server.
CMD ["sh", "docker/entrypoint.sh"]
