import os
import uuid
import requests
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

# Ensure outputs folder exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Serve outputs publicly
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")


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
        input_video = os.path.join(OUTPUT_DIR, f"{job_id}_input.mp4")

        # ----------------------------
        # FIXED VIDEO SOURCE (STABLE CDN)
        # ----------------------------
        video_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

        # download video safely
        r = requests.get(video_url, stream=True, timeout=30)
        r.raise_for_status()

        with open(input_video, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        # ----------------------------
        # SAFE AUDIO GENERATION
        # ----------------------------
        subprocess.run([
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "5",
            audio_path
        ], check=True)

        # ----------------------------
        # VIDEO RENDER
        # ----------------------------
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_video,
            "-i", audio_path,
            "-vf",
            "scale=720:1280:force_original_aspect_ratio=decrease,"
            "pad=720:1280:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-shortest",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {
                "error": "FFmpeg failed",
                "details": result.stderr
            }

        # ----------------------------
        # RETURN DOWNLOAD LINKS
        # ----------------------------
        return {
            "status": "success",
            "video_url": f"https://vyyo4co8c8r0bkqz7x2xm9sx.178.104.247.146.sslip.io/outputs/{job_id}.mp4",
            "audio_file": f"https://vyyo4co8c8r0bkqz7x2xm9sx.178.104.247.146.sslip.io/outputs/{job_id}.mp3"
        }

    except Exception as e:
        return {
            "error": str(e)
        }
