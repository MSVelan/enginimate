import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from backend.workflow.graph import graph
from backend.workflow.models.state import State


app = FastAPI()


class QueryPayload(BaseModel):
    uuid: str
    query: str


@app.post("/run")
async def run_workflow(payload: QueryPayload):
    state_input = {"uuid": payload.uuid, "query": payload.query}
    state = State(**state_input)
    result_state = await graph.ainvoke(state)
    if result_state["error_message"]:
        return {"url": "", "error": result_state["error_message"]}
    return {"url": result_state["url"], "error": ""}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
