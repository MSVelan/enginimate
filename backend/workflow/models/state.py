from uuid import uuid4

from pydantic import BaseModel, Field

from typing import Literal

from backend.workflow.models.agent_schemas import (
    VideoCreationStep,
    QueryDecomposerOutput,
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
        default_factory=dict,
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
    feedback: list[str] = Field(
        default_factory=list,
        description="List of \
        constructive feedback for improving the current code",
    )
    done_code_generation: Literal["yes", "no"] = Field(
        default="no",
        description="\
        Code generation for all steps is done or not",
    )
    url: str = Field(
        default="",
        description="Final video url after \
        uploading to cloudinary",
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
