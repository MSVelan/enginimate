from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.workflow.models.state_agent_schemas import (
    QueryDecomposerOutput,
    VideoCreationStep,
)


class State(BaseModel):
    uuid: str = Field(default=uuid4().hex, description="Unique identifier for client")
    query: str = Field(default="", description="User query for scene generation")
    steps: list[VideoCreationStep] = Field(
        default_factory=list,
        description="List of \
        planned steps for the scene in sequential order",
    )
    current_step_description: str = Field(
        default="",
        description="Description of \
        current step for scene creation",
    )
    # Write after code generation of each major step
    completed_steps: int = Field(default=0, description="Total completed steps")
    prompts: QueryDecomposerOutput = Field(
        default_factory=QueryDecomposerOutput,
        description="\
        List of prompts for retrieval of relevant documents in the RAG pipeline",
    )
    formatted_docs: str = Field(
        default="",
        description="Content of retrieved \
        relevant documents",
    )
    code_generated: str = Field(
        default="",
        description="Correct code generated so far \
        until the current step",
    )
    error: str = Field(default="", description="Error generated on code execution")
    feedback: str = Field(
        default="",
        description="Constructive feedback for improving the current code",
    )
    evaluator_next_step: Literal["retry", "next_step", "continue"] = Field(
        default="next_step",
        description="Whether to retry current step or continue",
    )
    url: str = Field(
        default="",
        description="Final video url after \
        uploading to cloudinary",
    )
    public_id: Optional[str] = Field(
        default="",
        description="Public-id of video uploaded in cloudinary",
    )
    created_at: str = Field(
        default="",
        description="Time at which video rendering job was submitted",
    )
    completed_at: str = Field(
        default="",
        description="Time at which video rendering job was completed",
    )
    success: bool = Field(
        default=True,
        description="Indicates if the pipeline has \
        completed successfully",
    )
    error_message: str = Field(
        default="",
        description="Error message if the \
        pipeline failed",
    )
