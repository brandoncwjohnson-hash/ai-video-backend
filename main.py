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
        f"HOOK: attention grabbing opening of {base}",
        f"MAIN: detailed working scene of {base}",
        f"DETAIL: close up moment of {base}",
        f"END: cinematic closing of {base}"
    ]

# =========================
# STABLE PEXELS QUERY LAYER (IMPORTANT FIX)
# =========================

def get_search_query(scene: str):
    scene = scene.lower()

    if "developer" in scene or "coding" in scene or "programmer" in scene:
        return "programmer coding laptop"

    if "freelancer" in scene:
        return "freelancer working laptop"

    if "designer" in scene:
        return "designer working office"

    if "student" in scene or "learning" in scene:
        return "student studying laptop"

    if "apartment" in scene:
        return "modern apartment"

    if "office" in scene:
        return "office workspace"

    if "night" in scene:
        return "city night lights"

    if "laptop" in scene:
        return "laptop typing close up"

    if "screens" in scene or "monitors" in scene:
        return "computer screens office"

    if "ai" in scene:
        return "technology data"

    if "startup" in scene or "business" in scene:
        return "startup office meeting"

    return "technology office"

# =========================
# PEXELS FETCH
# =========================

def get_pexels_video(query: str):
    try:
        headers = {"Authorization": PEXELS_API_KEY}

        fallback_queries = [
            query,
            "office",
            "laptop",
            "technology",
            "people",
            "city"
        ]

        for q in fallback_queries:
            url = f"https://api.pexels.com/videos/search?query={q}&per_page=20"

            res = requests.get(url, headers=headers, timeout=10)
            data = res.json()

            videos = data.get("videos", [])

            for video in videos:
                files = video.get("video_files", [])

                mp4_files = [
                    f for f in files
                    if f.get("file_type") == "video/mp4" and f.get("link")
                ]

                if mp4_files:
                    best = sorted(mp4_files, key=lambda x: x.get("width", 0), reverse=True)[0]
                    return best["link"]

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

            # AUDIO
            audio_path = f"{OUTPUT_DIR}/{job_id}.mp3"
            await generate_voice(req.script, audio_path)

            # SCENES
            scenes = split_into_scenes(req.script)

            video_clips = []

            for i, scene in enumerate(scenes):
                query = get_search_query(scene)

                print("Scene:", scene)
                print("Query:", query)

                video_url = get_pexels_video(query)

                if video_url:
                    clip_path = f"{OUTPUT_DIR}/{job_id}_{i}.mp4"

                    video_data = requests.get(video_url).content

                    with open(clip_path, "wb") as f:
                        f.write(video_data)

                    video_clips.append(clip_path)

            if len(video_clips) == 0:
                raise Exception("No valid Pexels clips found")

            # CONCAT LIST
            list_file = f"{OUTPUT_DIR}/{job_id}_list.txt"

            with open(list_file, "w") as f:
                for clip in video_clips:
                    if os.path.exists(clip):
                        f.write(f"file '{os.path.abspath(clip)}'\n")

            # FINAL VIDEO
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
