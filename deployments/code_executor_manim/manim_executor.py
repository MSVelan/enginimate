import os
import shutil
from typing import Optional

import logging
import asyncio

import cloudinary
from cloudinary import CloudinaryVideo

import subprocess


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _initialize_manim_project(pjt_name):
    try:
        subprocess.run(
            f"yes '' | manim init project {pjt_name} --default",
            shell=True,
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        raise Exception(f"{e.returncode}: {e.stderr}")


# on success, creates media/videos/main/1080p60/Enginimate.mp4
async def _uploadVideo(pjt_name):
    cloudinary.config(secure=True)
    url = None
    try:
        logger.info("\nUploading...\n")
        cur_dir = os.path.dirname(__file__)
        file_path = os.path.join(
            pjt_name, "media", "videos", "main", "1080p60", "Enginimate.mp4"
        )
        logger.info("Video path for uploading: " + file_path)
        if os.path.exists(file_path):
            result = cloudinary.uploader.upload_large(
                file_path,
                resource_type="video",
            )
            url = result["secure_url"]
        else:
            raise Exception("video wasnt generated to start uploading")
    except Exception as e:
        logger.error("Error uploading video:", repr(e))
        raise

    return url


async def test_code(pjt_name, code, cls_name="Enginimate") -> Optional[str]:
    """Runs manim code and returns error if found"""
    file_path = os.path.join(pjt_name, "main.py")
    # create project if file not exists
    if not os.path.exists(file_path):
        try:
            _initialize_manim_project(pjt_name)
        except:
            raise
    logger.info("Copying code to main.py...")
    with open(file_path, "w") as f:
        f.write(code)
    logger.info("Running manim -ql main.py Enginimate")
    try:
        subprocess.run(
            args=["manim", "-ql", "main.py", cls_name],
            cwd=pjt_name,
            check=True,
            capture_output=True,
        )
        logger.info("Successful execution of manim code")
    except subprocess.CalledProcessError as e:
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        return e.stderr
    except FileNotFoundError:
        logger.error("File not found")
        raise
    except Exception as e:
        logger.error("Unexpected error: ", repr(e))
        raise
    return ""


async def run_and_upload(pjt_name, code, cls_name="Enginimate") -> Optional[str]:
    """Runs manim code and uploads to cloudinary"""
    file_path = os.path.join(pjt_name, "main.py")
    cur_dir = os.path.dirname(__file__)
    # create project if file not exists
    if not os.path.exists(file_path):
        try:
            _initialize_manim_project(pjt_name)
        except:
            raise
    logger.info("Copying code to main.py...")
    with open(file_path, "w") as f:
        f.write(code)
    logger.info("Running manim -qh main.py Enginimate")
    try:
        subprocess.run(
            args=[
                "manim",
                "render",
                "-qh",
                file_path,
                cls_name,
                "--media_dir=data",
                "--write_to_movie",
                "--format=webm",
            ],
            # cwd=pjt_name,
            cwd=cur_dir,
            check=True,
            capture_output=True,
        )
        logger.info("Successful execution of manim code")
    except subprocess.CalledProcessError as e:
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        raise Exception(e.stderr)
    except FileNotFoundError:
        logger.error("File not found")
        raise
    except Exception as e:
        logger.error("Unexpected error: ", repr(e))
        raise

    # try:
    #     url = await _uploadVideo(pjt_name)
    # except:
    #     raise
    # logger.info("Ran and uploaded video")
    # return url

    # lets try ls -lR . to check if video is created or not.
    # data_dir = os.path.join(pjt_name, "data")
    try:
        result = subprocess.run(
            args=["ls", "-lR", "data"],
            cwd=cur_dir,
            check=True,
            capture_output=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        raise Exception(e.stderr)
    except FileNotFoundError:
        logger.error("File not found")
        raise
    except Exception as e:
        logger.error("Unexpected error: ", repr(e))
        raise


# remove directory containing pjt_name
def cleanup(pjt_name):
    try:
        shutil.rmtree(pjt_name)
    except FileNotFoundError as e:
        pass  # no exception raised
    except Exception as e:
        logger.error(repr(e))
        raise
