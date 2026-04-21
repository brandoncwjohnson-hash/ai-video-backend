FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# IMPORTANT: force clean copy (no caching issues)
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
