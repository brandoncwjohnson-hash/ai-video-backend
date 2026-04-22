import uuid
import asyncio
import os
import subprocess
import requests

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

print("🔥 AI VIDEO BACKEND RUNNING")

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
    hook_only: bool = False

# =========================
# SCENE HANDLING (GENERIC - IMPORTANT)
# Frontend controls storytelling
# Backend only ensures fallback structure
# =========================

def split_into_scenes(script: str):
    """
    Generic fallback scene splitter.
    DO NOT add storytelling logic here.
    Frontend should provide structured scenes in future.
    """

    base = script.strip()

    return [
        f"{base} opening visual context",
        f"{base} main explanation visual",
        f"{base} supporting visual detail",
        f"{base} closing visual context"
    ]

# =========================
# PEXELS QUERY EXTRACTION (SAFE + GENERIC)
# =========================

def get_search_query(scene: str):
    scene = scene.lower()

    keywords = [
        "people", "office", "technology", "laptop",
        "city", "money", "business", "work",
        "computer", "nature", "travel", "team",
        "meeting", "desk", "phone", "data",
        "analytics", "success"
    ]

    for k in keywords:
        if k in scene:
            return k

    return "technology"

# =========================
# PEXELS VIDEO FETCH
# =========================

def get_pexels_video(query: str):
    try:
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=5"
        headers = {"Authorization": PEXELS_API_KEY}

        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        videos = data.get("videos", [])

        for video in videos:
            files = video.get("video_files", [])
            if files:
                return files[0]["link"]

        return None

    except Exception as e:
        print("PEXELS ERROR:", e)
        return None

# =========================
# VOICE GENERATION
# =========================

async def generate_voice(text, output_path):
    import edge_tts

    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    await communicate.save(output_path)

# =========================
# WORKER
# =========================

async def worker():
    print("🚀 WORKER STARTED")

    while True:
        job_id, req = await queue.get()

        try:
            jobs[job_id]["status"] = "processing"

            # -------------------------
            # AUDIO
            # -------------------------
            audio_path = f"{OUTPUT_DIR}/{job_id}.mp3"
            await generate_voice(req.script, audio_path)

            # -------------------------
            # SCENES
            # -------------------------
            scenes = split_into_scenes(req.script)

            video_clips = []

            for i, scene in enumerate(scenes):
                query = get_search_query(scene)

                print("🎬 Scene:", scene)
                print("🔎 Query:", query)

                video_url = get_pexels_video(query)

                if video_url:
                    clip_path = f"{OUTPUT_DIR}/{job_id}_{i}.mp4"

                    video_data = requests.get(video_url).content

                    with open(clip_path, "wb") as f:
                        f.write(video_data)

                    video_clips.append(clip_path)

            # -------------------------
            # SAFETY CHECK
            # -------------------------
            if len(video_clips) == 0:
                raise Exception("No valid Pexels clips found")

            # -------------------------
            # CONCAT LIST FILE
            # -------------------------
            list_file = f"{OUTPUT_DIR}/{job_id}_list.txt"

            with open(list_file, "w") as f:
                for clip in video_clips:
                    if os.path.exists(clip) and os.path.getsize(clip) > 1000:
                        f.write(f"file '{os.path.abspath(clip)}'\n")

            if os.path.getsize(list_file) == 0:
                raise Exception("No valid clips to concatenate")

            # -------------------------
            # FINAL OUTPUT
            # -------------------------
            output_path = f"{OUTPUT_DIR}/{job_id}_final.mp4"

            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]

            subprocess.run(cmd, check=True)

            jobs[job_id]["status"] = "complete"
            jobs[job_id]["video_url"] = f"/outputs/{job_id}_final.mp4"

            print("✅ COMPLETED:", job_id)

        except Exception as e:
            print("❌ ERROR:", e)
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

        queue.task_done()

# =========================
# STARTUP
# =========================

@app.on_event("startup")
async def startup():
    asyncio.create_task(worker())
    print("✅ SERVER READY")

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
