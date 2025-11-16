import os
from typing import Literal

from dotenv import load_dotenv
from IPython.display import Image, display
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from backend.workflow.models.state import State
from backend.workflow.nodes.coding_agent import coding_agent
from backend.workflow.nodes.evaluator import evaluator_agent
from backend.workflow.nodes.query_decomposer import query_decomposer
from backend.workflow.nodes.reasoning_agent import reasoning_agent
from backend.workflow.nodes.render_and_upload import render_and_upload
from backend.workflow.nodes.retriever import retriever
from backend.workflow.nodes.sql_uploader import sql_uploader

load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_KEY")
os.environ["CEREBRAS_API_KEY"] = os.getenv("CEREBRAS_KEY")
os.environ["LANGSMITH_ENDPOINT"] = os.getenv(
    "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
)
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "Enginimate")


def route_on_error(state: State) -> Literal["END", "continue"]:
    if len(state.error_message) != 0:
        return "END"
    return "continue"


def evaluator_agent_route(
    state: State,
) -> Literal["END"] | Literal["retry", "next_step", "continue"]:
    if len(state.error_message) != 0:
        return "END"
    return state.evaluator_next_step


# define nodes and edges
workflow = StateGraph(State)

workflow.add_node("reasoning_agent", reasoning_agent)
workflow.add_node("query_decomposer", query_decomposer)
# workflow.add_node("retriever", retriever)
workflow.add_node("coding_agent", coding_agent)
workflow.add_node("evaluator_agent", evaluator_agent)
workflow.add_node("render_and_upload", render_and_upload)
workflow.add_node("sql_uploader", sql_uploader)

workflow.add_edge(START, "reasoning_agent")
workflow.add_conditional_edges(
    "reasoning_agent", route_on_error, {"END": END, "continue": "query_decomposer"}
)
workflow.add_conditional_edges(
    "query_decomposer", route_on_error, {"END": END, "continue": "coding_agent"}
)
# workflow.add_conditional_edges(
#     "query_decomposer", route_on_error, {"END": END, "continue": "retriever"}
# )
# workflow.add_conditional_edges(
#     "retriever", route_on_error, {"END": END, "continue": "coding_agent"}
# )
workflow.add_conditional_edges(
    "coding_agent",
    route_on_error,
    {"END": END, "continue": "evaluator_agent"},
)
workflow.add_conditional_edges(
    "evaluator_agent",
    evaluator_agent_route,
    {
        "END": END,
        "retry": "coding_agent",
        "next_step": "query_decomposer",
        "continue": "render_and_upload",
    },
)
workflow.add_conditional_edges(
    "render_and_upload",
    route_on_error,
    {"END": END, "continue": "sql_uploader"},
)
workflow.add_conditional_edges(
    "sql_uploader",
    route_on_error,
    {"END": END, "continue": END},
)

# checkpointer = InMemorySaver()
# graph = workflow.compile(checkpointer=checkpointer)
# Don't really need a checkpointer at this point
graph = workflow.compile()

display(Image(graph.get_graph().draw_mermaid_png()))
