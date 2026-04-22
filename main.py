import uuid
import os
import asyncio
import subprocess

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# =========================
# APP INIT
# =========================

app = FastAPI()

# =========================
# DIRECTORIES
# =========================

OUTPUT_DIR = "outputs"
ASSETS_DIR = "assets"
FALLBACK_VIDEO = os.path.join(ASSETS_DIR, "fallback.mp4")

os.makedirs(OUTPUT_DIR, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

# =========================
# REQUEST MODEL
# =========================

class VideoRequest(BaseModel):
    script: str
    avatar: str = "male_nomad"
    voice: str = "marin"
    hook_only: bool = True

# =========================
# IN-MEMORY QUEUE SYSTEM
# =========================

jobs = {}
queue = asyncio.Queue()

# =========================
# VIDEO GENERATION (MVP)
# =========================

async def generate_video(job_id: str, req: VideoRequest):
    try:
        jobs[job_id]["status"] = "processing"

        output_file = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")

        # MVP: copy fallback video as generated output
        if os.path.exists(FALLBACK_VIDEO):
            subprocess.run(["cp", FALLBACK_VIDEO, output_file])
        else:
            # create empty placeholder file if fallback missing
            with open(output_file, "wb") as f:
                f.write(b"")

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["video_url"] = f"/outputs/{job_id}.mp4"

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# =========================
# WORKER LOOP
# =========================

async def worker():
    while True:
        job_id, req = await queue.get()
        await generate_video(job_id, req)
        queue.task_done()

@app.on_event("startup")
async def startup():
    asyncio.create_task(worker())

# =========================
# ROUTES
# =========================

@app.get("/")
def root():
    return {"status": "running"}

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

@app.get("/api/video/status/{job_id}")
async def get_status(job_id: str):
    return jobs.get(job_id, {"error": "job not found"})
