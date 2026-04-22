import uuid
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

# 👇 IMPORT YOUR EXISTING FUNCTIONS
# KEEP YOUR ORIGINAL FUNCTIONS BELOW THIS LINE
# (we will call generate_video)

app = FastAPI()

# =========================
# REQUEST MODEL
# =========================

class VideoRequest(BaseModel):
    idea: str
    avatar: str | None = None
    voice: str
    hook_only: bool = False

# =========================
# JOB STORAGE
# =========================

jobs: Dict[str, Dict] = {}
queue = asyncio.Queue()

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

            # CALL YOUR EXISTING FUNCTION
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
# KEEP YOUR ORIGINAL CODE BELOW
# =========================
