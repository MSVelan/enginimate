async def retrieve_docs(user_query, k_code=3, k_doc=2, k_summary=2):
    query = _get_detailed_instruct(user_query)
    code_docs = await _retrieve_docs(query, k=k_code, type="code")
    docstrings = await _retrieve_docs(query, k=k_doc, type="documentation")
    summary_docs = await _retrieve_docs(query, k=k_summary, type="summary")
    return code_docs + docstrings + summary_docs


def format_retrieved_docs(docs):
    content = ""
    for i, (doc, score) in enumerate(docs, 1):
        content += "=" * 15 + f"Block {i}" + "=" * 15 + "\n"
        content += f"Relevance Score: {score}\n\n"
        content += doc.page_content + "\n"
        content += "\nMetadata:\n"
        for k, v in doc.metadata.items():
            content += f"{k}: {v}\n"
    return content


def _get_detailed_instruct(query: str) -> str:
    """Instruct template for Qwen3-Embedding:0.6b embedding model"""
    task_description = """
Given a query, retrieve relevant documents that answer the query
"""
    return f"Instruct: {task_description}\nQuery:{query}"


async def _get_pg_engine():
    import os

    from dotenv import load_dotenv

    load_dotenv()

    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT")

    CONNECTION_STRING = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_HOST}"
        f":{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    from langchain_postgres import PGEngine

    pg_engine = PGEngine.from_connection_string(url=CONNECTION_STRING)
    return pg_engine


async def _retrieve_docs(query, k=3, type="code"):
    """Retrieve documents of specific type for a given query.
    Returns List[Tuple[Document: str, metadata: dict]]: list of Document objects
    with similarity score.
    """
    from langchain_core.documents import Document
    from sqlalchemy import text

    from backend.workflow.utils.HFSpace.hf_space_wrapper import CustomEmbedding

    embed_service = CustomEmbedding()

    pg_engine = await _get_pg_engine()

    query_embedding = embed_service.embed_query(query)
    embedding_str = f"[{','.join(map(str, query_embedding))}]"

    sql_query = """
    select langchain_id, content, embedding, langchain_metadata,
    (embedding <=> CAST(:query_embedding AS vector)) as distance
    from public.manim_docs
    where langchain_metadata->>'type'=:type
    order by distance
    limit :k;
    """

    async with pg_engine._pool.connect() as conn:
        result = await conn.execute(
            text(sql_query), {"query_embedding": embedding_str, "type": type, "k": k}
        )
        rows = result.fetchall()

    docs = []
    for row in rows:
        doc = Document(page_content=row.content, metadata=row.langchain_metadata)
        similarity_score = 1 - row.distance
        docs.append((doc, similarity_score))

    return docs
