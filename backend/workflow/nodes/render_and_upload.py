import asyncio
import aiohttp
import uuid

from backend.workflow.models.state import State


async def render_and_upload(state: State):
    job_uuid = str(uuid.uuid4())
    try:
        await _make_async_post_request(
            url="https://enginimate-render-service.onrender.com/trigger-rendering",
            headers=None,
            payload={
                "uuid": job_uuid,
                "code": state.code_generated,
                "scene_name": "Enginimate",
            },
        )

        # wait upto 15 mins for completion
        result = await _make_async_get_request(
            url=f"https://enginimate-render-service.onrender.com/render-result/{job_uuid}",
            params={"wait": True, "timeout": 900},
        )
    except Exception as e:
        return {"error_message": str(e)}

    if result.get("video_url") is None:
        return {"error_message": result.get("error")}

    video_url = result["video_url"]
    public_id = result["public_id"]
    return {"url": video_url, "public_id": public_id}


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


async def _make_async_get_request(url, params, max_retries=3):
    for i in range(max_retries):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    resp = await response.json()
                    return resp
            except Exception as e:
                print(f"Error during GET request: {e}")
                await asyncio.sleep(1)
                if i == max_retries - 1:
                    raise e
