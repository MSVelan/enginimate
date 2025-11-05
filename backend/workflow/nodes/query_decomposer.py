from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.workflow.models.state import State


class QueryDecomposerOutput(BaseModel):
    code_prompt: str = Field(
        default="",
        description="Clean minimal prompt \
        for fetching relevant code snippets",
    )
    documentation_prompt: str = Field(
        default="",
        description="Clean minimal prompt \
        for fetching relevant documentation",
    )
    summary_prompt: str = Field(
        default="",
        description="Clean minimal prompt for \
        fetching relevant autosummary snippets \
        (summary of class names, functions, methods)",
    )


def query_decomposer(state: State):
    llm = init_chat_model("groq:openai/gpt-oss-20b", temperature=0.7)

    system_prompt = """You are an expert at RAG systems. Your task is to \
    rewrite a query in a clear consise way so that embedding models can \
    better understand the query and fetch relevant documents for different types.
    """

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{query}"),
        ]
    )

    query_decomposer_llm = llm.with_structured_output(QueryDecomposerOutput)
    pipeline = prompt_template | query_decomposer_llm
    prompts = pipeline.invoke({"query": state.query})
    return {"prompts": prompts}
