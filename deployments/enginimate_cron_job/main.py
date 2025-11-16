import os

import cloudinary
import cloudinary.uploader
import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


origins = ["https://api.cron-job.org"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
)


def _get_connection_string():
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT")

    conn_string = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_HOST}"
        f":{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    return conn_string


@app.get("/trigger-job")
async def trigger_job():
    """
    Takes public id from RENDER_TABLE for last 0.5 hour
    and deletes them from cloudinary
    """
    conn_string = _get_connection_string()
    try:
        public_ids = []
        with psycopg.connect(conn_string) as conn:
            RENDER_TABLE = os.getenv("RENDER_TABLE")
            with conn.cursor() as cur:
                # get public-ids in last 0.5 hours
                query = f"""
                SELECT public_id FROM {RENDER_TABLE}
                WHERE completed_at > NOW() - INTERVAL '30 minutes';
                """
                cur.execute(query)
                rows = cur.fetchall()
                for row in rows:
                    public_ids.append(row[0])
        for public_id in public_ids:
            cloudinary.uploader.destroy(public_id, resource_type="video")
    except Exception as e:
        print("Error occurred in cron-job execution:", str(e))
