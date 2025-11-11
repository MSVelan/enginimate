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
                    return resp
            except Exception as e:
                print(f"Error during POST request: {e}")
                await asyncio.sleep(1)
                if i == max_retries - 1:
                    raise e


class CustomEmbedding(Embeddings):
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


class ManimExecutor:
    def __init__(self, uuid="dummy"):
        self.uuid = uuid
        self.base_url = "https://msvelan-code-executor-manim.hf.space/"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {HF_TOKEN}",
        }

    def test_code(self, code):
        """Executes code and returns error on execution if found"""
        url = self.base_url + "test-code"
        payload = {"uuid": self.uuid, "code": code}
        try:
            out = asyncio.run(_make_async_post_request(url, self.headers, payload))
        except:
            raise
        return out.get("error", None)

    def run_and_upload(self, code):
        """Executes code and uploads video to cloudinary
        - Currently doesn't work because HF spaces have ephemeral storage.
        """
        url = self.base_url + "run-and-upload"
        payload = {"uuid": self.uuid, "code": code}
        try:
            out = asyncio.run(_make_async_post_request(url, self.headers, payload))
        except:
            raise
        return out.get("url", None)

    def cleanup(self):
        """Executes code and returns error on execution if found"""
        url = self.base_url + "cleanup"
        payload = {"uuid": self.uuid}
        try:
            out = asyncio.run(_make_async_post_request(url, self.headers, payload))
        except:
            raise


if __name__ == "__main__":

    myexecutor = ManimExecutor("testing")
    code = """
from manim import *


class Enginimate(Scene):
    def construct(self):
        square = Square(side_length=2, color=WHITE)
        circle = Circle(radius=1, color=YELLOW)
        self.add(square, circle)
    """
    err = None
    try:
        err = myexecutor.run_and_upload(code)
    except Exception as e:
        print(repr(e))
    print(err)
