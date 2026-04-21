FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (FFmpeg is required for your video engine)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy entire backend code into container
COPY . .

# IMPORTANT: Force correct port for Coolify / Traefik
ENV PORT=8000

# IMPORTANT: Ensure correct module is used
# CHANGE THIS LINE depending on your file name:
# If your main file is main.py → keep main:app
# If your file is video_factory.py → change to video_factory:app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
