import os
import uuid
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure outputs folder exists
os.makedirs("outputs", exist_ok=True)

# Serve outputs publicly
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

class VideoRequest(BaseModel):
    text: str


def get_pexels_video():
    if not PEXELS_API_KEY:
        return None

    headers = {"Authorization": PEXELS_API_KEY}

    try:
        res = requests.get(
            "https://api.pexels.com/videos/search?query=business%20lifestyle&per_page=5",
            headers=headers,
            timeout=10
        )

        data = res.json()
        videos = data.get("videos", [])

        if not videos:
            return None

        video_files = videos[0].get("video_files", [])

        if not video_files:
            return None

        return video_files[0].get("link")

    except Exception as e:
        print("Pexels error:", str(e))
        return None


def download_file(url, path):
    r = requests.get(url, stream=True)
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)


@app.post("/generate-video")
def generate_video(req: VideoRequest):

    job_id = str(uuid.uuid4())

    video_path = f"outputs/{job_id}.mp4"
    audio_path = f"outputs/{job_id}.mp3"
    input_video = f"outputs/{job_id}_input.mp4"

    # Get Pexels video (fallback included)
    video_url = get_pexels_video()

    if not video_url:
        video_url = "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"

    download_file(video_url, input_video)

    # TTS
    try:
        import edge_tts
        import asyncio

        async def create_audio():
            communicate = edge_tts.Communicate(req.text, "en-US-AriaNeural")
            await communicate.save(audio_path)

        asyncio.run(create_audio())

    except Exception as e:
        print("TTS error:", str(e))
        return {"error": "TTS failed"}

    # FFmpeg render
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_video,
            "-i", audio_path,
            "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {
                "error": "FFmpeg failed",
                "details": result.stderr
            }

    except Exception as e:
        return {"error": str(e)}

    # FINAL OUTPUT (FULL PUBLIC URL)
    return {
        "ffmpeg_return_code": 0,
        "video_url": f"https://vyyo4co8c8r0bkqz7x2xm9sx.178.104.247.146.sslip.io/outputs/{job_id}.mp4",
        "audio_file": f"https://vyyo4co8c8r0bkqz7x2xm9sx.178.104.247.146.sslip.io/outputs/{job_id}.mp3",
        "status": "success"
    }
