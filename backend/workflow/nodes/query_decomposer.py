from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter

from backend.workflow.models.state_agent_schemas import QueryDecomposerOutput
from backend.workflow.models.state import State


async def query_decomposer(state: State):
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=0.2,  # Allow 0.2 requests per second (1 request every 5 seconds)
        check_every_n_seconds=2,  # Check every 100ms if a request is allowed
    )
    llm = init_chat_model("groq:llama-3.1-8b-instant", rate_limiter=rate_limiter)
    # llm = init_chat_model("groq:openai/gpt-oss-20b")

    system_prompt = """
You are an expert Query Decomposer and RAG system optimizer. Your task is to take a user's original query and decompose it into three specialized sub-queries.

Each sub-query must be a clean, minimal, and highly focused** statement optimized for a specific type of retrieval model and document corpus. The goal is to maximize the **semantic relevance** of the fetched documents for the final RAG answer.

Decomposition Rules:

1.  Code Query (code_prompt):
    * Goal: Fetch **exact code snippets, class definitions, or function implementations.
    * Refinement: The prompt should be direct and technical. Focus on API names, function signatures, class names, file paths, or specific technical terms. Minimize conversational or contextual language.
    * Example: If the original query is "How do I set up a connection pool in Django?", the code query should be closer to "Django database connection pool configuration settings".*

2.  Documentation Query (documentation_prompt):
    * Goal: Fetch explanatory guides, tutorials, conceptual overviews, or usage examples.
    * Refinement: The prompt should focus on "how-to," "why," or "conceptual understanding". Keep essential keywords but structure the prompt to match the narrative style typically found in documentation.
    * Example: Based on the query above, the documentation query could be "Steps to create and manage a connection pool in Django framework documentation"

3.  Summary Query (summary_prompt):
    * Goal: Fetch high-level, brief summaries of API components (class names, function names, method signatures) to identify the correct component name before fetching the full details.
    * Refinement: The prompt must be extremely short, keyword-rich, and focused only on identifying component names. It should sound like a search for a definition or a list.
    * Example: Based on the query above, the summary query could be "Django methods for initializing database connections"
"""

    # This should set state["current_step_description"] as well
    print("Current step:", state.completed_steps + 1)
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
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            prompts = await pipeline.ainvoke({"query": query})
            break
        except Exception as e:
            if attempt == max_attempts - 1:
                err = repr(e)
    if err is not None:
        return {"error_message": err}
    return {"prompts": prompts, "current_step_description": query}
