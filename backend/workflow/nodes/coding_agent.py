from backoff import on_exception
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    SummarizationMiddleware,
)
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import InMemorySaver

# from pydantic import BaseModel, Field

from backend.workflow.models.state import State
from backend.workflow.tools.coding_agent_tools import (
    fetch_code_snippets,
    fetch_docs,
    fetch_summary,
)


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


async def coding_agent(state: State):
    model = init_chat_model("groq:openai/gpt-oss-120b")
    system_prompt = """
You are a expert Python developer specialized in Manim-CE library. Your sole function \
write python code using Manim-CE library for a given scene generation query. You must \
use a single class for scene generation and the class must be named Enginimate, this \
class inherits the Scene base class. Start writing the python code only when you are \
confident, make use of the tools to fetch required details otherwise.
The complete, runnable Python code as a single string. \
MUST NOT include any surrounding text, explanations, or conversational filler.

Task:
1. Add code only for the current phase to the existing code
2. Check your code for common issues:
   - Are all objects added to scene before animating?
   - Are coordinates within bounds (-7 to 7, -4 to 4)?
   - Are animations in logical order?
   - Do transforms make sense?
   - Use the apt time length for the animation
    """
    print("Coding Agent:")
    agent = create_agent(
        model,
        system_prompt=system_prompt,
        # NOTE: Response format doesn't seem to work with langchain-groq
        # response_format=PythonCode,
        middleware=[
            SummarizationMiddleware(
                model="groq:llama-3.1-8b-instant",
                max_tokens_before_summary=4000,
                messages_to_keep=5,
            ),
            ModelCallLimitMiddleware(
                # thread_limit=10,  # Max 10 calls per thread (across runs)
                run_limit=10,
                exit_behavior="end",  # Or "error" to raise exception
            ),
        ],
        checkpointer=InMemorySaver(),
        tools=[fetch_summary, fetch_code_snippets, fetch_docs],
        debug=True,
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

    print("Generated code for current step")
    return {
        "code_generated": result["messages"][-1].content,
    }
