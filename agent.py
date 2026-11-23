"""Core agent loop: Gemini function calling + human-in-the-loop confirmation."""
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

import tools
from prompts import SYSTEM_PROMPT

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_STEPS = 6
TZ = ZoneInfo("Africa/Cairo")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


@dataclass
class Session:
    user_id: str
    history: list = field(default_factory=list)
    pending: dict = field(default_factory=dict)  # action_id -> {name, args, summary}


SESSIONS: dict[str, Session] = {}  # TODO: replace with Redis/Postgres


def get_session(user_id: str) -> Session:
    return SESSIONS.setdefault(user_id, Session(user_id=user_id))


def _config() -> types.GenerateContentConfig:
    now = datetime.now(TZ).strftime("%A %Y-%m-%d %H:%M (Africa/Cairo)")
    return types.GenerateContentConfig(
        system_instruction=f"{SYSTEM_PROMPT}\n\nالتاريخ والوقت دلوقتي: {now}",
        tools=[types.Tool(function_declarations=tools.DECLARATIONS)],
        # We run the loop manually so action tools can be intercepted.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.4,
    )


def _text(resp) -> str:
    parts = resp.candidates[0].content.parts or []
    return "".join(p.text for p in parts if getattr(p, "text", None)).strip()


def _run_loop(session: Session) -> dict:
    new_pending = []
    for _ in range(MAX_STEPS):
        resp = client.models.generate_content(
            model=MODEL, contents=session.history, config=_config()
        )
        content = resp.candidates[0].content
        session.history.append(content)

        calls = [p.function_call for p in (content.parts or []) if p.function_call]
        if not calls:
            return {"reply": _text(resp), "pending_actions": new_pending}

        results = []
        for call in calls:
            args = dict(call.args or {})
            if call.name in tools.ACTION_TOOLS:
                action_id = uuid.uuid4().hex[:10]
                summary = tools.summarize_action(call.name, args)
                session.pending[action_id] = {
                    "name": call.name, "args": args, "summary": summary,
                }
                new_pending.append(
                    {"action_id": action_id, "tool": call.name, "summary": summary}
                )
                out = {"status": "awaiting_user_confirmation", "action_id": action_id}
            else:
                try:
                    out = tools.READ_TOOLS[call.name](**args)
                except Exception as e:  # surface errors to the model, not the user
                    out = {"error": str(e)}
            results.append(
                types.Part.from_function_response(name=call.name, response={"result": out})
            )
        session.history.append(types.Content(role="user", parts=results))

    return {
        "reply": "الموضوع خد وقت أكتر من المتوقع. ممكن توضحلي طلبك تاني باختصار؟",
        "pending_actions": new_pending,
    }


def chat(user_id: str, text: str) -> dict:
    s = get_session(user_id)
    s.history.append(types.Content(role="user", parts=[types.Part(text=text)]))
    return _run_loop(s)


def confirm(user_id: str, action_id: str, approved: bool) -> dict:
    s = get_session(user_id)
    action = s.pending.pop(action_id, None)
    if not action:
        return {"reply": "الإجراء ده مش موجود أو اتنفذ قبل كده.", "pending_actions": []}

    if not approved:
        note = f"[النظام] المستخدم رفض الإجراء: {action['summary']}. اسأله لو عايز بديل."
    else:
        try:
            result = tools.ACTION_IMPL[action["name"]](**action["args"])
            note = f"[النظام] المستخدم وافق واتنفذ: {action['summary']}. النتيجة: {result}"
        except Exception as e:
            note = f"[النظام] التنفيذ فشل: {action['summary']}. السبب: {e}. اعتذر واقترح بديل."
    s.history.append(types.Content(role="user", parts=[types.Part(text=note)]))
    return _run_loop(s)
