from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import uuid

from manim_executor import test_code, run_and_upload, cleanup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-sandbox", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    logger.info("Build successful, ready to take on requests.")


class ExecutionRequest(BaseModel):
    code: str
    uuid: str = str(uuid.uuid4())


class CleanupRequest(BaseModel):
    uuid: str


class ExecutionResponse(BaseModel):
    error: str


class UploadResponse(BaseModel):
    url: str


@app.post("/test-code")
async def tester(request: ExecutionRequest):
    try:
        err = await test_code("manim_test_" + request.uuid, request.code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ExecutionResponse(error=err)


# Note: This route is deprecated
# HF Spaces clears mp4 files aggresively as part of its ephemeral storage management
# Checkout render_manim_videos server for this functionality
@app.post("/run-and-upload")
async def run_upload(request: ExecutionRequest):
    try:
        url = await run_and_upload("manim_test_" + request.uuid, request.code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return UploadResponse(url=url)


@app.get("/")
async def root():
    return {
        "message": "Sandbox is running",
        "endpoints": ["/test-code", "/run-and-upload"],
    }


@app.get("/cleanup")
async def cleandir(request: CleanupRequest):
    pjt_name = "manim_test_" + request.uuid
    try:
        cleanup(pjt_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # return None is same as returning status 200 with no body
