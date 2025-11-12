from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import hmac
import hashlib
from typing import Optional, Dict
from enum import Enum
import asyncio
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

origins = [
    "http://localhost:8000",
    "https://api.github.com",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
)

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "MSVelan")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "enginimate")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-secret-key")

# In-memory storage (use Redis/database in production)
jobs: Dict[str, dict] = {}


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ManimRenderRequest(BaseModel):
    uuid: str
    code: str
    scene_name: str = "Enginimate"
    quality: str = "high"


class JobStatusResponse(BaseModel):
    uuid: str
    status: JobStatus
    video_url: Optional[str] = None
    public_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


@app.post("/trigger-rendering")
async def trigger_rendering(request: ManimRenderRequest):
    """
    Trigger Manim rendering job
    """
    # Check if UUID already exists
    if request.uuid in jobs:
        return {
            "success": False,
            "message": f"Job with UUID {request.uuid} already exists",
            "status": jobs[request.uuid]["status"],
        }

    # Create job entry
    jobs[request.uuid] = {
        "uuid": request.uuid,
        "status": JobStatus.PENDING,
        "code": request.code,
        "scene_name": request.scene_name,
        "quality": request.quality,
        "video_url": None,
        "public_id": None,
        "error": None,
        "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "completed_at": None,
    }

    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/dispatches"
        payload = {
            "event_type": "render-manim",
            "client_payload": {
                "uuid": request.uuid,
                "code": request.code,
                "scene_name": request.scene_name,
                "quality": request.quality,
            },
        }
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",  # Add API version
            "Content-Type": "application/json",
            "User-Agent": "Test",
        }

        client = httpx.Client()
        response = client.post(
            url,
            headers=headers,
            json=payload,
        )
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 204:
            jobs[request.uuid]["status"] = JobStatus.PROCESSING
            return {
                "success": True,
                "uuid": request.uuid,
                "message": "Rendering job submitted successfully",
                "status": JobStatus.PROCESSING,
                "note": "Use GET /render-status/{uuid} to check status and get video URL",
            }
        else:
            jobs[request.uuid]["status"] = JobStatus.FAILED
            jobs[request.uuid]["error"] = f"GitHub API error: {response.text}"
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to trigger workflow: {response.text}",
            )

    except Exception as e:
        jobs[request.uuid]["status"] = JobStatus.FAILED
        jobs[request.uuid]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/render-status/{uuid}", response_model=JobStatusResponse)
async def get_render_status(uuid: str):
    """
    Get the status of a rendering job by UUID
    """
    if uuid not in jobs:
        raise HTTPException(status_code=404, detail=f"Job with UUID {uuid} not found")

    job = jobs[uuid]
    return JobStatusResponse(**job)


@app.get("/render-result/{uuid}")
async def get_render_result(uuid: str, wait: bool = False, timeout: int = 300):
    """
    Get the video URL for a completed job.

    - uuid: Job UUID
    - wait: If True, wait for job to complete (polling with timeout)
    - timeout: Maximum seconds to wait (default 300 = 5 minutes)
    """
    if uuid not in jobs:
        raise HTTPException(status_code=404, detail=f"Job with UUID {uuid} not found")

    job = jobs[uuid]

    # If wait=True, poll until completed or timeout
    if wait:
        elapsed = 0
        poll_interval = 3  # Check every 3 seconds

        while elapsed < timeout:
            if job["status"] == JobStatus.COMPLETED:
                return {
                    "success": True,
                    "uuid": uuid,
                    "video_url": job["video_url"],
                    "public_id": job["public_id"],
                }
            elif job["status"] == JobStatus.FAILED:
                return {"success": False, "uuid": uuid, "error": job["error"]}

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout reached
        raise HTTPException(
            status_code=408, detail=f"Job still processing after {timeout} seconds"
        )

    # No wait - return current status
    if job["status"] == JobStatus.COMPLETED:
        return {
            "success": True,
            "uuid": uuid,
            "video_url": job["video_url"],
            "public_id": job["public_id"],
        }
    elif job["status"] == JobStatus.FAILED:
        return {"success": False, "uuid": uuid, "error": job["error"]}
    else:
        return {
            "success": False,
            "uuid": uuid,
            "status": job["status"],
            "message": "Job is still processing",
        }


@app.post("/webhook/render-complete")
async def render_complete_webhook(request: Request):
    """
    Internal webhook endpoint that GitHub Actions calls when rendering is complete
    """
    body = await request.body()
    print(f"\n=== DEBUG WEBHOOK RECEIVED ===")
    print(f"Headers: {dict(request.headers)}")
    print(f"Body: {body.decode()}")
    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    print(signature)
    if signature:
        expected_signature = (
            "sha256="
            + hmac.new(WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
        )
        print(expected_signature)

        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse the payload
    payload = await request.json()
    uuid = payload.get("uuid")

    if not uuid or uuid not in jobs:
        print(f"Warning: Received webhook for unknown UUID: {uuid}")
        return {"success": False, "message": "Unknown UUID"}

    # Update job status
    job = jobs[uuid]

    if payload.get("status") == "completed":
        job["status"] = JobStatus.COMPLETED
        job["video_url"] = payload.get("video_url")
        job["public_id"] = payload.get("public_id")
        job["completed_at"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        print(f"Job {uuid} completed. Video URL: {job['video_url']}")
    else:
        job["status"] = JobStatus.FAILED
        job["error"] = payload.get("error", "Unknown error")
        job["completed_at"] = datetime.utcnow().isoformat()
        print(f"Job {uuid} failed. Error: {job['error']}")

    return {"success": True, "message": "Webhook processed", "uuid": uuid}


@app.delete("/job/{uuid}")
async def delete_job(uuid: str):
    """
    Delete a job from the queue (cleanup)
    """
    if uuid not in jobs:
        raise HTTPException(status_code=404, detail=f"Job with UUID {uuid} not found")

    del jobs[uuid]
    return {"success": True, "message": f"Job {uuid} deleted"}


@app.get("/jobs")
async def list_jobs():
    """
    List all jobs (for debugging)
    """
    return {"total": len(jobs), "jobs": list(jobs.values())}


@app.get("/")
async def root():
    return {
        "message": "Manim Render API",
        "endpoints": {
            "POST /trigger-rendering": "Trigger Manim rendering job",
            "GET /render-status/{uuid}": "Check job status",
            "GET /render-result/{uuid}": "Get video URL (supports wait parameter)",
            "GET /jobs": "List all jobs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
