"""
api.py - Digest REST API
提供 identity 與 participant 查詢介面給外部服務使用。

端點：
  GET /identity/{identity_id}/participants   查詢 identity 在各 channel 的帳號
  GET /identity/me/participants              查詢 LOGOS_IDENTITY_ID 的帳號
"""

import os
import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ["DB_URL"]
LOGOS_IDENTITY_ID = os.environ.get("LOGOS_IDENTITY_ID", "")


# ── DB ────────────────────────────────────────────────────────────

_pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(DB_URL)
    yield
    await _pool.close()


app = FastAPI(title="Digest API", lifespan=lifespan)


def pool() -> asyncpg.Pool:
    assert _pool is not None
    return _pool


# ── Core（純查詢） ─────────────────────────────────────────────────

async def fetch_participants(identity_id: str) -> list[dict]:
    rows = await pool().fetch(
        """
        SELECT icp.channel, icp.external_id
        FROM identity_channel_participant icp
        JOIN identity i ON i.id = icp.identity_id
        WHERE icp.identity_id = $1
        ORDER BY icp.channel
        """,
        identity_id,
    )
    return [dict(r) for r in rows]


# ── Routes ────────────────────────────────────────────────────────

@app.get("/identity/me/participants")
async def get_my_participants():
    if not LOGOS_IDENTITY_ID:
        raise HTTPException(status_code=503, detail="LOGOS_IDENTITY_ID 未設定")
    return await fetch_participants(LOGOS_IDENTITY_ID)


@app.get("/identity/{identity_id}/participants")
async def get_participants(identity_id: str):
    rows = await fetch_participants(identity_id)
    if not rows:
        raise HTTPException(status_code=404, detail="identity 不存在或無 participant")
    return rows
