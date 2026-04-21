from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gtts import gTTS
import uuid
import os
import subprocess

app = FastAPI()

OUTPUT_DIR = "outputs"
BACKGROUND_IMAGE = "background.jpg"

os.makedirs(OUTPUT_DIR, exist_ok=True)


class AudioRequest(BaseModel):
    text: str


class VideoRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"status": "running"}


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


@app.post("/generate-video")
def generate_video(request: VideoRequest):
    try:
        file_id = str(uuid.uuid4())

        audio_path = f"{OUTPUT_DIR}/{file_id}.mp3"
        video_path = f"{OUTPUT_DIR}/{file_id}.mp4"

        # Create audio
        tts = gTTS(text=request.text, lang="en")
        tts.save(audio_path)

        # FFmpeg command
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

        # 🔥 IMPORTANT FIX: show real FFmpeg error
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

    except Exception as e:
        return {"error": str(e)}
