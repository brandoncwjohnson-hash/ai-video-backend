import uuid
import requests
import traceback
import subprocess
import asyncio
import shutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import edge_tts

app = FastAPI()
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure folders exist
os.makedirs("outputs", exist_ok=True)
os.makedirs("assets", exist_ok=True)

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")


class VideoRequest(BaseModel):
    text: str


# ---------------- PEXELS VIDEO ----------------
def get_pexels_video():
    if not PEXELS_API_KEY:
        return None

    headers = {"Authorization": PEXELS_API_KEY}

    try:
        res = requests.get(
            "https://api.pexels.com/videos/search?query=business%20lifestyle&per_page=5",
            headers=headers,
            timeout=10
        )

        data = res.json()
        videos = data.get("videos", [])

        if not videos:
            return None

        video_files = videos[0].get("video_files", [])
        if not video_files:
            return None

        return video_files[0].get("link")

    except Exception as e:
        print("PEXELS ERROR:", str(e))
        return None


# ---------------- LOCAL FALLBACK ----------------
def get_safe_fallback_video():
    local_path = "assets/fallback.mp4"

    if os.path.exists(local_path):
        return local_path

    raise Exception("Missing fallback video: /assets/fallback.mp4")


# ---------------- DOWNLOAD ----------------
def download_file(url, path):
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()

    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    if os.path.getsize(path) < 10000:
        raise Exception("Downloaded file too small or corrupted")


# ---------------- VALIDATE MP4 ----------------
def is_valid_mp4(path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", path],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


# ---------------- MAIN API ----------------
@app.post("/generate-video")
def generate_video(req: VideoRequest):

    try:
        job_id = str(uuid.uuid4())

        video_path = f"outputs/{job_id}.mp4"
        audio_path = f"outputs/{job_id}.mp3"
        input_video = f"outputs/{job_id}_input.mp4"

        # STEP 1 — GET VIDEO
        video_url = get_pexels_video()

        if not video_url:
            video_url = get_safe_fallback_video()

        # STEP 2 — DOWNLOAD OR COPY
        if video_url.startswith("http"):
            download_file(video_url, input_video)
        else:
            shutil.copy(video_url, input_video)

        # STEP 3 — VALIDATE INPUT VIDEO (CRITICAL FIX)
        if not is_valid_mp4(input_video):
            raise Exception("Input video is not a valid MP4 (corrupt or unsupported file)")

        # STEP 4 — TTS
        async def create_audio():
            communicate = edge_tts.Communicate(req.text, "en-US-AriaNeural")
            await communicate.save(audio_path)

        asyncio.run(create_audio())

        # STEP 5 — FFmpeg render
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_video,
            "-i", audio_path,
            "-vf", "scale=720:1280,format=yuv420p",
            "-c:v", "libx264",
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

        return {
            "status": "success",
            "video_url": f"/outputs/{job_id}.mp4",
            "audio_file": f"/outputs/{job_id}.mp3"
        }

    except Exception as e:
        print("🔥 ERROR:", str(e))
        print(traceback.format_exc())

        return {
            "error": str(e)
        }


# ---------------- VOICES ----------------
@app.get("/api/video/voices")
def get_voices():
    return {
        "voices": [
            {"id": "aria", "label": "Aria"},
            {"id": "guy", "label": "Guy"},
            {"id": "jenny", "label": "Jenny"},
            {"id": "ana", "label": "Ana"},
            {"id": "ryan", "label": "Ryan"}
        ]
    }


# ---------------- HEALTH ----------------
@app.get("/")
def root():
    return {"status": "running"}
