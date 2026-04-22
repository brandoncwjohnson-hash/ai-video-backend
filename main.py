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
# SCENE SPLITTER
# =========================

def split_into_scenes(script: str):
    base = script.strip()

    return [
        f"HOOK: {base}",
        f"MIDDLE: {base}",
        f"DETAIL: {base}",
        f"ENDING: {base}"
    ]

# =========================
# FIXED PEXELS SAFE QUERIES
# =========================

def get_search_query(scene: str):
    scene = scene.lower()

    # 🔥 PEXELS-OPTIMIZED QUERIES (REAL DATASET MATCHES)

    if "developer" in scene or "coding" in scene or "programmer" in scene:
        return "man coding laptop"

    if "freelancer" in scene:
        return "man working laptop"

    if "designer" in scene:
        return "creative office desk"

    if "apartment" in scene:
        return "modern apartment interior"

    if "night" in scene:
        return "city night traffic"

    if "city" in scene:
        return "city timelapse night"

    if "laptop" in scene:
        return "typing on laptop close up"

    if "screens" in scene or "monitors" in scene:
        return "multiple monitors desk"

    if "office" in scene:
        return "office workspace"

    if "startup" in scene or "business" in scene:
        return "startup meeting office"

    if "learning" in scene:
        return "student studying desk"

    if "ai" in scene:
        return "technology abstract data"

    # 🚨 GUARANTEE FALLBACK (NEVER FAILS)
    return "technology office"

# =========================
# MULTI-CLIP FETCH (SAFE)
# =========================

def get_pexels_clips(query: str, limit: int = 2):
    try:
        headers = {"Authorization": PEXELS_API_KEY}

        url = f"https://api.pexels.com/videos/search?query={query}&per_page=20"

        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        videos = data.get("videos", [])

        candidates = []

        for video in videos:
            files = video.get("video_files", [])

            for f in files:
                if f.get("file_type") != "video/mp4":
                    continue

                link = f.get("link")
                width = f.get("width", 0)
                height = f.get("height", 0)
                duration = video.get("duration", 0)

                if not link:
                    continue

                score = width

                if width > height:
                    score += 500

                if 5 <= duration <= 20:
                    score += 300

                candidates.append({
                    "link": link,
                    "score": score
                })

        if not candidates:
            return []

        candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

        return [c["link"] for c in candidates[:limit]]

    except Exception as e:
        print("PEXELS ERROR:", e)
        return []

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

            audio_path = f"{OUTPUT_DIR}/{job_id}.mp3"
            await generate_voice(req.script, audio_path)

            scenes = split_into_scenes(req.script)

            video_clips = []

            for i, scene in enumerate(scenes):
                query = get_search_query(scene)

                print("Scene:", scene)
                print("Query:", query)

                video_urls = get_pexels_clips(query, limit=2)

                scene_clips = []

                for j, video_url in enumerate(video_urls):
                    clip_path = f"{OUTPUT_DIR}/{job_id}_{i}_{j}.mp4"

                    video_data = requests.get(video_url).content

                    with open(clip_path, "wb") as f:
                        f.write(video_data)

                    scene_clips.append(clip_path)

                if len(scene_clips) == 0:
                    continue

                video_clips.append(scene_clips[0])

            if len(video_clips) == 0:
                raise Exception("No valid Pexels clips found")

            list_file = f"{OUTPUT_DIR}/{job_id}_list.txt"

            with open(list_file, "w") as f:
                for clip in video_clips:
                    if os.path.exists(clip):
                        f.write(f"file '{os.path.abspath(clip)}'\n")

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

            print("DONE:", job_id)

        except Exception as e:
            print("ERROR:", e)
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

        queue.task_done()

# =========================
# STARTUP
# =========================

@app.on_event("startup")
async def startup():
    asyncio.create_task(worker())
    print("SERVER READY")

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
