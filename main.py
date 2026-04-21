import os
import uuid
import random
from fastapi import FastAPI
from pydantic import BaseModel
from gtts import gTTS
import requests
import subprocess

app = FastAPI()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class VideoRequest(BaseModel):
    text: str


# ----------------------------
# 1. AUDIO GENERATION
# ----------------------------
@app.post("/generate-audio")
def generate_audio(request: VideoRequest):
    file_id = str(uuid.uuid4())
    file_path = f"{OUTPUT_DIR}/{file_id}.mp3"

    tts = gTTS(text=request.text, lang="en")
    tts.save(file_path)

    return {"audio_file": file_path}


# ----------------------------
# 2. PEXELS VIDEO FETCH (FIXED)
# ----------------------------
def get_pexels_video(query_list):
    headers = {"Authorization": PEXELS_API_KEY}

    for query in query_list:
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=5"
        res = requests.get(url, headers=headers).json()

        videos = res.get("videos", [])

        if videos:
            video_files = videos[0]["video_files"]
            if video_files:
                return video_files[0]["link"]

    return None


# ----------------------------
# 3. VIDEO GENERATION
# ----------------------------
@app.post("/generate-video")
def generate_video(request: VideoRequest):

    file_id = str(uuid.uuid4())

    audio_path = f"{OUTPUT_DIR}/{file_id}.mp3"
    video_path = f"{OUTPUT_DIR}/{file_id}.mp4"

    # create audio
    tts = gTTS(text=request.text, lang="en")
    tts.save(audio_path)

    # map script → visual keywords
    text = request.text.lower()

    queries = []

    if "work" in text:
        queries.append("office")
    if "income" in text:
        queries.append("laptop")
    if "travel" in text:
        queries.append("travel")
    if "world" in text:
        queries.append("city")
    if "escape" in text:
        queries.append("lifestyle")

    # fallback if nothing matched
    if not queries:
        queries = ["travel", "city", "laptop", "office"]

    video_url = get_pexels_video(queries)

    # FINAL fallback (prevents failure)
    if not video_url:
        video_url = "background.jpg"

    # build video
    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", video_url if video_url == "background.jpg" else "background.jpg",
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return {
            "error": "FFmpeg failed",
            "details": result.stderr
        }

    return {
        "video_file": video_path,
        "audio_file": audio_path,
        "video_url": f"/{video_path}"
    }
