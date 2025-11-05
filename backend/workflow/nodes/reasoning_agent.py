from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.workflow.models.state import State


class VideoCreationStep(BaseModel):
    step_id: int = Field(
        default=0,
        description="nth step in the sequential \
        order for scene creation",
    )
    description: str = Field(default="", description="Description of the current step")


class ReasoningAgentOutput(BaseModel):
    steps: list[VideoCreationStep] = Field(
        default_factory=list,
        description="Steps \
        required for the scene creation",
    )


def reasoning_agent(state: State):
    llm = init_chat_model("groq:openai/gpt-oss-20b", temperature=0.7)

    system_prompt = """You are an expert senior Python developer \
    specializing in the Manim animation library.  
    Your task is to plan out the detailed, step-by-step process \
    required to implement a scene in Manim based on the description provided.

    Requirements:
    1. Break down the scene into clear, actionable steps in sequential \
    order for implementation.
    2. Include what objects, animations, and transitions will be used.
    3. Mention any special camera movements or effects if they enhance visual appeal.
    4. Describe the order of execution logically, from setup to rendering.
    5. Avoid writing actual Manim code — focus only on the planning and structure.
    """

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{scene_description}"),
        ]
    )

    planner = llm.with_structured_output(ReasoningAgentOutput)
    pipeline = prompt_template | planner
    scene_generation_steps = pipeline.invoke({"scene_description": state.prompt})
    return {"steps": scene_generation_steps.steps}
