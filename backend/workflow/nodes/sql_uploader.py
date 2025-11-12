import psycopg
import os
from dotenv import load_dotenv

from backend.workflow.models.state import State

load_dotenv()


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


async def sql_uploader(state: State):
    conn_string = _get_connection_string()
    try:
        with psycopg.connect(conn_string) as conn:
            RENDER_TABLE = os.getenv("RENDER_TABLE")
            with conn.cursor() as cur:
                # create table
                # client_uuid, query, code_generated, url, public_id
                create_table_query = f"""
                    CREATE TABLE IF NOT EXISTS %s(
                        uuid UUID PRIMARY KEY,
                        query VARCHAR(1000) NOT NULL,
                        code_generated VARCHAR(2000) NOT NULL,
                        url VARCHAR(200),
                        public_id VARCHAR(60)
                    );
                """
                cur.execute(create_table_query, RENDER_TABLE)
                # TODO: return created_at from render_and_upload service and add to state
                insert_query = f"""
                    INSERT INTO %s (uuid, query, code_generated, url, public_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cur.execute(
                    insert_query,
                    (
                        state.uuid,
                        state.query,
                        state.code_generated,
                        state.url,
                        state.public_id,
                    ),
                )
    except Exception as e:
        return {"error_message": str(e)}
