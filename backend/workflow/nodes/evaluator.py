import logging
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_cerebras import ChatCerebras
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter
from pydantic import BaseModel, Field

from backend.workflow.models.state import State
from backend.workflow.utils.HFSpace.hf_space_wrapper import ManimExecutor

logger = logging.getLogger(__name__)

# TODO: create Enum class for evaluation for better llm output


class EvaluatorAgentOutput(BaseModel):
    """Output format for code evaluation."""

    evaluation: Literal["retry", "continue"] = Field(
        default="continue",
        description="Output retry if there is need for retrying the code for current step, else output continue",
    )
    feedback: str = Field(
        default="",
        description="Effective feedback to improve the code for current phase if evaluation is retry, otherwise output empty string",
    )


async def evaluator_agent(state: State):
    logger.info("Evaluator:")
    # check for syntax error first
    executor = ManimExecutor(uuid=state.uuid)
    err = ""
    final_code = "\n".join(state.code_generated.split("\n")[1:-1])
    try:
        err = await executor.test_code(final_code)
    except Exception as e:
        return {"code_generated": final_code, "error_message": str(e)}

    if err:
        logger.info("Execution error:" + err)
        return {
            "code_generated": final_code,
            "error": err,
            "evaluator_next_step": "retry",
            "feedback": "Rectify the syntax error",
        }
    logger.info("No syntax errors")

    # llm = init_chat_model("gpt-oss-120b", model_provider="cerebras")
    # llm = init_chat_model("groq:llama-3.1-8b-instant")
    llm = init_chat_model("groq:openai/gpt-oss-20b")
    # llm = init_chat_model("groq:groq/compound")
    # llm = ChatCerebras(model="gpt-oss-120b")

    system_prompt = """
You are a highly specialized Senior Python QA Developer for the Manim Animation Library.

Your task is to critically analyze the provided Python code snippet based on the overall scene description and the current animation phase. Your focus is strictly on semantic and functional errors that would prevent a successful, meaningful animation.

Evaluation Criteria:

1. Scene Inclusion: Are all Mobjects explicitly added to the scene?
2. Coordinate Sanity & Placement: Are objects positioned appropriately without unnecessary overlap?
3. Animation Logic & Dependencies: Do animations follow a logical sequence?
4. Transformations: Do transformations make sense for the Mobject types?
5. Timing: Is run_time appropriate? Is the timing of animation adequate enough to pay proper attention to specific parts of the screen.
6. Step Compliance: Check whether the current step of the multi-step generation process is interpreted correctly and reflected in the produced code. Although this condition can be loosened for steps like "Render the animation as video", because the actual rendering of manim video is done by running command in the command line.
"""
    # You are a senior Python QA developer
    # specializing in the Manim animation library.
    # Your task is to check for semantic errors in the given python code
    # based on the description of the overall scene and the current phase.
    # Do not be too strict in evaluation.

    # Task:
    # 1. Check your code for common issues:
    # - Are all objects added to scene before animating?
    # - Are coordinates within bounds (-7 to 7, -4 to 4)?
    # - Are animations in logical order?
    # - Do transforms make sense?
    # - Is the length of animation sound enough for the given task

    query = """
Scene description: {scene_description}
Current Phase: {current_step_description}
Code generated so far:
{code_generated}
"""

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", query),
        ]
    )
    evaluator = llm.with_structured_output(EvaluatorAgentOutput)
    pipeline = prompt_template | evaluator
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            result = await pipeline.ainvoke(
                {
                    "scene_description": state.query,
                    "current_step_description": state.current_step_description,
                    "code_generated": final_code,
                }
            )
            break
        except Exception as e:
            if attempt == max_attempts - 1:
                return {"code_generated": final_code, "error_message": str(e)}
    if result.evaluation == "retry":
        logger.info("Retry")
        logger.info("Feedback " + result.feedback)
        return {
            "code_generated": final_code,
            "feedback": result.feedback,
            "evaluator_next_step": "retry",
        }

    if len(state.steps) == state.completed_steps + 1:
        logger.info("Done scene generation")
        return {
            "code_generated": final_code,
            "feedback": "",
            "completed_steps": len(state.steps),
            "evaluator_next_step": "continue",
        }

    logger.info("Move to next step")
    logger.info("Completed steps: " + str(state.completed_steps + 1))
    return {
        "code_generated": final_code,
        "feedback": "",
        "evaluator_next_step": "next_step",
        "completed_steps": state.completed_steps + 1,
    }
