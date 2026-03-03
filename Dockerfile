# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Evita file .pyc e abilita output non bufferizzato
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Installa dipendenze prima (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice sorgente (nuova struttura v2)
COPY main.py .
COPY bot/ ./bot/
COPY db/ ./db/
COPY services/ ./services/
COPY scheduler/ ./scheduler/

# Volume per persistere il database SQLite
VOLUME ["/app/data"]
ENV DB_PATH=/app/data/busbot.db

EXPOSE 8080

CMD ["python", "main.py"]
