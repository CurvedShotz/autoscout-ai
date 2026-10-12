FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY app ./app

RUN uv sync --locked --no-dev \
    && useradd --system --create-home --home-dir /home/autoscout --shell /usr/sbin/nologin autoscout \
    && chown -R autoscout:autoscout /app

USER autoscout

EXPOSE 8080

CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8080}\""]
