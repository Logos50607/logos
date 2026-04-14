"""
api.py - Digest REST API
提供 identity 與 participant 查詢介面給外部服務使用。

端點：
  GET  /identity/{identity_id}/participants  查詢 identity 在各 channel 的帳號
  GET  /identity/me/participants             查詢 LOGOS_IDENTITY_ID 的帳號
  POST /gps                                  接收 Overland GPS 定位（寫入 Postgres）
"""

import math
import os
import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv

load_dotenv()

DB_URL             = os.environ["DB_URL"]
LOGOS_IDENTITY_ID  = os.environ.get("LOGOS_IDENTITY_ID", "")
GPS_IDENTITY_ID    = os.environ.get("GPS_IDENTITY_ID", LOGOS_IDENTITY_ID)
GPS_MIN_DISTANCE_M = float(os.environ.get("GPS_MIN_DISTANCE_M", "50"))
GPS_TOKEN          = os.environ.get("GPS_TOKEN", "")


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
    participants = await fetch_participants(LOGOS_IDENTITY_ID)
    return {"identity_id": LOGOS_IDENTITY_ID, "participants": participants}


@app.get("/identity/{identity_id}/participants")
async def get_participants(identity_id: str):
    rows = await fetch_participants(identity_id)
    if not rows:
        raise HTTPException(status_code=404, detail="identity 不存在或無 participant")
    return rows


# ── GPS（Overland → Postgres） ────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _last_location() -> tuple[float, float] | None:
    row = await pool().fetchrow(
        "SELECT lat, lng FROM location WHERE identity_id = $1 ORDER BY recorded_at DESC LIMIT 1",
        GPS_IDENTITY_ID,
    )
    return (row["lat"], row["lng"]) if row else None


async def _insert_location(lat: float, lng: float) -> None:
    await pool().execute(
        "INSERT INTO location (identity_id, lat, lng) VALUES ($1, $2, $3)",
        GPS_IDENTITY_ID, lat, lng,
    )


async def _touch_location() -> None:
    """沒移動時更新最後一筆的 updated_at，記錄最後確認時間。"""
    await pool().execute(
        """
        UPDATE location SET updated_at = NOW()
        WHERE id = (SELECT id FROM location WHERE identity_id = $1 ORDER BY recorded_at DESC LIMIT 1)
        """,
        GPS_IDENTITY_ID,
    )


@app.post("/gps")
async def receive_gps(request: Request, token: str = ""):
    import json as _json
    body_bytes = await request.body()

    # Overland sends token as "Authorization: Bearer <token>"
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:]

    if GPS_TOKEN and token != GPS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    payload = _json.loads(body_bytes)
    locations = payload.get("locations", [])
    last = await _last_location()
    inserted = 0

    for feat in locations:
        coords = feat.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        lng, lat = float(coords[0]), float(coords[1])

        if last and _haversine(last[0], last[1], lat, lng) < GPS_MIN_DISTANCE_M:
            await _touch_location()
            continue

        await _insert_location(lat, lng)
        last = (lat, lng)
        inserted += 1

    return {"result": "ok", "inserted": inserted}
