import os
import uuid
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure outputs folder exists
if not os.path.exists("outputs"):
    os.makedirs("outputs")

# Serve video files
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# ===== REQUEST MODEL =====
class VideoRequest(BaseModel):
    idea: str
    avatar: str = "male_nomad"
    voice: str = "marin"
    hook_only: bool = True

# ===== QUEUE SYSTEM =====
jobs = {}
queue = asyncio.Queue()

# ===== VIDEO GENERATION (SAFE VERSION) =====
async def generate_video(job_id, req: VideoRequest):
    try:
        jobs[job_id]["status"] = "rendering"

        output_path = f"outputs/{job_id}.mp4"

        # Create a dummy video file (temporary)
        with open(output_path, "wb") as f:
            f.write(b"FAKE VIDEO CONTENT")

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["video_url"] = f"/outputs/{job_id}.mp4"

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# ===== WORKER =====
async def worker():
    while True:
        job_id, req = await queue.get()
        await generate_video(job_id, req)
        queue.task_done()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(worker())

# ===== ROUTES =====

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/api/video/webhook/start")
async def start_video(req: VideoRequest):
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "video_url": None,
        "error": None
    }

    await queue.put((job_id, req))

    return {"job_id": job_id}

@app.get("/api/video/status/{job_id}")
async def get_status(job_id: str):
    return jobs.get(job_id, {"error": "job not found"})
