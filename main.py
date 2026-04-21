from pydantic import BaseModel

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
