FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir poetry==1.8.5 \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser

CMD ["python", "-m", "app.bot"]
