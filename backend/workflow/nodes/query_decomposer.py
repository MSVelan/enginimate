from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

from backend.workflow.models.state_agent_schemas import QueryDecomposerOutput
from backend.workflow.models.state import State


async def query_decomposer(state: State):
    llm = init_chat_model("groq:openai/gpt-oss-20b")

    system_prompt = """You are an expert at RAG systems. Your task is to \
rewrite a query in a clear consise way so that embedding models can \
better understand the query and fetch relevant documents for different types.
"""

    # This should set state["current_step_description"] as well
    query = state.steps[state.completed_steps].description
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{query}"),
        ]
    )

    query_decomposer_llm = llm.with_structured_output(QueryDecomposerOutput)
    pipeline = prompt_template | query_decomposer_llm
    print("Query Decomposer:")
    print(query)
    err = None
    try:
        prompts = await pipeline.ainvoke({"query": query})
    except Exception as e:
        err = repr(e)
    if err is not None:
        return {"error_message": err}
    return {"prompts": prompts, "current_step_description": query}
