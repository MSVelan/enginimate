import requests
import uuid

job_uuid = str(uuid.uuid4())

# Submit job
requests.post(
    "http://localhost:8000/trigger-rendering",
    json={
        "uuid": job_uuid,
        "code": """
from manim import *
class HelloWorld(Scene):
    def construct(self):
        text = Text("Hello, World!")
        self.play(Write(text))
        self.wait()
""",
        "scene_name": "HelloWorld",
    },
)

# job_uuid = "b56319a3-221c-47d8-8dc9-f6531337ce37"

# Wait for result (blocks until complete or timeout)
result = requests.get(
    f"http://localhost:8000/render-result/{job_uuid}",
    params={"wait": True, "timeout": 300},
)

print(result.json())
# print(f"Video URL: {result.json()['video_url']}")
