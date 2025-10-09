from __future__ import annotations

import os
from typing import Optional

import httpx
from fastmcp import FastMCP


NODE_BASE_URL = os.getenv("NODE_BASE_URL", "http://localhost:3000")

app = FastMCP("whatsapp-mcp")


def _normalize_to(recipient: str) -> str:
    if recipient.endswith("@c.us") or recipient.endswith("@g.us"):
        return recipient
    digits = "".join(ch for ch in recipient if ch.isdigit())
    return f"{digits}@c.us" if digits else recipient

async def _fetch_recent_messages(to: Optional[str] = None, chatId: Optional[str] = None, limit: int = 10) -> dict:
    params = {}
    if chatId:
        params["chatId"] = chatId
    if to and not chatId:
        params["to"] = _normalize_to(to)
    if limit:
        params["limit"] = str(max(1, min(int(limit), 50)))

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(f"{NODE_BASE_URL}/mcp/get_recent_messages", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            try:
                return e.response.json()
            except Exception:
                return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
def _normalize_conversation(messages: list[dict], me_id_predicate) -> list[dict]:
    normalized: list[dict] = []
    for m in messages:
        speaker = "me" if me_id_predicate(m) else "them"
        normalized.append({
            "role": speaker,
            "text": m.get("body"),
            "timestamp": m.get("timestamp"),
            "fromMe": bool(m.get("fromMe")),
            "from": m.get("from"),
            "to": m.get("to"),
        })
    return normalized



@app.tool()
async def send_message(to: str, text: Optional[str] = None, message: Optional[str] = None, include_context: bool = True) -> dict:
    """Send a WhatsApp message. Provide `to` (phone or WhatsApp ID) and either `text` or `message`.
    If `include_context` is true, also return the last 5 text messages from this chat."""
    body_text = text if text is not None else message
    if not to or not body_text:
        return {"ok": False, "error": "Missing required fields: to, text"}

    normalized_to = _normalize_to(to)

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(
                f"{NODE_BASE_URL}/mcp/send_message",
                json={"to": normalized_to, "text": body_text},
            )
            resp.raise_for_status()
            send_result = resp.json()

            context_result: Optional[dict] = None
            if include_context:
                try:
                    ctx_resp = await client.get(
                        f"{NODE_BASE_URL}/mcp/get_recent_messages",
                        params={"to": normalized_to, "limit": "5"},
                    )
                    if ctx_resp.is_success:
                        context_result = ctx_resp.json()
                    else:
                        # Best-effort; do not fail send if context fetch fails
                        context_result = {"ok": False, "error": f"HTTP {ctx_resp.status_code}"}
                except Exception as e_ctx:
                    context_result = {"ok": False, "error": str(e_ctx)}

            # Provide a simple normalized view with roles me/them when context is available
            normalized_context = None
            try:
                if context_result and context_result.get("ok") and isinstance(context_result.get("messages"), list):
                    # In whatsapp-web.js, messages from me have fromMe=true
                    normalized_context = _normalize_conversation(context_result["messages"], lambda m: bool(m.get("fromMe")))
            except Exception:
                normalized_context = None

            return {"ok": True, "send": send_result, "contextLast5": context_result, "conversation": normalized_context}
        except httpx.HTTPStatusError as e:
            try:
                return e.response.json()
            except Exception:
                return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


@app.tool()
async def get_recent_messages(to: Optional[str] = None, chatId: Optional[str] = None, limit: int = 10) -> dict:
    """Get latest N text messages for a chat. Provide `to` (phone/id) or `chatId`."""
    return await _fetch_recent_messages(to=to, chatId=chatId, limit=limit)


@app.tool()
async def get_conversation(to: Optional[str] = None, chatId: Optional[str] = None, limit: int = 10) -> dict:
    """Get a normalized conversation view with roles me/them for a chat."""
    base = await _fetch_recent_messages(to=to, chatId=chatId, limit=limit)
    if not base.get("ok"):
        return base
    try:
        messages = base.get("messages", [])
        conversation = _normalize_conversation(messages, lambda m: bool(m.get("fromMe")))
        return {"ok": True, "chatId": base.get("chatId"), "messages": messages, "conversation": conversation}
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    # Run FastMCP server. By default binds to localhost:3001; configure via env if needed.
    app.run()
