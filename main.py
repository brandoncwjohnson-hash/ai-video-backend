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

# 👉 STEP LATER: put your Pexels API key here
PEXELS_API_KEY = "PUT_YOUR_PEXELS_API_KEY_HERE"


class VideoRequest(BaseModel):
    text: str


# ----------------------------
# 1. GET PEXELS VIDEO
# ----------------------------
def get_pexels_video(query: str):
    headers = {"Authorization": PEXELS_API_KEY}

    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"
    res = requests.get(url, headers=headers).json()

    video_url = res["videos"][0]["video_files"][0]["link"]

    file_id = str(uuid.uuid4())
    video_path = f"{OUTPUT_DIR}/{file_id}.mp4"

    video_data = requests.get(video_url).content

    with open(video_path, "wb") as f:
        f.write(video_data)

    return video_path


# ----------------------------
# 2. GENERATE VOICE
# ----------------------------
def generate_voice(text, file_id):
    audio_path = f"{OUTPUT_DIR}/{file_id}.mp3"
    tts = gTTS(text=text, lang="en")
    tts.save(audio_path)
    return audio_path


# ----------------------------
# 3. BUILD VIDEO
# ----------------------------
def build_video(bg_video, audio_file, output_file, hook, cta):

    command = [
        "ffmpeg", "-y",

        # loop background video
        "-stream_loop", "-1",
        "-i", bg_video,

        # audio
        "-i", audio_file,

        # video effects
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
# 4. MAIN ENDPOINT
# ----------------------------
@app.post("/generate-video")
def generate_video(request: VideoRequest):

    try:
        file_id = str(uuid.uuid4())

        # split script
        parts = request.text.split(".")

        hook = parts[0][:60] if len(parts) > 0 else "Hook"
        cta = "Get Nomadic Wallet in bio"

        # STEP 1: Pexels background
        bg_video = get_pexels_video(request.text)

        # STEP 2: voice
        audio_file = generate_voice(request.text, file_id)

        # STEP 3: output path
        output_file = f"{OUTPUT_DIR}/{file_id}.mp4"

        # STEP 4: build video
        build_video(bg_video, audio_file, output_file, hook, cta)

        return {
            "video_url": f"/{output_file}",
            "audio_file": audio_file
        }

    except Exception as e:
        return {"error": str(e)}
