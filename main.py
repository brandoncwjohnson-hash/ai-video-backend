import os
import uuid
import requests
import subprocess

from fastapi import FastAPI
from pydantic import BaseModel
from gtts import gTTS

app = FastAPI()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ⚠️ PUT YOUR PEXELS API KEY HERE
PEXELS_API_KEY = "PUT_YOUR_PEXELS_API_KEY_HERE"


class VideoRequest(BaseModel):
    text: str


# ----------------------------
# SAFE PEXELS VIDEO FETCHER
# ----------------------------
def get_pexels_video(query: str):
    try:
        headers = {"Authorization": PEXELS_API_KEY}

        url = f"https://api.pexels.com/videos/search?query={query}&per_page=5"
        res = requests.get(url, headers=headers).json()

        videos = res.get("videos", [])

        # fallback if empty
        if not videos:
            fallback = requests.get(
                "https://api.pexels.com/videos/search?query=business&per_page=5",
                headers=headers
            ).json()
            videos = fallback.get("videos", [])

        if not videos:
            raise Exception("No videos returned from Pexels")

        video_url = videos[0]["video_files"][0]["link"]

        file_id = str(uuid.uuid4())
        video_path = f"{OUTPUT_DIR}/{file_id}.mp4"

        video_data = requests.get(video_url).content

        with open(video_path, "wb") as f:
            f.write(video_data)

        return video_path

    except Exception as e:
        raise Exception(f"Pexels error: {str(e)}")


# ----------------------------
# VOICE GENERATION
# ----------------------------
def generate_voice(text, file_id):
    audio_path = f"{OUTPUT_DIR}/{file_id}.mp3"
    tts = gTTS(text=text, lang="en")
    tts.save(audio_path)
    return audio_path


# ----------------------------
# VIDEO BUILDER
# ----------------------------
def build_video(bg_video, audio_file, output_file, hook, cta):

    command = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", bg_video,
        "-i", audio_file,

        "-vf",
        (
            "scale=1080:1920,"
            "drawtext=text='" + hook + "':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=200:enable='lt(t,3)',"
            "drawtext=text='" + cta + "':fontsize=55:fontcolor=yellow:x=(w-text_w)/2:y=200:enable='gte(t,8)'"
        ),

        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        output_file
    ]

    subprocess.run(command, check=True)


# ----------------------------
# MAIN ENDPOINT
# ----------------------------
@app.post("/generate-video")
def generate_video(request: VideoRequest):

    try:
        file_id = str(uuid.uuid4())

        # basic script split
        parts = request.text.split(".")
        hook = parts[0][:60] if parts else "Build income online"
        cta = "Get Nomadic Wallet in bio"

        # 1. Pexels video
        bg_video = get_pexels_video(request.text)

        # 2. voice
        audio_file = generate_voice(request.text, file_id)

        # 3. output
        output_file = f"{OUTPUT_DIR}/{file_id}.mp4"

        # 4. build video
        build_video(bg_video, audio_file, output_file, hook, cta)

        return {
            "video_url": f"/{output_file}",
            "audio_file": audio_file,
            "status": "success"
        }

    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }
