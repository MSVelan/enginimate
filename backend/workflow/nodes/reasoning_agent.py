from typing import Annotated
import annotated_types
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.workflow.models.state_agent_schemas import VideoCreationStep
from backend.workflow.models.state import State


class ReasoningAgentOutput(BaseModel):
    # definition taken from pydantic.conlist
    steps: Annotated[list[VideoCreationStep], annotated_types.Len(0, max_length=15)] = (
        Field(
            default_factory=list,
            description="Steps required for the scene creation",
            max_length=15,
        )
    )


async def reasoning_agent(state: State):
    llm = init_chat_model("groq:openai/gpt-oss-20b")

    system_prompt = """You are an expert senior Python developer \
specializing in the Manim animation library.  
Your task is to plan out the detailed, step-by-step process \
required to implement a scene in Manim based on the description provided. \
Keep the number of steps less if the complexity of query is less.
Reason about the total time length of animation required based on the complexity \
of the query and include the time length for each animation step.

Requirements:
1. Break down the scene into clear, actionable steps in sequential \
order for implementation.
2. Make sure to limit the number of steps by 15, keep the number of steps \
less if the complexity of query is less.
3. Include what objects, animations, and transitions will be used.
4. Include the time length of animation which is apt for each step.
5. Mention any special camera movements or effects if they enhance visual appeal.
6. Describe the order of execution logically, from setup to rendering.
7. Avoid writing actual Manim code — focus only on the planning and structure.
"""

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{scene_description}"),
        ]
    )

    planner = llm.with_structured_output(ReasoningAgentOutput)
    pipeline = prompt_template | planner
    print("Reasoning Agent: ")
    err = None
    try:
        scene_generation_steps = await pipeline.ainvoke(
            {"scene_description": state.query}
        )
    except Exception as e:
        err = repr(e)
    if err is not None:
        return {"error_message": err}
    print(scene_generation_steps.steps)
    return {"steps": scene_generation_steps.steps}
