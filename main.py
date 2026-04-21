import os
import uuid
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ensure outputs folder exists BEFORE mount (prevents crash)
os.makedirs("outputs", exist_ok=True)

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


# ---------------- FIXED DOWNLOAD (CRITICAL) ----------------
def download_file(url, path):
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()

        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        # prevent ffmpeg crashes
        if os.path.getsize(path) < 10000:
            raise Exception("Downloaded file too small or corrupted")

    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")


@app.post("/generate-video")
def generate_video(req: VideoRequest):

    job_id = str(uuid.uuid4())

    video_path = f"outputs/{job_id}.mp4"
    audio_path = f"outputs/{job_id}.mp3"
    input_video = f"outputs/{job_id}_input.mp4"

    # STEP 1 — video source
    video_url = get_pexels_video()

    # fallback (stable source)
    if not video_url:
        video_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4"

    # STEP 2 — download video safely
    download_file(video_url, input_video)

    # STEP 3 — generate voice (Edge TTS)
    try:
        import edge_tts
        import asyncio

        async def create_audio():
            communicate = edge_tts.Communicate(req.text, "en-US-AriaNeural")
            await communicate.save(audio_path)

        asyncio.run(create_audio())

    except Exception as e:
        return {"error": str(e)}

    # STEP 4 — render video
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_video,
        "-i", audio_path,
        "-vf", "scale=720:1280,format=yuv420p",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return {
            "error": "FFmpeg failed",
            "details": result.stderr
        }

    # STEP 5 — return output
    return {
        "status": "success",
        "video_url": f"/outputs/{job_id}.mp4",
        "audio_file": f"/outputs/{job_id}.mp3"
    }


# ---------------- VOICES ENDPOINT ----------------
@app.get("/api/video/voices")
def get_voices():
    return {
        "voices": [
            {"id": "aria", "label": "Aria"},
            {"id": "guy", "label": "Guy"},
            {"id": "jenny", "label": "Jenny"},
            {"id": "ana", "label": "Ana"},
            {"id": "ryan", "label": "Ryan"}
        ]
    }
