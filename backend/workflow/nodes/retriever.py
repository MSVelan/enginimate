from backend.workflow.models.state import State
from backend.workflow.utils.retrieve import retrieve_docs


async def retriever(state: State):
    def format_retrieved_docs(docs):
        content = ""
        for i, (doc, score) in enumerate(docs, 1):
            content += "=" * 30 + f"Block {i}" + "=" * 30 + "\n"
            content += f"Relevance Score: {score}\n\n"
            content += doc.page_content + "\n"
            content += "\nMetadata:\n"
            for k, v in doc.metadata.items():
                content += f"{k}: {v}\n"
        return content

    docs = await retrieve_docs(state.query, k_summary=1)
    return {"formatted_docs": format_retrieved_docs(docs)}
