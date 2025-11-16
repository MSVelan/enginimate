import asyncio
import logging

from backoff import on_exception
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    SummarizationMiddleware,
    ToolRetryMiddleware,
    wrap_model_call,
)
from langchain.chat_models import init_chat_model
from langchain_cerebras import ChatCerebras
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.checkpoint.memory import InMemorySaver

# from pydantic import BaseModel, Field
from backend.workflow.models.state import State
from backend.workflow.tools.coding_agent_tools import (
    fetch_code_snippets,
    fetch_docs,
    fetch_summary,
)

logger = logging.getLogger(__name__)
# can set logging level with logger.setLevel


# structured output is not available when using tool calls for langchain_groq
# Define the desired structure for the code output
# class PythonCode(BaseModel):
#     """
#     A structure to hold only the generated Python code.
#     The LLM MUST only output the code within this structure.
#     """

#     code: str = Field(
#         description="The complete, runnable Python code as a single string. \
#         MUST NOT include any surrounding text, explanations, or conversational filler."
#     )
# NOTE: can add class name for scene generation here, but kept it static.


@wrap_model_call
async def retry_model_middleware(request, handler):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await handler(request)
        except Exception as e:
            if attempt == max_retries - 1:
                raise  # Re-raise if all retries are exhausted
            logger.warning(
                f"Retrying model call (attempt {attempt + 1}/{max_retries}) after error: {e}"
            )
            await asyncio.sleep(2**attempt)
    return await handler(request)  # Should not be reached if exceptions are re-raised


async def coding_agent(state: State):
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=0.1,  # Allow 0.1 requests per second (1 request every 10 seconds)
        check_every_n_seconds=2,  # Check every 100ms if a request is allowed
        # max_bucket_size=5,  # Allow a burst of up to 5 requests
    )
    # model = init_chat_model("groq:llama-3.1-8b-instant", rate_limiter=rate_limiter)
    model = init_chat_model("groq:qwen/qwen3-32b", rate_limiter=rate_limiter)
    # model = ChatCerebras(model="qwen-3-32b", rate_limiter=rate_limiter)
    # model = init_chat_model(
    #     "qwen-3-32b", model_provider="cerebras", rate_limiter=rate_limiter
    # )
    system_prompt = """
You are a expert Python developer specialized in Manim-CE library. Your sole function 
write python code using Manim-CE library for a given scene generation query. You must 
use a single class for scene generation and the class must be named Enginimate, this 
class inherits the Scene base class. Start writing the python code only when you are 
confident, make use of the tools to fetch required details otherwise. Include the 
required configuration in the code itself if necessary. Please do add descriptive text in
the screen visuals when required.
The complete, runnable Python code as a single string. 
MUST NOT include any surrounding text, explanations, or conversational filler.

Keep the limit argument for tool calls less since each document contains around 1000 tokens.

Task:
1. Add code only for the current phase to the existing code
2. Make sure the text is clearly visible and not out of bounds with appropriate font size
3. Make sure that no Mobjects overlap without any reason.
4. Check your code for common issues:
   - Are all objects added to scene before animating?
   - Are coordinates within bounds (-7 to 7, -4 to 4)?
   - Are animations in logical order?
   - Do transforms make sense?
   - Use the apt time length for the animation
5. Make sure to interpret the current phase logically and incorporate that in the current phase whenever possible.

You must add surrounding Markdown fences (like ```python or ```) around the code.
"""
    logger.info("Coding Agent:")
    agent = create_agent(
        model,
        system_prompt=system_prompt,
        # NOTE: Response format doesn't seem to work with langchain-groq
        # response_format=PythonCode,
        middleware=[
            SummarizationMiddleware(
                model="groq:llama-3.1-8b-instant",
                max_tokens_before_summary=2000,
                messages_to_keep=2,
            ),
            ModelCallLimitMiddleware(
                # thread_limit=10,  # Max 10 calls per thread (across runs)
                run_limit=10,
                exit_behavior="end",  # Or "error" to raise exception
            ),
            retry_model_middleware,
            ToolRetryMiddleware(
                max_retries=2,
                on_failure="return_message",
            ),
        ],
        checkpointer=InMemorySaver(),
        tools=[fetch_summary, fetch_code_snippets, fetch_docs],
        # debug=True,
    )

    query = """
Scene description: {scene_description}
Current Phase: {current_step_description}
Code generated so far:
{code_generated}
Context from manim-ce documentation:
{formatted_docs}
Execution error:
{error}
Feedback:
{feedback}
    """

    template = ChatPromptTemplate.from_messages([("human", query)])

    pipeline = template | agent
    try:
        result = await pipeline.ainvoke(
            {
                "scene_description": state.query,
                "current_step_description": state.current_step_description,
                "code_generated": state.code_generated,
                "formatted_docs": state.formatted_docs,
                "error": state.error,
                "feedback": state.feedback,
            },
            config={"configurable": {"thread_id": "testing"}},
        )
    except Exception as e:
        return {"error_message": str(e)}

    logger.info("Generated code for current step")
    return {
        "code_generated": result["messages"][-1].content,
    }
