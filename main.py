from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import requests
import uuid
import os
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips

app = FastAPI()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def generate_image(prompt, api_key):
    url = "https://api.openai.com/v1/images/generations"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024"
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    image_url = result["data"][0]["url"]
    image_data = requests.get(image_url).content

    filename = f"{uuid.uuid4()}.jpg"
    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "wb") as f:
        f.write(image_data)

    return path

def add_text(image_path, text):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(FONT_PATH, 60)

    width, height = img.size
    text = text.upper()

    # wrap text
    lines = []
    words = text.split()
    line = ""

    for word in words:
        test_line = f"{line} {word}".strip()
        w, h = draw.textsize(test_line, font=font)

        if w < width * 0.8:
            line = test_line
        else:
            lines.append(line)
            line = word

    lines.append(line)

    y = height // 2 - (len(lines) * 40)

    for l in lines:
        w, h = draw.textsize(l, font=font)
        x = (width - w) / 2

        draw.text((x+2, y+2), l, font=font, fill="black")
        draw.text((x, y), l, font=font, fill="white")

        y += h + 10

    output_path = image_path.replace(".jpg", "_text.jpg")
    img.save(output_path)

    return output_path

def create_clip(image_path, duration=4):
    clip = ImageClip(image_path).set_duration(duration)

    # simple zoom effect
    clip = clip.resize(lambda t: 1 + 0.05 * t)

    return clip

@app.post("/generate-video")
async def generate_video(request: Request):
    data = await request.json()

    scenes = data["scenes"]
    api_key = data["openai_api_key"]

    clips = []

    for scene in scenes:
        text = scene["text"]
        prompt = scene["image_prompt"]

        img_path = generate_image(prompt, api_key)
        img_with_text = add_text(img_path, text)

        clip = create_clip(img_with_text)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    output_file = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.mp4")
    final.write_videofile(output_file, fps=24)

    return FileResponse(output_file, media_type="video/mp4", filename="video.mp4")
