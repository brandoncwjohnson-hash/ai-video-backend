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
    hook_only: bool = True

# =========================
# SCENES (IMPROVED)
# =========================

def split_into_scenes(script: str):
    base = script.lower()

    return [
        f"{base} office stress frustration laptop work problem",
        f"{base} ai automation software dashboard analytics screen",
        f"{base} online income passive money business success laptop",
        f"{base} digital nomad freedom travel beach laptop sunset"
    ]

# =========================
# PEXELS QUERY (FIXED)
# =========================

def get_search_query(scene: str):
    scene = scene.lower()

    keywords = [
        "ai", "technology", "laptop", "office",
        "money", "business", "success", "work",
        "computer", "finance", "startup",
        "remote", "travel", "freedom", "coding"
    ]

    for k in keywords:
        if k in scene:
            return k

    return "technology"

# =========================
# PEXELS FETCH
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
# VOICE
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
            print(f"🎬 Processing {job_id}")

            jobs[job_id]["status"] = "processing"

            # -------------------------
            # AUDIO
            # -------------------------
            audio_path = f"{OUTPUT_DIR}/{job_id}.mp3"
            await generate_voice(req.script, audio_path)

            # -------------------------
            # SCENES → CLIPS
            # -------------------------
            scenes = split_into_scenes(req.script)

            video_clips = []

            for i, scene in enumerate(scenes):
                print("🎬 Scene:", scene)

                query = get_search_query(scene)
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
            # CONCAT SAFELY
            # -------------------------
            list_file = f"{OUTPUT_DIR}/{job_id}_list.txt"

            with open(list_file, "w") as f:
                for clip in video_clips:
                    if os.path.exists(clip) and os.path.getsize(clip) > 1000:
                        f.write(f"file '{os.path.abspath(clip)}'\n")

            if os.path.getsize(list_file) == 0:
                raise Exception("No valid clips to concatenate")

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

            # -------------------------
            # DONE
            # -------------------------
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["video_url"] = f"/outputs/{job_id}_final.mp4"

            print(f"✅ DONE {job_id}")

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
    print("🚀 SERVER STARTING")
    asyncio.create_task(worker())
    print("✅ WORKER READY")

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
