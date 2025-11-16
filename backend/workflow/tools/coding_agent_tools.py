from langchain.tools import tool

from backend.workflow.utils.retrieve import format_retrieved_docs, retrieve_docs


@tool
async def fetch_code_snippets(query: str, limit: int = 3):
    """Search the manim documentation for code snippets matching the query.

    Args:
        query: Search terms to look for code snippets
        limit: Maximum number of langchain Document objects(chunks) to return
    """
    docs = await retrieve_docs(query, k_code=limit, k_doc=0, k_summary=0)
    return format_retrieved_docs(docs)


@tool
async def fetch_docs(query: str, limit: int = 3):
    """Search the manim documentation for documentation matching the query.

    Args:
        query: Search terms to look for
        limit: Maximum number of langchain Document objects(chunks) to return
    """
    docs = await retrieve_docs(query, k_code=0, k_doc=limit, k_summary=0)
    return format_retrieved_docs(docs)


@tool
async def fetch_summary(query: str, limit: int = 3):
    """Search the manim documentation for API Documentation matching the query.

    Args:
        query: Search terms to look for the specific API
        limit: Maximum number of langchain Document objects(chunks) to return
    """
    docs = await retrieve_docs(query, k_code=0, k_doc=0, k_summary=limit)
    return format_retrieved_docs(docs)
