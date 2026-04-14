"""
api.py - Digest REST API
提供 identity 與 participant 查詢介面給外部服務使用。

端點：
  GET  /identity/{identity_id}/participants  查詢 identity 在各 channel 的帳號
  GET  /identity/me/participants             查詢 LOGOS_IDENTITY_ID 的帳號
  POST /gps                                  接收 Overland GPS 定位（寫入 Turso）
"""

import math
import os
import asyncpg
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

DB_URL             = os.environ["DB_URL"]
LOGOS_IDENTITY_ID  = os.environ.get("LOGOS_IDENTITY_ID", "")
TURSO_URL          = os.environ.get("TURSO_URL", "")
TURSO_TOKEN        = os.environ.get("TURSO_TOKEN", "")
GPS_IDENTITY_ID    = os.environ.get("GPS_IDENTITY_ID", LOGOS_IDENTITY_ID)
GPS_MIN_DISTANCE_M = float(os.environ.get("GPS_MIN_DISTANCE_M", "50"))


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


# ── GPS（Overland → Turso） ────────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _turso_last_location() -> tuple[float, float] | None:
    """回傳 Turso 中最新一筆位置的 (lat, lng)，無資料回 None。"""
    body = {"requests": [{"type": "execute", "stmt": {
        "sql": "SELECT lat, lng FROM location WHERE identity_id = ? ORDER BY recorded_at DESC LIMIT 1",
        "args": [{"type": "text", "value": GPS_IDENTITY_ID}],
    }}]}
    async with httpx.AsyncClient() as client:
        r = await client.post(TURSO_URL, json=body,
                              headers={"Authorization": f"Bearer {TURSO_TOKEN}"}, timeout=10)
    rows = r.json()["results"][0]["response"]["result"]["rows"]
    if not rows:
        return None
    return float(rows[0][0]["value"]), float(rows[0][1]["value"])


async def _turso_insert(lat: float, lng: float, address: str) -> None:
    body = {"requests": [{"type": "execute", "stmt": {
        "sql": "INSERT INTO location (identity_id, lat, lng, address, recorded_at, updated_at) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
        "args": [
            {"type": "text",  "value": GPS_IDENTITY_ID},
            {"type": "float", "value": lat},
            {"type": "float", "value": lng},
            {"type": "text",  "value": address},
        ],
    }}]}
    async with httpx.AsyncClient() as client:
        r = await client.post(TURSO_URL, json=body,
                              headers={"Authorization": f"Bearer {TURSO_TOKEN}"}, timeout=10)
    if r.json()["results"][0]["type"] != "ok":
        raise RuntimeError(r.text)


async def _turso_touch(lat: float, lng: float) -> None:
    """沒移動時更新最後一筆的 updated_at，記錄最後確認時間。"""
    body = {"requests": [{"type": "execute", "stmt": {
        "sql": "UPDATE location SET updated_at = datetime('now') WHERE id = (SELECT id FROM location WHERE identity_id = ? ORDER BY recorded_at DESC LIMIT 1)",
        "args": [{"type": "text", "value": GPS_IDENTITY_ID}],
    }}]}
    async with httpx.AsyncClient() as client:
        await client.post(TURSO_URL, json=body,
                          headers={"Authorization": f"Bearer {TURSO_TOKEN}"}, timeout=10)


GPS_TOKEN = os.environ.get("GPS_TOKEN", "")


class OverlandPayload(BaseModel):
    locations: list[dict]


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
    if not TURSO_URL or not TURSO_TOKEN:
        raise HTTPException(status_code=503, detail="TURSO_URL / TURSO_TOKEN 未設定")

    payload = OverlandPayload(**_json.loads(body_bytes))
    last = await _turso_last_location()
    inserted = 0

    for feat in payload.locations:
        coords = feat.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        lng, lat = float(coords[0]), float(coords[1])
        address = ""

        if last and _haversine(last[0], last[1], lat, lng) < GPS_MIN_DISTANCE_M:
            await _turso_touch(lat, lng)
            continue

        await _turso_insert(lat, lng, address)
        last = (lat, lng)
        inserted += 1

    return {"result": "ok", "inserted": inserted}
