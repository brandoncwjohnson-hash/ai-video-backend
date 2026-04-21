from fastapi import FastAPI
from pydantic import BaseModel
from gtts import gTTS
import uuid
import os
import subprocess
import urllib.request

app = FastAPI()

OUTPUT_DIR = "outputs"
BASE_DIR = os.getcwd()

BACKGROUND_IMAGE = os.path.join(BASE_DIR, "background.jpg")
BACKGROUND_URL = "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"

os.makedirs(OUTPUT_DIR, exist_ok=True)


class VideoRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"status": "running"}


def ensure_background_exists():
    if not os.path.exists(BACKGROUND_IMAGE):
        urllib.request.urlretrieve(BACKGROUND_URL, BACKGROUND_IMAGE)


@app.post("/generate-video")
def generate_video(request: VideoRequest):
    ensure_background_exists()

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
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        video_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        return {
            "error": "FFmpeg failed",
            "details": result.stderr
        }

    return {
        "video_file": video_path,
        "audio_file": audio_path
    }
