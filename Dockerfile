FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/tracker.db \
    BACKUP_DIR=/data/backups \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && \
    useradd --system --gid app --create-home --home-dir /home/app app && \
    mkdir -p /app/logs /data /data/backups && \
    chown -R app:app /app /data

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R app:app /app

USER app

CMD ["python", "bot.py"]
