FROM python:3.11-slim

# =========================
# SYSTEM DEPENDENCIES
# =========================

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# WORKDIR
# =========================

WORKDIR /app

# =========================
# PYTHON DEPENDENCIES
# =========================

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    requests \
    edge-tts

# =========================
# COPY CODE
# =========================

COPY . .

# =========================
# START SERVER
# =========================

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
