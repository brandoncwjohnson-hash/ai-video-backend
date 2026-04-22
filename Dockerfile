FROM python:3.11-slim

WORKDIR /app

# install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# install python deps
RUN pip install --no-cache-dir fastapi uvicorn requests edge-tts

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
