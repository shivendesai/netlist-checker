import dataclasses
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Header, Request
from pydantic import BaseModel

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


class NetlistPayload(BaseModel):
    netlist: Optional[str] = None
    components: Optional[list] = None
    nets: Optional[list] = None


@router.post("/check")
async def check_netlist(
    request: Request,
    file: Optional[UploadFile] = File(None),
    authorization: Optional[str] = Header(None),
):
    source_file = "unknown"
    netlist = None

    # Check if it's JSON payload
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            payload = NetlistPayload(**body)

            if payload.netlist:
                # JSON with netlist text
                try:
                    netlist = parse(payload.netlist)
                except Exception as exc:
                    raise HTTPException(status_code=422, detail=f"Parse error: {exc}")
                source_file = "schematic.net"
            elif payload.components is not None and payload.nets is not None:
                # JSON with pre-parsed components and nets
                from app.core.parser import Component, Net, Pin, Netlist as NetlistClass
                components = [Component(ref=c["ref"], value=c["value"], footprint=c.get("footprint", "")) for c in payload.components]
                nets = []
                for n in payload.nets:
                    pins = [Pin(ref=p["ref"], number=p["number"]) for p in n.get("pins", [])]
                    nets.append(Net(code=n.get("code", "0"), name=n["name"], pins=pins))
                netlist = NetlistClass(components=components, nets=nets)
                source_file = "schematic.json"
            else:
                raise HTTPException(status_code=400, detail="JSON payload must include 'netlist' or both 'components' and 'nets'")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}")
    elif file:
        # Multipart file upload (original behavior)
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
        source_file = file.filename
    else:
        raise HTTPException(status_code=400, detail="Must provide either JSON body or file upload")

    report = run_checks(netlist, source_file=source_file)
    result_dict = _report_to_dict(report)

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        _save_history(token, source_file, report, result_dict["results"])

    return result_dict
