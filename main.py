import uuid
import os
import asyncio
import requests
import subprocess

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# =========================
# APP SETUP
# =========================

app = FastAPI()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

print("🔥 MVP VIDEO BACKEND STARTED")

# =========================
# CONFIG
# =========================

PEXELS_API_KEY = "PUT_YOUR_PEXELS_API_KEY_HERE"

jobs = {}
queue = asyncio.Queue()

# =========================
# REQUEST MODEL
# =========================

class VideoRequest(BaseModel):
    script: str
    avatar: str | None = None
    voice: str = "en-US-AriaNeural"
    hook_only: bool = True

# =========================
# PEXELS
# =========================

def get_pexels_video(query: str):
    try:
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"
        headers = {"Authorization": PEXELS_API_KEY}

        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        if "videos" in data and len(data["videos"]) > 0:
            video_files = data["videos"][0]["video_files"]
            return video_files[0]["link"]

        return None

    except Exception as e:
        print("PEXELS ERROR:", e)
        return None

# =========================
# TTS
# =========================

async def generate_voice(text, output_path):
    import edge_tts

    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    await communicate.save(output_path)

# =========================
# WORKER (FIXED)
# =========================

async def worker():
    print("🚀 WORKER STARTED")

    while True:
        job_id, req = await queue.get()

        try:
            print(f"🎬 Processing {job_id}")

            jobs[job_id]["status"] = "processing"

            # -------------------------
            # 1. VOICE (FIXED)
            # -------------------------
            audio_path = f"{OUTPUT_DIR}/{job_id}.mp3"
            await generate_voice(req.script, audio_path)

            # -------------------------
            # 2. PEXELS VIDEO
            # -------------------------
            query = " ".join(req.script.split(" ")[:3])
            video_url = get_pexels_video(query)

            if not video_url:
                raise Exception("No Pexels video found")

            video_path = f"{OUTPUT_DIR}/{job_id}.mp4"

            video_data = requests.get(video_url).content
            with open(video_path, "wb") as f:
                f.write(video_data)

            # -------------------------
            # 3. MERGE (FFMPEG)
            # -------------------------
            output_path = f"{OUTPUT_DIR}/{job_id}_final.mp4"

            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]

            subprocess.run(cmd, check=True)

            # -------------------------
            # 4. DONE
            # -------------------------
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["video_url"] = f"/outputs/{job_id}_final.mp4"

            print(f"✅ COMPLETED {job_id}")

        except Exception as e:
            print("❌ JOB FAILED:", e)
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

        queue.task_done()

# =========================
# STARTUP (SAFE)
# =========================

@app.on_event("startup")
async def startup():
    print("🚀 SERVER STARTING")

    try:
        asyncio.create_task(worker())
        print("✅ WORKER STARTED")
    except Exception as e:
        print("❌ WORKER START FAILED:", e)

# =========================
# API
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

@app.get("/api/video/status/{job_id}")
async def status(job_id: str):
    return jobs.get(job_id, {"error": "job not found"})
