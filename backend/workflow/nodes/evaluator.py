from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal

from backend.workflow.models.state import State


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


def evaluator_agent(state: State):
    llm = init_chat_model("groq:openai/gpt-oss-20b", temperature=0.7)

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
- Are run_times reasonable (0.5-3 seconds)?
- Do transforms make sense?
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
    result = pipeline.invoke(
        {
            "scene_description": state.query,
            "current_step_description": state.current_step_description,
            "code_generated": state.code_generated,
            "formatted_docs": state.formatted_docs,
        }
    )
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
