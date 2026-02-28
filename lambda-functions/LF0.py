import json
import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lex = boto3.client("lexv2-runtime")

BOT_ID = os.environ.get("LEX_BOT_ID", "").strip()
BOT_ALIAS_ID = os.environ.get("LEX_BOT_ALIAS_ID", "").strip()
LOCALE_ID = os.environ.get("LEX_LOCALE_ID", "en_US").strip()


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }


def _resp(status, body_obj):
    return {
        "statusCode": status,
        "headers": _cors_headers(),
        "body": json.dumps(body_obj)
    }


def _safe_json_loads(s):
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}


def lambda_handler(event, context):
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return _resp(200, {"ok": True})

    if not BOT_ID or not BOT_ALIAS_ID or not LOCALE_ID:
        return _resp(500, {
            "messages": [{
                "type": "unstructured",
                "unstructured": {"text": "Server misconfiguration: Lex bot/alias/locale not set in LF0 env vars."}
            }]
        })

    body = _safe_json_loads(event.get("body"))

    # Expected body format from your frontend:
    # { sessionId: "...", messages: [{type:"unstructured", unstructured:{text:"..."}}] }
    session_id = (body.get("sessionId") or "").strip()
    messages = body.get("messages") or []

    user_text = ""
    if isinstance(messages, list) and len(messages) > 0:
        m0 = messages[0] or {}
        if m0.get("type") == "unstructured":
            user_text = ((m0.get("unstructured") or {}).get("text") or "").strip()

    if not user_text:
        return _resp(200, {
            "messages": [{
                "type": "unstructured",
                "unstructured": {"text": "Please type a message to continue."}
            }]
        })

    # If frontend didn't send a sessionId, create one
    if not session_id:
        # deterministic-ish fallback
        session_id = f"sess-{context.aws_request_id}"

    try:
        # IMPORTANT: We do NOT pass sessionState or slots here.
        # We let Lex manage the conversation state based on sessionId.
        lex_resp = lex.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=LOCALE_ID,
            sessionId=session_id,
            text=user_text
        )

        # Lex returns "messages": [{contentType:"PlainText", content:"..."}...]
        out = []
        for msg in (lex_resp.get("messages") or []):
            content = (msg.get("content") or "").strip()
            if content:
                out.append({
                    "type": "unstructured",
                    "unstructured": {"text": content}
                })

        # If Lex returned no messages (rare), synthesize something helpful
        if not out:
            # If Lex is waiting for input for a slot, it usually DOES return messages.
            # But keep a safe fallback.
            out.append({
                "type": "unstructured",
                "unstructured": {"text": "Got it. Please continue."}
            })

        return _resp(200, {
            "sessionId": session_id,
            "messages": out
        })

    except Exception as e:
        logger.exception("LF0 error calling Lex: %s", str(e))
        return _resp(500, {
            "sessionId": session_id,
            "messages": [{
                "type": "unstructured",
                "unstructured": {"text": "Oops, something went wrong. Please try again."}
            }]
        })
