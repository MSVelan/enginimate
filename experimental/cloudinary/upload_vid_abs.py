# Set your Cloudinary credentials
# ==============================
from dotenv import load_dotenv

load_dotenv()

# Import the Cloudinary libraries
# ==============================
# Import to format the JSON responses
# ==============================
import json

import cloudinary
from cloudinary import CloudinaryVideo

# Set configuration parameter: return "https" URLs by setting secure=True
# ==============================
config = cloudinary.config(secure=True)
print(
    "****1. Set up and configure the SDK:****\nCredentials: ",
    config.cloud_name,
    config.api_key,
    "\n",
)


def uploadVideo():

    # Upload the video and get its URL
    # ==============================

    # Upload the video.
    # Set the asset's public ID and allow overwriting the asset with new versions
    try:
        print("\nUploading...\n")
        result = cloudinary.uploader.upload_large(
            "/home/msvelan/Videos/ShivTandavStotram.mp4",
            resource_type="video",
            eager=[
                {"streaming_profile": "sd", "format": "m3u8"},
            ],
            eager_async=True,
        )
        print("Upload result:\n", json.dumps(result, indent=2), "\n")
        print("\nPlayback URL: ", result["playback_url"], "\n")  # m3u8 URL
    except Exception as e:
        print("Error uploading video:", e)
        return None

    public_id = result["public_id"]
    # Build the URL for the video and save it in the variable 'srcURL'
    srcURL = CloudinaryVideo(public_id).build_url()

    # Log the video URL to the console.
    # Copy this URL in a browser tab to generate the video on the fly.
    print("****2. Uploaded the video****\nDelivery URL: ", srcURL, "\n")
    return public_id


def getAssetInfo(public_id):

    # Get and use details of the video
    # ==============================

    # Get video details and save it in the variable 'video_info'.
    print("Fetching asset info for public_id:", public_id, "\n")
    video_info = cloudinary.api.resource(public_id, resource_type="video")
    print(
        "****3. Get and use details of the video****\nUpload response:\n",
        json.dumps(video_info, indent=2),
        "\n",
    )


def uploadFinalM3U8(
    file="/home/msvelan/Programming/msvelan/projects/python/edugpt/experimental/cloudinary/m3u8-files/final.m3u8",
):
    try:
        print("\nUploading final m3u8 file...\n")
        result = cloudinary.uploader.upload(
            file,
            resource_type="raw",
        )
        print("Final m3u8 upload result:\n", json.dumps(result, indent=2), "\n")
        print("\nFinal m3u8 URL: ", result["secure_url"], "\n")
    except Exception as e:
        print("Error uploading final m3u8 file:", e)


def main():
    public_id = uploadVideo()
    if not public_id:
        return
    getAssetInfo(public_id)


uploadFinalM3U8()
# main()
