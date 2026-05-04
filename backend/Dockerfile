FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Playwright dependencies
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# spaCy model
RUN python -m spacy download en_core_web_sm

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4", "--loop", "uvloop"]
