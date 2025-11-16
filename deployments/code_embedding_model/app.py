import logging
from typing import List, Optional, Union

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Embedding API", version="1.0.0")

# Load model at startup
model = None
model_name = None


@app.on_event("startup")
async def startup_event():
    global model, model_name
    logger.info("Loading embedding model...")
    # Default model
    model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    model_name = "Qwen/Qwen3-Embedding-0.6B"
    logger.info("Model loaded successfully!")


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: Optional[str] = "Qwen/Qwen3-Embedding-0.6B"


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[dict]
    model: str
    usage: dict


@app.post("/v1/embeddings")
def create_embeddings(request: EmbeddingRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        local_model = model
        local_model_name = model_name
        if model_name != request.model:
            local_model = SentenceTransformer(request.model)
            logger.info("Loaded model: ", request.model)
            local_model_name = request.model
        # Handle both single string and list of strings
        texts = [request.input] if isinstance(request.input, str) else request.input

        # Generate embeddings
        embeddings = local_model.encode(texts, convert_to_numpy=True)

        # Format response in OpenAI-compatible format
        data = []
        for idx, embedding in enumerate(embeddings):
            data.append(
                {"object": "embedding", "embedding": embedding.tolist(), "index": idx}
            )

        return EmbeddingResponse(
            data=data,
            model=local_model_name,
            usage={
                "prompt_tokens": sum(len(text.split()) for text in texts),
                "total_tokens": sum(len(text.split()) for text in texts),
            },
        )

    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Embedding API is running", "endpoint": "/v1/embeddings"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_name": model_name,
        "model_loaded": model is not None,
    }
