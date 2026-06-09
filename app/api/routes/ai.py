import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ai")

_SYSTEM_PROMPT_TEMPLATE = (
    "You are an expert PCB and electronics engineer assistant embedded in a KiCad schematic checker plugin. "
    "The engineer is currently working on a schematic. You have real-time access to their design. "
    "Current components in schematic: {comp_list}\n"
    "Last check results are also provided for context.\n"
    "Be specific, practical, and concise. Reference their actual component names when answering. "
    "Help them understand and fix issues in their schematic."
)


class _Context(BaseModel):
    source_file: str = ""
    current_components: list[dict[str, Any]] = []
    last_save_results: list[dict[str, Any]] = []


class ChatRequest(BaseModel):
    message: str
    context: _Context = _Context()


@router.post("/chat")
async def ai_chat(req: ChatRequest):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI assistant not configured (no API key)")

    # Build system prompt with current component context
    components = req.context.current_components or []
    comp_list = ', '.join([f"{c['ref']} ({c['value']})" for c in components]) if components else 'none'
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(comp_list=comp_list)

    user_content = _build_user_message(req.message, req.context)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_prompt},
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
    lines = [f"Schematic file: {ctx.source_file or 'unknown'}"]

    if ctx.current_components:
        comp_list = ', '.join([f"{c['ref']} ({c['value']})" for c in ctx.current_components])
        lines.append(f"Components placed: {comp_list}")

    if ctx.last_save_results:
        passed = sum(1 for r in ctx.last_save_results if r.get("passed"))
        lines.append(f"\nLast check results: {len(ctx.last_save_results)} total, {passed} passed")
        for r in ctx.last_save_results:
            status = "PASS" if r.get("passed") else r.get("severity", "?").upper()
            line = f"  [{status}] {r.get('check_id', '')}: {r.get('message', '')}"
            if not r.get("passed") and r.get("suggestion"):
                line += f" → {r['suggestion']}"
            lines.append(line)

    lines.append(f"\nQuestion: {message}")
    return "\n".join(lines)
