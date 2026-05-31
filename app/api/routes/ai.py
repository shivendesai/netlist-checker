import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ai")

_SYSTEM_PROMPT = (
    "You are an expert PCB and electronics engineer assistant embedded in a netlist checker tool. "
    "The user has just run automated checks on their KiCad netlist. You have full context of their "
    "design and check results. Be specific, practical, and concise. Reference their actual component "
    "names, net names, and specific errors when answering. Help them understand and fix issues in "
    "their schematic."
)


class _Context(BaseModel):
    source_file: str = ""
    results: list[dict[str, Any]] = []


class ChatRequest(BaseModel):
    message: str
    context: _Context = _Context()


@router.post("/chat")
async def ai_chat(req: ChatRequest):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI assistant not configured (no API key)")

    user_content = _build_user_message(req.message, req.context)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                },
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"AI service error {resp.status_code}")

    return {"reply": resp.json()["choices"][0]["message"]["content"]}


def _build_user_message(message: str, ctx: _Context) -> str:
    lines = [f"Netlist file: {ctx.source_file or 'unknown'}"]
    if ctx.results:
        passed = sum(1 for r in ctx.results if r.get("passed"))
        lines.append(f"Checks: {len(ctx.results)} total, {passed} passed\n")
        lines.append("Results:")
        for r in ctx.results:
            status = "PASS" if r.get("passed") else r.get("severity", "?").upper()
            line = f"  [{status}] {r.get('check_id', '')}: {r.get('message', '')}"
            if r.get("component"):
                line += f" (component: {r['component']})"
            if r.get("net"):
                line += f" (net: {r['net']})"
            if not r.get("passed") and r.get("suggestion"):
                line += f"\n    Fix: {r['suggestion']}"
            lines.append(line)
    lines.append(f"\nUser question: {message}")
    return "\n".join(lines)
