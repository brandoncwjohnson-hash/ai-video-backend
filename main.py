from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import uuid
import os
import requests
import subprocess

app = FastAPI()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# -----------------------------
# INPUT MODELS
# -----------------------------

class Scene(BaseModel):
    setting: str
    action: str
    object: str = ""
    duration: int

class VideoRequest(BaseModel):
    script: str
    scenes: list[Scene]

# -----------------------------
# SIMPLE IN-MEMORY CACHE (MVP)
# Replace with Redis later
# -----------------------------

CACHE = {}

# -----------------------------
# DIRECTOR ENGINE
# -----------------------------

def build_query(scene: Scene):
    parts = [scene.setting, scene.object, scene.action]
    return " ".join([p for p in parts if p]).strip()

# -----------------------------
# PEXELS FETCH
# -----------------------------

def fetch_pexels_video(query):
    if query in CACHE:
        return CACHE[query]

    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    res = requests.get(url, headers=headers)
    data = res.json()

    clips = []

    for video in data.get("videos", []):
        files = video.get("video_files", [])
        if files:
            clips.append(files[0]["link"])

    CACHE[query] = clips
    return clips

# -----------------------------
# DOWNLOAD VIDEO
# -----------------------------

def download_clip(url, filename):
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)

# -----------------------------
# RENDER VIDEO (SIMPLE MVP)
# -----------------------------

def render_video(scene_clips):
    os.makedirs("output", exist_ok=True)

    inputs = []

    for i, clip in enumerate(scene_clips):
        filename = f"output/clip_{i}.mp4"
        download_clip(clip, filename)
        inputs.append(filename)

    list_file = "output/list.txt"

    with open(list_file, "w") as f:
        for inp in inputs:
            f.write(f"file '{inp}'\n")

    output_path = "output/final.mp4"

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ])

    return output_path

# -----------------------------
# MAIN ENDPOINT
# -----------------------------

@app.post("/generate-video")
def generate_video(req: VideoRequest):

    all_clips = []

    for scene in req.scenes:

        query = build_query(scene)
        clips = fetch_pexels_video(query)

        if clips:
            all_clips.append(clips[0])  # pick best simple version

    output = render_video(all_clips)

    return {
        "status": "success",
        "video_path": output
    }
