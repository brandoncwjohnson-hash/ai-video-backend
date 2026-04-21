from fastapi import FastAPI
from pydantic import BaseModel
from gtts import gTTS
import uuid
import os
import subprocess
import urllib.request

app = FastAPI()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_DIR = os.getcwd()
BACKGROUND_IMAGE = os.path.join(BASE_DIR, "background.jpg")
BACKGROUND_URL = "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"


class VideoRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"status": "running"}


def ensure_background():
    if not os.path.exists(BACKGROUND_IMAGE):
        urllib.request.urlretrieve(BACKGROUND_URL, BACKGROUND_IMAGE)


@app.post("/generate-audio")
def generate_audio(request: VideoRequest):
    file_id = str(uuid.uuid4())
    audio_path = f"{OUTPUT_DIR}/{file_id}.mp3"

    tts = gTTS(text=request.text, lang="en")
    tts.save(audio_path)

    return {"audio_file": audio_path}


@app.post("/generate-video")
def generate_video(request: VideoRequest):
    try:
        ensure_background()

        file_id = str(uuid.uuid4())

        audio_path = f"{OUTPUT_DIR}/{file_id}.mp3"
        video_path = f"{OUTPUT_DIR}/{file_id}.mp4"

        tts = gTTS(text=request.text, lang="en")
        tts.save(audio_path)

        command = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", BACKGROUND_IMAGE,
            "-i", audio_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            video_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        return {
            "ffmpeg_return_code": result.returncode,
            "ffmpeg_error": result.stderr,
            "video_file": video_path,
            "audio_file": audio_path
        }

    except Exception as e:
        return {"error": str(e)}
