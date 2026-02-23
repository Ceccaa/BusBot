# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Evita file .pyc e abilita output non bufferizzato
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Installa dipendenze prima (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice sorgente
COPY main.py bot.py scraper.py config.py ./

# Volume per persistere la configurazione utenti
VOLUME ["/app/data"]
ENV CONFIG_PATH=/app/data/user_config.json

CMD ["python", "main.py"]
