import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# =========================
# OUTPUT DIRECTORY
# =========================
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# VIDEO GENERATION LAYER (ABSTRACTION)
# =========================
def generate_scene_video(scene, job_id, index):
    """
    SINGLE ENTRY POINT for video generation.

    CURRENT STATE:
    - placeholder implementation

    NEXT STATE:
    - Stable Video Diffusion integration (GPU worker)
    """

    clip_path = os.path.join(
        OUTPUT_DIR,
        f"{job_id}_scene_{index}.mp4"
    )

    # TEMP PLACEHOLDER (safe fallback)
    with open(clip_path, "wb") as f:
        f.write(b"placeholder")

    return clip_path


# =========================
# PIPELINE: BUILD VIDEO FROM SCENES
# =========================
def generate_video_from_scenes(scenes, job_id):

    clips = []

    for i, scene in enumerate(scenes):

        clip_path = generate_scene_video(scene, job_id, i)
        clips.append(clip_path)

    return clips


# =========================
# PROCESS JOB
# =========================
def process_video_job(job_id, scenes):

    try:
        clips = generate_video_from_scenes(scenes, job_id)

        # FINAL OUTPUT (FFMPEG will replace this later)
        final_video_path = os.path.join(
            OUTPUT_DIR,
            f"{job_id}_final.mp4"
        )

        # Placeholder final video file
        with open(final_video_path, "wb") as f:
            f.write(b"placeholder-final-video")

        return {
            "status": "complete",
            "video_url": final_video_path,
            "error": None
        }

    except Exception as e:
        return {
            "status": "failed",
            "video_url": None,
            "error": str(e)
        }


# =========================
# API ENDPOINT
# =========================
@app.post("/api/video/webhook/start")
async def start_video_job(request: Request):

    body = await request.json()

    job_id = body.get("job_id", "unknown")
    scenes = body.get("scenes", [])

    result = process_video_job(job_id, scenes)

    return JSONResponse({
        "job_id": job_id,
        "status": result["status"],
        "video_url": result["video_url"],
        "error": result["error"]
    })


# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ai-video-backend"
    }
