import uvicorn
import redis.asyncio as redis

from enum import Enum
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from backend.workflow.graph import graph
from backend.workflow.models.state import State

origins = ["http://localhost:3000"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
)

r = redis.from_url("redis://localhost:6379/0", decode_responses=True)


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
    result_state = await graph.ainvoke(state)
    if result_state.get("error_message"):
        await r.hset(
            uuid,
            mapping={
                "status": JobStatus.FAILED,
                "error": result_state["error_message"],
                "url": "",
            },
        )
    else:
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
    if await r.exists(request.uuid):
        status = await r.hget(request.uuid, "status")
        return JobResultResponse(uuid=request.uuid, status=JobStatus(status))

    await r.hset(
        request.uuid,
        mapping={"status": JobStatus.PENDING, "query": request.query},
    )
    await r.expire(request.uuid, 60 * 60 * 24)

    background_tasks.add_task(_run_graph_and_store, request.uuid, request.query)
    return JobResultResponse(uuid=request.uuid, status=JobStatus.PENDING)


@app.get("/result/{uuid}", response_model=JobResultResponse)
async def get_result(uuid: str):
    if not await r.exists(uuid):
        raise HTTPException(status_code=404, detail="Job not found")

    data = await r.hgetall(uuid)
    return JobResultResponse(
        uuid=uuid,
        status=JobStatus(data["status"]),
        url=data.get("url") or None,
        error=data.get("error") or None,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
