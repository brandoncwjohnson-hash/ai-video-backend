import os
import uuid
import asyncio
import subprocess
import requests

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import edge_tts

app = FastAPI()

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

# Serve outputs
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Request model
class VideoRequest(BaseModel):
    idea: str
    avatar: str = "male_nomad"
    voice: str = "en-US-GuyNeural"
    hook_only: bool = True

# Queue
jobs = {}
queue = asyncio.Queue()

# ===== SIMPLE SCRIPT GENERATOR =====
def generate_script(idea: str):
    return f"Want to know how to {idea}? This could change your life."

# ===== AUDIO GENERATION =====
async def create_audio(text, output_file, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

# ===== DOWNLOAD SAMPLE VIDEO (fallback) =====
def get_background_video(path):
    url = "https://samplelib.com/lib/preview/mp4/sample-5s.mp4"
    r = requests.get(url)
    with open(path, "wb") as f:
        f.write(r.content)

# ===== VIDEO BUILDER =====
async def generate_video(job_id, req: VideoRequest):
    try:
        jobs[job_id]["status"] = "generating_script"

        script = generate_script(req.idea)

        jobs[job_id]["status"] = "generating_audio"

        audio_path = f"outputs/{job_id}.mp3"
        await create_audio(script, audio_path, req.voice)

        jobs[job_id]["status"] = "fetching_video"

        video_input = f"outputs/{job_id}_bg.mp4"
        get_background_video(video_input)

        jobs[job_id]["status"] = "rendering"

        final_video = f"outputs/{job_id}.mp4"

        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", video_input,
            "-i", audio_path,
            "-shortest",
            "-c:v", "copy",
            "-c:a", "aac",
            final_video
        ])

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["video_url"] = f"/outputs/{job_id}.mp4"

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# Worker
async def worker():
    while True:
        job_id, req = await queue.get()
        await generate_video(job_id, req)
        queue.task_done()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(worker())

# Routes
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
