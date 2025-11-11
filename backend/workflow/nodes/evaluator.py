from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal

from backend.workflow.models.state import State
from backend.workflow.utils.HFSpace.hf_space_wrapper import ManimExecutor


class EvaluatorAgentOutput(BaseModel):
    evaluation: Literal["retry", "continue"] = Field(
        default="",
        description="Whether to retry code generation for current step",
    )
    feedback: str = Field(
        default="",
        description="Effective feedback to improve the code for current phase \
only if evaluation is retry, leave empty otherwise",
    )


async def evaluator_agent(state: State):
    # check for syntax error first
    executor = ManimExecutor(uuid=state.uuid)
    err = ""
    try:
        err = executor.test_code(state.code_generated)
    except Exception as e:
        return {"error_message": str(e)}

    if err:
        return {
            "error": err,
            "evaluator_next_step": "retry",
            "feedback": "Rectify the syntax error",
        }

    llm = init_chat_model("groq:openai/gpt-oss-20b")

    system_prompt = """You are a senior Python QA developer \
specializing in the Manim animation library.  
Your task is to check for semantic errors in the given python code \
based on the description of the overall scene and the current phase. \
Do not be too strict in evaluation.

Task:
1. Check your code for common issues:
- Are all objects added to scene before animating?
- Are coordinates within bounds (-7 to 7, -4 to 4)?
- Are animations in logical order?
- Do transforms make sense?
- Is the length of animation sound enough for the given task
"""

    query = """
Scene description: {scene_description}
Current Phase: {current_step_description}
Code generated so far:
{code_generated}
Context from manim-ce documentation:
{formatted_docs}
"""

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", query),
        ]
    )
    print("Evaluator:")
    evaluator = llm.with_structured_output(EvaluatorAgentOutput)
    pipeline = prompt_template | evaluator
    err = None
    try:
        result = await pipeline.ainvoke(
            {
                "scene_description": state.query,
                "current_step_description": state.current_step_description,
                "code_generated": state.code_generated,
                "formatted_docs": state.formatted_docs,
            }
        )
    except Exception as e:
        err = repr(e)
    if err is not None:
        return {"error_message": err}
    if result.evaluation == "retry":
        print("Retry")
        print("Feedback", result.feedback)
        return {"feedback": result.feedback, "evaluator_next_step": "retry"}

    if len(state.steps) == state.completed_steps + 1:
        # done video generation
        print("Done scene generation")
        return {
            "feedback": "",
            "completed_steps": len(state.steps),
            "evaluator_next_step": "continue",
        }

    print("Move to next step")
    # move to next step
    return {
        "feedback": "",
        "evaluator_next_step": "next_step",
        "completed_steps": state.completed_steps + 1,
    }
