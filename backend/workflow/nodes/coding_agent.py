from langchain.agents import create_agent
from langchain.agents.middleware import (
    after_model,
    AgentState,
    ModelCallLimitMiddleware,
    SummarizationMiddleware,
    after_agent,
)
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import HumanMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from backend.workflow.models.state import State
from backend.workflow.utils.sandbox.sandbox_executor import DockerSandbox
from backend.workflow.tools.coding_agent import (
    fetch_code_snippets,
    fetch_docs,
    fetch_summary,
)


# Define the desired structure for the code output
class PythonCode(BaseModel):
    """
    A structure to hold only the generated Python code.
    The LLM MUST only output the code within this structure.
    """

    code: str = Field(
        description="The complete, runnable Python code as a single string. \
        MUST NOT include any surrounding text, explanations, or conversational filler."
    )
    # NOTE: can add class name for scene generation here, but kept it static.


sandbox = DockerSandbox()


@after_agent
def destroy_sandbox(state: AgentState, runtime: Runtime):
    sandbox.cleanup()


@after_model
def code_execution_middleware(state: AgentState, runtime: Runtime):
    if not (
        state["messages"][-1].additional_kwargs.get("tool_calls", None) is None
        or len(state["messages"][-1].additional_kwargs["tool_calls"]) == 0
    ):
        print("Tool call generated")
        return None

    pycode = state["messages"][-1].content
    print("Code Generated:")
    print(pycode)
    err = None
    try:
        sandbox.run_code(pycode)
    except Exception as e:
        print("Received error from server")
        err = str(e)
        print(err)
    print("No errors from server")
    if err is not None:
        return {"messages": [HumanMessage(err)]}
    return {"messages": [HumanMessage("Code execution successful: No errors")]}


def coding_agent(state: State):
    model = init_chat_model("groq:openai/gpt-oss-120b")
    system_prompt = """
You are a expert Python developer specialized in Manim-CE library. Your sole function \
write python code using Manim-CE library for a given scene generation query. You must \
use a single class for scene generation and the class must be named Enginimate, this \
class inherits the Scene base class. Do not use self.wait() at the end of construct \
method of the Enginimate class.
The complete, runnable Python code as a single string. \
MUST NOT include any surrounding text, explanations, or conversational filler.
    """
    agent = create_agent(
        model,
        system_prompt=system_prompt,
        # NOTE: Response format doesn't seem to work with langchain-groq
        # response_format=PythonCode,
        middleware=[
            SummarizationMiddleware(
                model="groq:llama-3.1-8b-instant",
                max_tokens_before_summary=4000,
                # messages_to_keep=20,
            ),
            ModelCallLimitMiddleware(
                # thread_limit=10,  # Max 10 calls per thread (across runs)
                run_limit=5,  # Max 5 calls per run (single invocation)
                exit_behavior="end",  # Or "error" to raise exception
            ),
            code_execution_middleware,
            destroy_sandbox,
        ],
        checkpointer=InMemorySaver(),
        tools=[fetch_summary, fetch_code_snippets, fetch_docs],
        debug=True,
    )

    query = """
Query: {current_step_description}
Code generated so far:
{code_generated}
Context from manim-ce documentation:
{formatted_docs}
Feedback:
{feedback}
    """

    template = ChatPromptTemplate.from_messages([("human", query)])

    pipeline = template | agent
    result = pipeline.invoke(
        {
            "current_step_description": state["current_step_description"],
            "code_generated": state["code_generated"],
            "formatted_docs": state["formatted_docs"],
            "feedback": state["feedback"],
        },
        config={"configurable": {"thread_id": "testing"}},
    )

    # return {"code_generated": result.code}
    return {"code_generated": result["messages"][-2].content}
