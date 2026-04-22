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

# =========================
# SCENE SPLITTER
# =========================

def split_into_scenes(script: str):
    script = script.strip()

    return [
        f"HOOK: {script}",
        f"MIDDLE: {script}",
        f"DETAIL: {script}",
        f"ENDING: {script}"
    ]

# =========================
# PEXELS (DEBUG + ROBUST)
# =========================

def get_pexels_clips(query: str, limit: int = 2):
    try:
        headers = {"Authorization": PEXELS_API_KEY}

        url = f"https://api.pexels.com/videos/search?query={query}&per_page=20"

        res = requests.get(url, headers=headers, timeout=10)

        print("\n====================")
        print("PEXELS QUERY:", query)
        print("STATUS:", res.status_code)

        data = res.json()

        videos = data.get("videos", [])

        print("VIDEOS FOUND:", len(videos))

        candidates = []

        for video in videos:
            files = video.get("video_files", [])

            for f in files:

                link = f.get("link")
                if not link:
                    continue

                width = f.get("width") or 0
                height = f.get("height") or 0
                duration = video.get("duration") or 0

                print("FILE:", link, width, height, duration)

                if width == 0 or height == 0:
                    continue

                score = 0

                # resolution scoring
                if width >= 1920:
                    score += 500
                elif width >= 1280:
                    score += 300
                else:
                    score += 100

                # cinematic preference
                if width > height:
                    score += 200

                # duration sweet spot
                if 4 <= duration <= 20:
                    score += 200

                candidates.append({
                    "link": link,
                    "score": score
                })

        print("CANDIDATES FOUND:", len(candidates))

        if not candidates:
            print("❌ NO CANDIDATES FOR:", query)
            return []

        candidates.sort(key=lambda x: x["score"], reverse=True)

        return [c["link"] for c in candidates[:limit]]

    except Exception as e:
        print("PEXELS ERROR:", e)
        return []

# =========================
# VOICE (PLACEHOLDER)
# =========================

async def generate_voice(text, output_path):
    with open(output_path, "wb") as f:
        f.write(b"")

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

                query = scene.replace("HOOK:", "").replace("MIDDLE:", "").replace("DETAIL:", "").replace("ENDING:", "").strip()

                print("\nSCENE:", scene)
                print("QUERY:", query)

                video_urls = get_pexels_clips(query, limit=2)

                if not video_urls:
                    print("⚠️ NO CLIPS FOR SCENE:", i)
                    continue

                clip_path = f"{OUTPUT_DIR}/{job_id}_{i}.mp4"

                video_data = requests.get(video_urls[0]).content

                with open(clip_path, "wb") as f:
                    f.write(video_data)

                video_clips.append(clip_path)

            if not video_clips:
                raise Exception("No valid Pexels clips found")

            list_file = f"{OUTPUT_DIR}/{job_id}_list.txt"

            with open(list_file, "w") as f:
                for clip in video_clips:
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

            print("✅ DONE:", job_id)

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
