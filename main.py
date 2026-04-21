from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gtts import gTTS
import uuid
import os
import subprocess

app = FastAPI()

# -----------------------------
# CONFIG
# -----------------------------
OUTPUT_DIR = "outputs"
BACKGROUND_IMAGE = "background.jpg"  # put any jpg/png in your project root

os.makedirs(OUTPUT_DIR, exist_ok=True)


# -----------------------------
# MODELS
# -----------------------------
class AudioRequest(BaseModel):
    text: str


class VideoRequest(BaseModel):
    text: str


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
def home():
    return {"status": "running"}


# -----------------------------
# AUDIO GENERATION ONLY
# -----------------------------
@app.post("/generate-audio")
def generate_audio(request: AudioRequest):
    try:
        file_id = str(uuid.uuid4())
        file_path = f"{OUTPUT_DIR}/{file_id}.mp3"

        tts = gTTS(text=request.text, lang="en")
        tts.save(file_path)

        return {"audio_file": file_path}

    except Exception as e:
        return {"error": str(e)}


# -----------------------------
# VIDEO GENERATION (AUDIO + IMAGE + FFMPEG)
# -----------------------------
@app.post("/generate-video")
def generate_video(request: VideoRequest):
    try:
        file_id = str(uuid.uuid4())

        audio_path = f"{OUTPUT_DIR}/{file_id}.mp3"
        video_path = f"{OUTPUT_DIR}/{file_id}.mp4"

        # 1. Create audio from text
        tts = gTTS(text=request.text, lang="en")
        tts.save(audio_path)

        # 2. Build video using FFmpeg
        # (loop background image + audio → video)
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

        subprocess.run(command, check=True)

        return {
            "video_file": video_path,
            "audio_file": audio_path
        }

    except Exception as e:
        return {"error": str(e)}
