import asyncio
import os
from time import sleep

import aiohttp
from dotenv import load_dotenv
from langchain.embeddings import Embeddings

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")


async def _make_async_post_request(url, headers, payload, max_retries=3):
    for i in range(max_retries):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    resp = await response.json()
            except Exception as e:
                print(f"Error during POST request: {e}")
                await asyncio.sleep(1)
                if i == max_retries - 1:
                    raise e
        return resp


class HFSpaceWrapper(Embeddings):
    def __init__(self, model="Qwen/Qwen3-Embedding-0.6B"):
        self.model = model
        super().__init__()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = self.get_embedding(texts)
        except:
            return []
        data = resp["data"]  # list of dicts
        return [d["embedding"] for d in data]

    def embed_query(self, text: str) -> list[float]:
        try:
            resp = self.get_embedding(text)
        except:
            return []
        data = resp["data"][0]  # dict
        return data["embedding"]

    def get_embedding(self, input: str | list):
        url = "https://msvelan-code-embedding-model.hf.space/v1/embeddings"
        # Model accepts any sentence-transformer input
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {HF_TOKEN}",
        }
        payload = {
            "model": self.model,
            "input": input,
        }

        out = asyncio.run(_make_async_post_request(url, headers, payload))
        # out = await self._make_async_post_request(url, headers, payload)
        return out
