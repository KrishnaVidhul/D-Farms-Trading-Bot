FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/New_York

WORKDIR /app

# Install system dependencies (gcc needed for some python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CRITICAL: Pre-download and cache the FinBERT model during build
# This prevents downloading it every time the container starts/restarts
RUN python -c "from transformers import pipeline; print('Downloading model...'); pipeline('text-classification', model='yiyanghkust/finbert-tone', tokenizer='yiyanghkust/finbert-tone'); print('Model cached.')"

COPY . .

CMD ["python", "main_orchestrator.py"]
