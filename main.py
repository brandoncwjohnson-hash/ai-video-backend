from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from gtts import gTTS
import uuid
import os
import subprocess
import urllib.request

app = FastAPI()

# =========================
# FOLDERS
# =========================
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_DIR = os.getcwd()
BACKGROUND_IMAGE = os.path.join(BASE_DIR, "background.jpg")
BACKGROUND_URL = "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"


# =========================
# REQUEST MODEL
# =========================
class VideoRequest(BaseModel):
    text: str


# =========================
# STATIC FILE ACCESS
# =========================
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def home():
    return {"status": "running"}


# =========================
# DOWNLOAD BACKGROUND IF MISSING
# =========================
def ensure_background():
    if not os.path.exists(BACKGROUND_IMAGE):
        urllib.request.urlretrieve(BACKGROUND_URL, BACKGROUND_IMAGE)


# =========================
# MAIN ENDPOINT
# =========================
@app.post("/generate-video")
def generate_video(request: VideoRequest):
    try:
        ensure_background()

        file_id = str(uuid.uuid4())

        audio_path = f"{OUTPUT_DIR}/{file_id}.mp3"
        video_path = f"{OUTPUT_DIR}/{file_id}.mp4"
        scaled_image = f"{OUTPUT_DIR}/{file_id}_scaled.jpg"

        # -------------------------
        # 1. TEXT → SPEECH
        # -------------------------
        tts = gTTS(text=request.text, lang="en")
        tts.save(audio_path)

        # -------------------------
        # 2. SCALE IMAGE (CRITICAL FOR VPS STABILITY)
        # -------------------------
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", BACKGROUND_IMAGE,
            "-vf", "scale=1280:720",
            scaled_image
        ], capture_output=True)

        # -------------------------
        # 3. IMAGE + AUDIO → VIDEO
        # -------------------------
        command = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", scaled_image,
            "-i", audio_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            video_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        # -------------------------
        # 4. RETURN DOWNLOADABLE URL
        # -------------------------
        return {
            "ffmpeg_return_code": result.returncode,
            "video_url": f"http://vyyo4co8c8r0bkqz7x2xm9sx.178.104.247.146.sslip.io/{video_path}",
            "audio_file": audio_path
        }

    except Exception as e:
        return {"error": str(e)}
