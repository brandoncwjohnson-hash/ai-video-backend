import os
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Serve outputs
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


class VideoRequest(BaseModel):
    text: str


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/generate-video")
def generate_video(req: VideoRequest):

    try:
        job_id = str(uuid.uuid4())

        video_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
        audio_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp3")

        # ---------------------------------------------------
        # STEP 1 — GENERATE SIMPLE BACKGROUND VIDEO (NO CDN)
        # ---------------------------------------------------
        subprocess.run([
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "color=c=black:s=720x1280:d=10",
            video_path
        ], check=True)

        # ---------------------------------------------------
        # STEP 2 — GENERATE AUDIO (100% SAFE SILENT TTS REPLACEMENT)
        # ---------------------------------------------------
        subprocess.run([
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "5",
            audio_path
        ], check=True)

        # ---------------------------------------------------
        # STEP 3 — COMBINE VIDEO + AUDIO
        # ---------------------------------------------------
        final_path = os.path.join(OUTPUT_DIR, f"{job_id}_final.mp4")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-vf",
            "format=yuv420p",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-shortest",
            final_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {
                "error": "FFmpeg failed",
                "details": result.stderr
            }

        # ---------------------------------------------------
        # STEP 4 — RETURN DOWNLOAD LINKS
        # ---------------------------------------------------
        return {
            "status": "success",
            "video_url": f"https://vyyo4co8c8r0bkqz7x2xm9sx.178.104.247.146.sslip.io/outputs/{job_id}_final.mp4",
            "audio_file": f"https://vyyo4co8c8r0bkqz7x2xm9sx.178.104.247.146.sslip.io/outputs/{job_id}.mp3"
        }

    except Exception as e:
        return {
            "error": str(e)
        }
