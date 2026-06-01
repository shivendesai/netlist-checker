import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from supabase import create_client

router = APIRouter()


def _make_client(token: str):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    client = create_client(url, key)
    client.postgrest.auth(token)
    return client


def _get_user_id(token: str) -> str:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    try:
        client = create_client(url, key)
        resp = client.auth.get_user(jwt=token)
        return resp.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/history")
def get_history(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.split(" ", 1)[1]
    user_id = _get_user_id(token)
    client = _make_client(token)
    try:
        result = (
            client.table("check_history")
            .select("id, source_file, passed, error_count, warning_count, results, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
