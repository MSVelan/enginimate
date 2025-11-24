import asyncio
import logging
from typing import Literal

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    SummarizationMiddleware,
    ToolRetryMiddleware,
    wrap_model_call,
)
from langchain.chat_models import init_chat_model
from langchain_cerebras import ChatCerebras
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

from backend.workflow.models.state import State
from backend.workflow.tools.coding_agent_tools import (
    fetch_code_snippets,
    fetch_docs,
    fetch_summary,
)
from backend.workflow.utils.HFSpace.hf_space_wrapper import ManimExecutor

logger = logging.getLogger(__name__)


@wrap_model_call
async def retry_model_middleware(request, handler):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(2**attempt)
            return await handler(request)
        except Exception as e:
            await asyncio.sleep(2**attempt)
            logger.warning(
                f"Retrying model call (attempt {attempt + 1}/{max_retries}) after error: {e}"
            )
            if attempt == max_retries - 1:
                raise  # Re-raise if all retries are exhausted
    return await handler(request)  # Should not be reached if exceptions are re-raised


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
        err_msg, err = await executor.test_code(final_code)
        if err_msg:
            return {"code_generated": final_code, "error_message": err_msg}
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

    async def evaluate_with_tools(
        scene_description, current_step_description, code_generated
    ):
        query = f"""
Scene description: {scene_description}
Current Phase: {current_step_description}
Code generated so far:
{code_generated}
"""
        rate_limiter = InMemoryRateLimiter(
            requests_per_second=0.2,  # Allow 0.2 requests per second (1 request every 5 seconds)
            check_every_n_seconds=2,  # Check every 100ms if a request is allowed
            # max_bucket_size=5,  # Allow a burst of up to 5 requests
        )
        llm = init_chat_model("groq:openai/gpt-oss-safeguard-20b")

        # llm = init_chat_model("groq:openai/gpt-oss-20b")
        # llm = init_chat_model("groq:moonshotai/kimi-k2-instruct-0905")
        # llm = init_chat_model("gpt-oss-120b", model_provider="cerebras")
        # llm = init_chat_model("groq:llama-3.1-8b-instant")
        # llm = init_chat_model("groq:groq/compound")
        # llm = ChatCerebras(model="gpt-oss-120b")

        parser = PydanticOutputParser(pydantic_object=EvaluatorAgentOutput)

        format_instructions = parser.get_format_instructions()

        system_prompt = f"""
You are a highly specialized Senior Python QA Developer for the Manim Animation Library.
Your task is to first verify that the supplied Python code snippet correctly implements the current step of the multi-step generation process, and only if it does continue with a deeper semantic analysis of the animation.

### STEP-COMPLIANCE CHECK
- The current step description will be provided in the user message (e.g. “Add a rotating square”, “Create a fading-out caption”, “Render the scene as a video”, etc.).
- Examine the code for the presence of the required objects, method calls, or actions that satisfy that description.

### ANIMATION-QUALITY CHECK (run only when step-compliance is true)
- Scene Inclusion: Are all Mobjects explicitly added to the scene?
- Coordinate Sanity & Placement: Are objects positioned appropriately without unnecessary overlap?
- Animation Logic & Dependencies: Do animations follow a logical sequence?
- Transformations: Do transformations make sense for the Mobject types?
- Timing: Is run_time appropriate? Is the timing of animation adequate enough to pay proper attention to specific parts of the screen.

After analyzing the code using available tools, provide your final evaluation in this exact format:

{format_instructions}
"""

        #         system_prompt = f"""
        # You are a highly specialized Senior Python QA Developer for the Manim Animation Library.

        # Your task is to critically analyze the provided Python code snippet based on the overall scene description and the current animation phase. Your focus is strictly on semantic and functional errors that would prevent a successful, meaningful animation.
        # Do not focus too much on the code since the coding agent has access to the latest documentation and you get working code free of any syntax errors.
        # You can use the available tools: `fetch_summary`, `fetch_code_snippets`, `fetch_docs` to fetch any documentation for review and providing feedback only when required.

        # Evaluation Criteria:

        # 1. Scene Inclusion: Are all Mobjects explicitly added to the scene?
        # 2. Coordinate Sanity & Placement: Are objects positioned appropriately without unnecessary overlap?
        # 3. Animation Logic & Dependencies: Do animations follow a logical sequence?
        # 4. Transformations: Do transformations make sense for the Mobject types?
        # 5. Timing: Is run_time appropriate? Is the timing of animation adequate enough to pay proper attention to specific parts of the screen.
        # 6. Step Compliance: Check whether the current step of the multi-step generation process is interpreted correctly and reflected in the produced code. Although this condition can be loosened for steps like "Render the animation as video", because the actual rendering of manim video is done by running command in the command line.

        # After analyzing the code using available tools, provide your final evaluation in this exact format:

        # {format_instructions}
        # """
        agent = create_agent(
            llm,
            system_prompt=system_prompt,
            middleware=[
                # SummarizationMiddleware(
                #     model="groq:llama-3.1-8b-instant",
                #     max_tokens_before_summary=2000,
                #     messages_to_keep=2,
                # ),
                ModelCallLimitMiddleware(
                    # thread_limit=10,  # Max 10 calls per thread (across runs)
                    run_limit=3,
                    exit_behavior="end",  # Or "error" to raise exception
                ),
                retry_model_middleware,
                ToolRetryMiddleware(
                    max_retries=2,
                    on_failure="return_message",
                    initial_delay=2,
                ),
            ],
            checkpointer=InMemorySaver(),
            tools=[fetch_summary, fetch_code_snippets, fetch_docs],
            # debug=True,
        )
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config={"configurable": {"thread_id": "evaluator"}},
        )
        final_message = result["messages"][-1].content

        try:
            return parser.parse(final_message)
        except:
            # Fallback: use LLM to reformat into structured output
            llm = init_chat_model("groq:meta-llama/llama-4-scout-17b-16e-instruct")
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    format_llm = llm.with_structured_output(EvaluatorAgentOutput)
                    return await format_llm.ainvoke(
                        [
                            (
                                "system",
                                "Convert the following evaluation into the required structure:",
                            ),
                            ("user", final_message),
                        ]
                    )
                except:
                    await asyncio.sleep(2**attempt)
                    if attempt == max_attempts - 1:
                        raise

    try:
        result = await evaluate_with_tools(
            state.query,
            state.current_step_description,
            final_code,
        )
    except Exception as e:
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

    # Older prompt
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
