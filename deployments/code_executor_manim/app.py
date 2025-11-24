import asyncio
import datetime
import json
import logging
import uuid
from contextlib import asynccontextmanager
from enum import Enum

import redis.asyncio as redis
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from manim_executor import cleanup, run_and_upload, test_code
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Build successful, ready to take on requests.")
    yield


app = FastAPI(title="agent-sandbox", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
)

r = redis.from_url("redis://localhost:6379/0", decode_responses=True)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionRequest(BaseModel):
    code: str
    uuid: str = str(uuid.uuid4())


class CleanupRequest(BaseModel):
    uuid: str
    status: JobStatus
    error_message: str = ""


class ExecutionResponse(BaseModel):
    uuid: str
    status: JobStatus
    error: str = ""
    error_message: str = ""


class UploadResponse(BaseModel):
    url: str
    status: JobStatus
    error_message: str = ""


async def _test_code(uuid: str, code: str):
    await r.hset(uuid, mapping={"status": JobStatus.PROCESSING, "code": code})
    try:
        err = await test_code("manim_test_" + uuid, code)
        await r.hset(
            uuid,
            mapping={
                "status": JobStatus.COMPLETED,
                "error": err,
                "error_message": "",
            },
        )
    except Exception as e:
        await r.hset(
            uuid,
            mapping={
                "status": JobStatus.FAILED,
                "error": "",
                "error_message": str(e),
            },
        )


@app.post("/trigger-test-code")
async def tester(request: ExecutionRequest, background_tasks: BackgroundTasks):
    if await r.exists(request.uuid):
        await r.delete(request.uuid)

    await r.hset(
        request.uuid,
        mapping={"status": JobStatus.PENDING, "code": request.code},
    )
    await r.expire(request.uuid, 60 * 60 * 1)
    background_tasks.add_task(_test_code, request.uuid, request.code)

    return ExecutionResponse(uuid=request.uuid, status=JobStatus.PENDING)


async def _wait_for_code_execution(
    uuid: str, poll_interval: float = 5, timeout: int = 60 * 30
):
    """Poll Redis until the job reaches a terminal state."""
    now = datetime.datetime.now()
    maxt = datetime.timedelta(seconds=int(timeout)) + now
    while datetime.datetime.now() <= maxt:
        data = await r.hgetall(uuid)
        if not data:
            return {
                "status": JobStatus.FAILED,
                "error_message": "Job not found",
                "error": "",
            }
        status = data.get("status")
        if status in (JobStatus.COMPLETED, JobStatus.FAILED):
            return {
                "status": status,
                "error": data.get("error"),
                "error_message": data.get("error_message"),
            }
        await asyncio.sleep(float(poll_interval))
    raise HTTPException(detail="Timeout occurred")


@app.get("/result/test-code/{uuid}")
async def get_test_result(uuid: str, poll_interval: float = 5, timeout: int = 60 * 30):
    try:
        return await _wait_for_code_execution(uuid, poll_interval, timeout)
    except:
        raise


@app.get("/events/test-code/{uuid}")
async def stream_result(uuid: str):
    """
    Returns an SSE stream that emits a single event when the job finishes.
    """

    async def event_generator():
        result = await _wait_for_code_execution(uuid)
        # The payload is sent as a JSON string in the `data` field.
        yield {
            "event": "job_finished",
            "data": json.dumps(result),
        }

    return EventSourceResponse(event_generator())


# below routes are not actually used in production app and hence aren't asynchronous


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
        "endpoints": [
            "/trigger-test-code",
            "/events/test-code/:uuid",
            "/result/test-code/:uuid",
            "/run-and-upload",
        ],
    }


@app.get("/cleanup")
async def cleandir(request: CleanupRequest):
    pjt_name = "manim_test_" + request.uuid
    try:
        cleanup(pjt_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # return None is same as returning status 200 with no body
