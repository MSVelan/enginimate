from pydantic import BaseModel, Field


class QueryDecomposerOutput(BaseModel):
    code_prompt: str = Field(
        default="",
        description="Clean minimal prompt \
        for fetching relevant code snippets",
    )
    documentation_prompt: str = Field(
        default="",
        description="Clean minimal prompt \
        for fetching relevant documentation",
    )
    summary_prompt: str = Field(
        default="",
        description="Clean minimal prompt for \
        fetching relevant autosummary snippets \
        (summary of class names, functions, methods)",
    )


class VideoCreationStep(BaseModel):
    step_id: int = Field(
        default=0,
        description="nth step in the sequential \
        order for scene creation",
    )
    description: str = Field(default="", description="Description of the current step")
