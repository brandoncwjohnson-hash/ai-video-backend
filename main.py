import uuid
import os
import asyncio
import subprocess
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Optional

# =========================
# APP INIT
# =========================

app = FastAPI()

OUTPUT_DIR = "outputs"
ASSETS_DIR = "assets"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

# =========================
# AVATARS
# =========================

AVATAR_IMAGES = {
    "brandon_clone": "assets/avatars/brandon.png",
    "male_nomad": "assets/avatars/male_nomad.png",
    "female_nomad": "assets/avatars/female_nomad.png",
    "generic_male": "assets/avatars/generic_male.png",
    "generic_female": "assets/avatars/generic_female.png"
}

# =========================
# JOB STORAGE (IN MEMORY)
# =========================

jobs: Dict[str, dict] = {}

queue = asyncio.Queue()

# =========================
# REQUEST MODEL
# =========================

class VideoRequest(BaseModel):
    script: str
    avatar: str = "male_nomad"
    voice: str = "marin"
    hook_only: bool = True

# =========================
# TTS (TEMP SIMPLE VERSION)
# =========================

async def generate_audio(text: str, output_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(output_path)

# =========================
# SADTALKER WRAPPER
# =========================

async def run_sadtalker(image_path, audio_path, output_path):
    cmd = [
        "python",
        "SadTalker/inference.py",
        "--source_image", image_path,
        "--driven_audio", audio_path,
        "--result_dir", OUTPUT_DIR
    ]

    subprocess.run(cmd, check=True)

# =========================
# WORKER
# =========================

async def worker():
    while True:
        job_id, req = await queue.get()

        try:
            jobs[job_id]["status"] = "processing"

            avatar_path = AVATAR_IMAGES.get(req.avatar, AVATAR_IMAGES["male_nomad"])

            audio_path = f"{OUTPUT_DIR}/{job_id}.mp3"
            video_path = f"{OUTPUT_DIR}/{job_id}.mp4"

            # 1. generate voice
            await generate_audio(req.script, audio_path)

            # 2. generate talking avatar (SadTalker)
            await run_sadtalker(avatar_path, audio_path, video_path)

            jobs[job_id]["status"] = "complete"
            jobs[job_id]["video_url"] = f"/outputs/{job_id}.mp4"

        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

        queue.task_done()

# =========================
# START WORKER ON BOOT
# =========================

@app.on_event("startup")
async def startup():
    asyncio.create_task(worker())

# =========================
# WEBHOOK START
# =========================

@app.post("/api/video/webhook/start")
async def start_job(req: VideoRequest):
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "video_url": None,
        "error": None
    }

    await queue.put((job_id, req))

    return {
        "job_id": job_id,
        "status": "queued"
    }

# =========================
# STATUS ENDPOINT
# =========================

@app.get("/api/video/status/{job_id}")
async def get_status(job_id: str):
    return jobs.get(job_id, {"error": "job not found"})
