FROM python:3.10

WORKDIR /app

# =========================
# SYSTEM DEPENDENCIES
# =========================

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# =========================
# COPY APP
# =========================

COPY . /app

# =========================
# PYTHON DEPENDENCIES
# =========================

RUN pip install --upgrade pip

RUN pip install fastapi uvicorn requests pydantic edge-tts

# =========================
# SADTALKER INSTALL (FIXED)
# =========================

RUN rm -rf SadTalker && \
    git clone --depth 1 https://github.com/OpenTalker/SadTalker.git

RUN pip install -r SadTalker/requirements.txt || true

# =========================
# PORT
# =========================

EXPOSE 8000

# =========================
# START SERVER
# =========================

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
