import docker
import os
from typing import Optional

import docker.errors


class DockerSandbox:
    def __init__(self):
        self.client = docker.from_env()
        self.container = None

    def create_container(self):
        try:
            cur_dir = os.path.dirname(__file__)
            image, build_logs = self.client.images.build(
                path=".",
                tag="agent-sandbox",
                rm=True,
                forcerm=True,
                buildargs={},
                dockerfile=os.path.join(cur_dir, "Dockerfile"),
                # decode=True
            )
        except docker.errors.BuildError as e:
            print("Build error logs:", flush=True)
            for log in e.build_log:
                if "stream" in log:
                    print(log["stream"].strip())
            raise

        print("Build successful", flush=True)
        # Create container with security constraints and proper logging
        self.container = self.client.containers.run(
            "agent-sandbox",
            command="tail -f /dev/null",  # Keep container running
            detach=True,
            tty=True,
            # mem_limit="512m",
            # cpu_quota=50000,
            pids_limit=2,
            security_opt=["no-new-privileges"],
            # cap_drop=["ALL"],
            # environment={"HF_TOKEN": os.getenv("HF_TOKEN")},
        )
        print("Container created", flush=True)

    def run_code(self, code: str, cls_name: str = "Enginimate") -> Optional[str]:
        """Runs manim code and returns error if found"""
        if not self.container:
            self.create_container()

        try:
            # Write to main.py file
            print("Copying code to main.py...", flush=True)
            self.container.exec_run(cmd=[code, ">", "main.py"], user="bot")
            # Execute code in container
            print("Running manim -ql main.py Enginimate", flush=True)
            self.container.exec_run(
                cmd=["manim", "-ql", "main.py", cls_name], user="bot"
            )
            print("Successful execution of manim code", flush=True)
        except docker.errors.APIError as e:
            print("Error logs while running:", flush=True)
            print(str(e), flush=True)
            raise
        except Exception as e:  # mostly raises docker.errors.ApiError
            raise

        # Collect all output
        # return exec_result.output.decode() if exec_result.output else None

        return None

    def cleanup(self):
        if self.container:
            try:
                self.container.stop()
            except docker.errors.NotFound:
                # Container already removed, this is expected
                pass
            except Exception as e:
                print(f"Error during cleanup: {e}", flush=True)
            finally:
                self.container = None  # Clear the reference


# Example usage:
# sandbox = DockerSandbox()

# try:
#     # Define your agent code
#     agent_code = """
# import os
# from smolagents import CodeAgent, InferenceClientModel

# # Initialize the agent
# agent = CodeAgent(
#     model=InferenceClientModel(token=os.getenv("HF_TOKEN"), provider="together"),
#     tools=[]
# )

# # Run the agent
# response = agent.run("What's the 20th Fibonacci number?")
# print(response)
# """

#     # Run the code in the sandbox
#     output = sandbox.run_code(agent_code)
#     print(output)

# finally:
#     sandbox.cleanup()
