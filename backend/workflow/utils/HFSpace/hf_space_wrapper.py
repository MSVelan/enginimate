import asyncio
import json
import logging
import os

import aiohttp
from dotenv import load_dotenv
from langchain.embeddings import Embeddings

logger = logging.getLogger(__name__)

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
                logger.exception(f"Error during POST request: {e}")
                await asyncio.sleep(1)
                if i == max_retries - 1:
                    raise e


async def _make_async_get_request(url, headers, params=None, max_retries=5):
    for i in range(max_retries):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    resp = await response.json()
                    return resp
            except Exception as e:
                logger.warning(f"Error during GET request: {e}")
                await asyncio.sleep(2**max_retries)
                if i == max_retries - 1:
                    raise e


async def _make_async_get_sse(url, headers, params=None, max_retries=3, timeout=30):
    for i in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    event_name: str | None = None
                    data_chunks: list[str] = []
                    async for line_bytes in response.content:
                        line = line_bytes.decode().strip()
                        if line == "":
                            if event_name and data_chunks:
                                # Join all ``data:`` lines (the spec allows multi‑line data)
                                raw_data = "\n".join(data_chunks)
                                try:
                                    return json.loads(raw_data)
                                except json.JSONDecodeError as exc:
                                    raise ValueError(
                                        f"Failed to decode SSE data as JSON: {raw_data!r}"
                                    ) from exc
                            event_name, data_chunks = None, []

                        if line.startswith("event:"):
                            event_name = line.partition(":")[2].strip()
                        elif line.startswith("data:"):
                            data_chunks.append(line.partition(":")[2].strip())
        except Exception as e:
            logger.warning(f"Error during GET request: {e}")
            await asyncio.sleep(1)
            if i == max_retries - 1:
                raise e


class CustomEmbedding(Embeddings):
    def __init__(self, model="Qwen/Qwen3-Embedding-0.6B"):
        self.model = model
        super().__init__()

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = await self.get_embedding(texts)
        except:
            return []
        data = resp["data"]  # list of dicts
        return [d["embedding"] for d in data]

    async def embed_query(self, text: str) -> list[float]:
        try:
            resp = await self.get_embedding(text)
        except:
            return []
        data = resp["data"][0]  # dict
        return data["embedding"]

    async def get_embedding(self, input: str | list):
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

        out = await _make_async_post_request(url, headers, payload)
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

    async def test_code(self, code):
        """Executes code and returns error on execution if found"""
        url = self.base_url + "trigger-test-code"
        payload = {"uuid": self.uuid, "code": code}
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await _make_async_post_request(url, self.headers, payload)
                break
            except:
                if attempt == max_retries - 1:
                    raise

            # initialize out by sending SSE get request
            # url = self.base_url + f"events/test-code/{self.uuid}"
            # out = await _make_async_get_sse(
            #     url, self.headers | {"Accept": "text/event-stream"}
            # )
            # long polling is enough for this usecase
        for attempt in range(max_retries):
            try:
                out = await _make_async_get_request(
                    url=f"{self.base_url}result/test-code/{self.uuid}",
                    params={"poll_interval": 5, "timeout": 60 * 30},
                    headers=self.headers,
                )
                break
            except:
                if attempt == max_retries - 1:
                    raise
        return (out.get("error_message", ""), out.get("error", None))

    async def run_and_upload(self, code):
        """Executes code and uploads video to cloudinary
        - Currently doesn't work because HF spaces have ephemeral storage.
        """
        url = self.base_url + "run-and-upload"
        payload = {"uuid": self.uuid, "code": code}
        try:
            out = await _make_async_post_request(url, self.headers, payload)
        except:
            raise
        return out.get("url", None)

    async def cleanup(self):
        """Executes code and returns error on execution if found"""
        url = self.base_url + "cleanup"
        payload = {"uuid": self.uuid}
        try:
            await _make_async_post_request(url, self.headers, payload)
        except:
            raise


if __name__ == "__main__":

    async def _demo():
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
            err = await myexecutor.run_and_upload(code)
        except Exception as e:
            print(repr(e))
        print(err)

    asyncio.run(_demo())
