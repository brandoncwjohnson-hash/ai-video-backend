import uuid
import asyncio
import os
import subprocess
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

app = FastAPI()
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# =========================
# CONFIG
# =========================

OUTPUT_DIR = "outputs"
ASSETS_DIR = "assets"
FALLBACK_VIDEO = os.path.join(ASSETS_DIR, "fallback.mp4")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# REQUEST MODEL
# =========================

class VideoRequest(BaseModel):
    idea: str
    avatar: str | None = None
    voice: str
    hook_only: bool = False

# =========================
# QUEUE + JOB STORAGE
# =========================

jobs: Dict[str, Dict] = {}
queue = asyncio.Queue()

# =========================
# UTIL FUNCTIONS
# =========================

def is_valid_mp4(path):
    return os.path.exists(path) and os.path.getsize(path) > 1000

def generate_video(req: VideoRequest):
    job_id = str(uuid.uuid4())

    video_output = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
    audio_output = os.path.join(OUTPUT_DIR, f"{job_id}.mp3")

    # 🔊 Generate simple silent audio (placeholder)
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", "5",
        "-q:a", "9",
        "-acodec", "libmp3lame",
        audio_output,
        "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not is_valid_mp4(FALLBACK_VIDEO):
        raise Exception("Fallback video missing or invalid")

    # 🎬 Combine video + audio
    subprocess.run([
        "ffmpeg",
        "-i", FALLBACK_VIDEO,
        "-i", audio_output,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        video_output,
        "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not is_valid_mp4(video_output):
        raise Exception("FFmpeg failed to produce valid video")

    return {
        "video_url": f"/outputs/{os.path.basename(video_output)}",
        "audio_file": f"/outputs/{os.path.basename(audio_output)}"
    }

# =========================
# WEBHOOK START
# =========================

@app.post("/api/video/webhook/start")
async def start_job(req: VideoRequest):
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queuing",
        "video_url": None,
        "error": None
    }

    await queue.put((job_id, req))

    return {"job_id": job_id}

# =========================
# STATUS ENDPOINT
# =========================

@app.get("/api/video/status/{job_id}")
async def get_status(job_id: str):
    return jobs.get(job_id, {"error": "job not found"})

# =========================
# WORKER
# =========================

async def worker():
    while True:
        job_id, req = await queue.get()

        try:
            jobs[job_id]["status"] = "generating_script"

            result = generate_video(req)

            jobs[job_id]["status"] = "finalizing"
            jobs[job_id]["video_url"] = result.get("video_url")

            jobs[job_id]["status"] = "complete"

        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

        queue.task_done()

# =========================
# START WORKER
# =========================

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(worker())

# =========================
# BASIC ROUTES
# =========================

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/api/video/voices")
def get_voices():
    return {
        "voices": ["aria", "marin", "verse", "alloy", "echo"]
    }
