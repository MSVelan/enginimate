import asyncio
import datetime
import json
import logging
import os
from enum import Enum
from typing import Optional

import redis.asyncio as redis
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.workflow.graph import graph
from backend.workflow.models.state import State
from backend.workflow.utils.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
origins = [FRONTEND_URL]

logger.info(f"Added origins to the CORS: {origins}")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobResultResponse(BaseModel):
    uuid: str
    status: JobStatus
    url: Optional[str] = None
    error: Optional[str] = None


class Request(BaseModel):
    uuid: str
    query: str


async def _run_graph_and_store(uuid: str, query: str):
    await r.hset(uuid, mapping={"status": JobStatus.PROCESSING, "query": query})
    state_input = {"uuid": uuid, "query": query}
    state = State(**state_input)
    logger.info(f"Started workflow for uuid: {uuid} - query: {query}")
    result_state = await graph.ainvoke(state, config={"recursion_limit": 150})
    if result_state.get("error_message"):
        logger.error(
            f"Error occurred in the workflow for uuid: {uuid} "
            f'- query: {query} - {result_state.get("error_message")}'
        )
        await r.hset(
            uuid,
            mapping={
                "status": JobStatus.FAILED,
                "error": result_state["error_message"],
                "url": "",
            },
        )
    else:
        logger.info(
            f"Workflow completed successfully for uuid: {uuid} - query: {query} \
                - video url: {result_state['url']}"
        )
        await r.hset(
            uuid,
            mapping={
                "status": JobStatus.COMPLETED,
                "url": result_state["url"],
                "error": "",
            },
        )


@app.post("/run", response_model=JobResultResponse)
async def run_workflow(request: Request, background_tasks: BackgroundTasks):
    # if request uuid already exists, override
    if await r.exists(request.uuid):
        await r.delete(request.uuid)
        # status = await r.hget(request.uuid, "status")
        # return JobResultResponse(uuid=request.uuid, status=JobStatus(status))

    await r.hset(
        request.uuid,
        mapping={"status": JobStatus.PENDING, "query": request.query},
    )
    await r.expire(request.uuid, 60 * 60 * 4)

    background_tasks.add_task(_run_graph_and_store, request.uuid, request.query)
    return JobResultResponse(uuid=request.uuid, status=JobStatus.PENDING)


async def _wait_for_final_status(uuid: str, poll_interval: float = 5, timeout=60 * 45):
    """Poll Redis until the job reaches a terminal state."""
    now = datetime.datetime.now()
    maxt = datetime.timedelta(seconds=timeout) + now
    while datetime.datetime.now() <= maxt:
        data = await r.hgetall(uuid)
        if not data:
            return {
                "status": JobStatus.FAILED,
                "error": "Job not found",
                "url": "",
            }
        status = data.get("status")
        if status in (JobStatus.COMPLETED, JobStatus.FAILED):
            return {
                "status": status,
                "url": data.get("url"),
                "error": data.get("error"),
            }
        await asyncio.sleep(poll_interval)


# trigger job using /run endpoint and then get back streaming response with this endpoint
@app.get("/events/{uuid}")
async def stream_result(uuid: str):
    """
    Returns an SSE stream that emits a single event when the job finishes.
    """

    async def event_generator():
        result = await _wait_for_final_status(uuid)
        # The payload is sent as a JSON string in the `data` field.
        yield {
            "event": "job_finished",
            "data": json.dumps(result),
        }

    return EventSourceResponse(event_generator())


# below endpoint can be used for short polling
@app.get("/status/{uuid}", response_model=JobResultResponse)
async def get_status(uuid: str):
    if not await r.exists(uuid):
        raise HTTPException(status_code=404, detail="Job not found")

    data = await r.hgetall(uuid)
    return JobResultResponse(
        uuid=uuid,
        status=JobStatus(data["status"]),
        url=data.get("url") or None,
        error=data.get("error") or None,
    )


# below endpoint can be used for long polling
@app.get("/result/{uuid}", response_model=JobResultResponse)
async def get_result(uuid: str):
    if not await r.exists(uuid):
        raise HTTPException(status_code=404, detail="Job not found")

    result = await _wait_for_final_status(uuid)
    if result is None:
        raise HTTPException(
            status_code=500, detail="Time limit exceeded for job during long polling"
        )

    return JobResultResponse(
        uuid=uuid,
        status=result.get("status") or JobStatus.FAILED,
        url=result.get("url") or None,
        error=result.get("error") or None,
    )


@app.get("/")
async def root():
    """API documentation endpoint"""
    return {
        "message": "Manim Workflow API",
        "endpoints": {
            "POST /run": "Trigger Manim workflow job",
            "GET /status/{uuid}": "Check job status",
            "GET /result/{uuid}": "Get result for the job uuid (supports long polling)",
            "GET /events/{uuid}": "SSE stream that emits event when job finishes",
        },
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
