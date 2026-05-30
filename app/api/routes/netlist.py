import dataclasses

from fastapi import APIRouter, HTTPException, UploadFile, File

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


@router.post("/check")
async def check_netlist(file: UploadFile = File(...)):
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
    return _report_to_dict(report)
