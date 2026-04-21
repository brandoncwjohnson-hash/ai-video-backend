from fastapi import FastAPI
from pydantic import BaseModel
from gtts import gTTS
import uuid
import os

app = FastAPI()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class AudioRequest(BaseModel):
    text: str

@app.post("/generate-audio")
def generate_audio(request: AudioRequest):
    try:
        file_id = str(uuid.uuid4())
        file_path = f"{OUTPUT_DIR}/{file_id}.mp3"

        tts = gTTS(text=request.text, lang="en")
        tts.save(file_path)

        return {"file": file_path}

    except Exception as e:
        return {"error": str(e)}
