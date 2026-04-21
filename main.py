from fastapi import FastAPI
from gtts import gTTS
import uuid
import os

app = FastAPI()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/")
def home():
    return {"status": "AI Video Server Running"}

@app.get("/test")
def test():
    return {"message": "Your API is working!"}

@app.post("/generate-audio")
def generate_audio(text: str):
    file_id = str(uuid.uuid4())
    file_path = f"{OUTPUT_DIR}/{file_id}.mp3"

    tts = gTTS(text=text, lang="en")
    tts.save(file_path)

    return {"file": file_path}
