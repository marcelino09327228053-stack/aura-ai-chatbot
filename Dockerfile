FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev postgresql-client gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --system --uid 10001 --create-home aura \
    && mkdir -p app/infrastructure/backups/storage app/infrastructure/logs static .private \
    && chown -R aura:aura /app

ENV AURA_ENV=production
ENV DB_BACKEND=postgres
ENV REDIS_ENABLED=true
ENV PLUGINS_ENABLED=true
ENV AGENTS_ENABLED=true

EXPOSE 8000

USER aura

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
