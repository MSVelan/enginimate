from backend.workflow.models.state import State
from backend.workflow.utils.retrieve import retrieve_docs, format_retrieved_docs


async def retriever(state: State):
    code_prompt = state["prompts"].code_prompt
    documentation_prompt = state["prompts"].documentation_prompt
    summary_prompt = state["prompts"].summary_prompt
    code_docs = await retrieve_docs(code_prompt, k_doc=0, k_summary=0)
    documentation_docs = await retrieve_docs(
        documentation_prompt, k_code=0, k_summary=0
    )
    summary_docs = await retrieve_docs(summary_prompt, k_code=0, k_doc=0)
    return {
        "formatted_docs": format_retrieved_docs(
            code_docs + documentation_docs + summary_docs
        )
    }
