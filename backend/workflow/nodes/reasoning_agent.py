import asyncio
import logging
from typing import Annotated

import annotated_types
from langchain.chat_models import init_chat_model
from langchain_cerebras import ChatCerebras
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter
from pydantic import BaseModel, Field

from backend.workflow.models.state import State
from backend.workflow.models.state_agent_schemas import VideoCreationStep

logger = logging.getLogger(__name__)


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
    logger.info("Reasoning Agent: ")
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=0.2,
        check_every_n_seconds=2,
        # max_bucket_size=5,
    )
    llm = init_chat_model("groq:llama-3.3-70b-versatile")

    # llm = init_chat_model("groq:moonshotai/kimi-k2-instruct-0905")
    # llm = init_chat_model(
    #     "llama-3.3-70b", model_provider="cerebras", rate_limiter=rate_limiter
    # )
    # llm = init_chat_model("groq:openai/gpt-oss-20b")
    # llm = ChatCerebras(model="llama-3.3-70b")

    system_prompt = """You are an expert senior Python developer
specializing in the Manim animation library.  
Your task is to plan a detailed, incremental roadmap for implementing a Manim
scene based on the description provided.  Each step should be small enough
that a separate piece of Python code (or a small code edit) can be written for
that step without requiring a large amount of context from later steps.  
The roadmap will be used for iterative code refinement, so avoid large
jumps in complexity; instead, break the work into natural, self-contained
chunks that build on the previous ones.

Guidelines

1. Incremental granularity -  
   - Use a clear “progression” wording (e.g., “Create the background”,  
     “Add the first object”, “Animate the first object”, …) so the next step
     clearly extends the previous one.

2. Maximum of 15 steps - keep the total number ≤ 15, and fewer if the
   query is simple.  The step count is counted after you have performed the
   incremental split.

3. Logical execution order - list the steps exactly as they should be
   written/executed in a typical Manim script: start with scene setup,
   then object creation, then animations, then clean-up or final transitions.

4. No actual code - only describe the plan; do not write Python or
   Manim code.  The output must be a pure outline that can be turned into
   code later.

5. No execution-only steps - Do not include meta-steps such as “Test the animation”,
   “Iterate for accuracy” or “Reverse the animation unless the proof explicitly requires it”.
   Only describe visual or structural actions that appear in the final animation.

5. Clarity and pacing - aim for slightly longer animation times than
   the bare minimum, and keep the overall scene length reasonable given the
   described complexity.

6. Iterative friendliness - make sure each step introduces only one new
   concept or a small combination of concepts.  This way the downstream
   agent can generate a code snippet for the step, test it, and then move on
   to the next step without needing to rewrite large portions of previous
   code.

Remember: keep steps small, sequential, and explicitly tied to the previous
step so that incremental code generation proceeds smoothly."""

    #     system_prompt = """You are an expert senior Python developer
    # specializing in the Manim animation library.
    # Your task is to plan out the detailed, step-by-step process
    # required to implement a scene in Manim based on the description provided.
    # Keep the number of steps less if the complexity of query is less.
    # Reason about the total time length of animation required based on the complexity
    # of the query and include the time length for each animation step.
    # Make the animation speed deliberately slower for better clarity, and
    # also keep the length of animation a little longer.

    # Requirements:
    # 1. Break down the scene into clear, actionable steps in sequential
    # order for implementation.
    # 2. Make sure to limit the number of steps by 15, keep the number of steps
    # less if the complexity of query is less.
    # 3. Include what objects, animations, and transitions will be used.
    # 4. Include the time length of animation which is apt for each step.
    # 5. Mention any special camera movements or effects if they enhance visual appeal.
    # 6. Describe the order of execution logically, from setup to rendering.
    # 7. Avoid writing actual Manim code — focus only on the planning and structure.
    # 8. Think carefully and break down the prompt into appropriate steps for
    # visual clarity and better animation.
    # """

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{scene_description}"),
        ]
    )

    planner = llm.with_structured_output(ReasoningAgentOutput)
    pipeline = prompt_template | planner
    err = None
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            scene_generation_steps = await pipeline.ainvoke(
                {"scene_description": state.query}
            )
            break
        except Exception as e:
            asyncio.sleep(2**attempt)
            if attempt == max_attempts - 1:
                err = repr(e)
    if err is not None:
        return {"error_message": err}
    logger.info(scene_generation_steps.steps)
    return {"steps": scene_generation_steps.steps}
