FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache

RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

RUN chmod +x entrypoint.sh
