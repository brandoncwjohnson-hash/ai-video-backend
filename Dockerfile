FROM python:3.10

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0

# copy backend
COPY . /app

# install python deps
RUN pip install --upgrade pip
RUN pip install fastapi uvicorn requests pydantic edge-tts

# clone SadTalker
RUN git clone https://github.com/OpenTalker/SadTalker.git

# install SadTalker deps
RUN pip install -r SadTalker/requirements.txt || true

# expose port
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
