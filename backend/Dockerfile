FROM python:3.12-slim AS builder

RUN pip install uv==0.5
WORKDIR /app

COPY pyproject.toml uv.lock .
RUN uv sync --no-dev --frozen

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /app/.venv .venv
COPY src/ src/
COPY data/ data/

EXPOSE 8000

CMD ["python", "-m", "advisor"]
