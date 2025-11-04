from pydantic import BaseModel, Field
from typing import Annotated
import operator
from uuid import uuid4
from backend.workflow.agents.planner import WorkerStep


class WorkerOutput(BaseModel):
    step_id: int = Field(default=0, description="Step number for scene creation")
    url: str = Field(default="", description="Uploaded URL of the generated video")


class WorkerState(BaseModel):
    step_id: int = Field(default=0, description="Step number for scene creation")
    description: str = Field(default="", description="Description of the step")
    docs: str = Field(
        default="",
        description="Most relevant documentation of manim \
to assist in writing python code using manim-ce library for the given description",
    )
    feedback: str = Field(default="", description="Feedback to improve the python code")
    code: str = Field(
        default="",
        description="Generated python code using manim-ce \
library for the given description",
    )
    code_retry_or_not: str = Field(
        default="",
        description="Whether to retry code \
generation or not",
    )
    url: str = Field(default="", description="Uploaded URL of the generated video")
    completed_steps: Annotated[list[WorkerOutput], operator.add] = Field(
        default_factory=list,
        description="List of completed steps with their outputs",
    )  # Workers write to this in parallel, list of WorkerOutput


class State(BaseModel):
    uuid: str = Field(default=uuid4().hex, description="Unique identifier for client")
    prompt: str = Field(default="", description="User prompt for scene generation")
    steps: list[WorkerStep] = Field(
        default_factory=list, description="List of planned steps for the scene"
    )
    completed_steps: Annotated[list[WorkerOutput], operator.add] = Field(
        default_factory=list,
        description="List of completed steps with their outputs",
    )  # Workers write to this in parallel, list of WorkerOutput
    success: bool = Field(
        default=True, description="Indicates if the pipeline completed successfully"
    )
    error_message: str = Field(
        default="", description="Error message if the pipeline failed"
    )
    sorted_urls: list[str] = Field(
        default_factory=list, description="List of video URLs sorted by step_id"
    )
