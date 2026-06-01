import dataclasses
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Header

from app.core.checker import run_checks
from app.core.parser import parse
from app.models.result import Severity

router = APIRouter()


def _report_to_dict(report):
    d = dataclasses.asdict(report)
    for r in d["results"]:
        if isinstance(r.get("severity"), Severity):
            r["severity"] = r["severity"].value
    d["passed"] = report.passed
    d["error_count"] = report.error_count
    d["warning_count"] = report.warning_count
    return d


def _save_history(token: str, filename: str, report, results: list) -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        return
    try:
        from supabase import create_client
        client = create_client(url, key)
        user_id = client.auth.get_user(jwt=token).user.id
        client.postgrest.auth(token)
        client.table("check_history").insert({
            "user_id": user_id,
            "source_file": filename,
            "passed": report.passed,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "results": results,
        }).execute()
    except Exception:
        pass  # Never fail the check because of a history write error


@router.post("/check")
async def check_netlist(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    if not file.filename.endswith(".net"):
        raise HTTPException(status_code=400, detail="Only .net files are accepted")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    try:
        netlist = parse(text)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Parse error: {exc}")

    report = run_checks(netlist, source_file=file.filename)
    result_dict = _report_to_dict(report)

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        _save_history(token, file.filename, report, result_dict["results"])

    return result_dict
