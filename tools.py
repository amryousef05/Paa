"""Tool declarations (for Gemini) + implementations.

READ_TOOLS run immediately. ACTION_TOOLS only run after explicit user confirmation.
Functions marked STUB need a real provider integration (see README).
"""
import os

import httpx

SERPER_KEY = os.getenv("SERPER_API_KEY", "")
PLACES_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
WA_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
VAPI_KEY = os.getenv("VAPI_API_KEY", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
VAPI_PHONE_ID = os.getenv("VAPI_PHONE_NUMBER_ID", "")
N8N_BASE = os.getenv("N8N_WEBHOOK_BASE", "")  # e.g. https://n8n.example.com/webhook

HTTP = httpx.Client(timeout=20)


# ---------------------------------------------------------------- READ tools
def search_web(query: str, num: int = 6) -> dict:
    """Serper.dev Google search (prices, products, Facebook pages via 'site:')."""
    r = HTTP.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_KEY},
        json={"q": query, "gl": "eg", "hl": "ar", "num": num},
    )
    r.raise_for_status()
    d = r.json()
    return {
        "results": [
            {"title": o.get("title"), "link": o.get("link"), "snippet": o.get("snippet")}
            for o in d.get("organic", [])[:num]
        ]
    }


def search_shopping(query: str, num: int = 6) -> dict:
    """Serper Shopping: compare product prices across Egyptian stores."""
    r = HTTP.post(
        "https://google.serper.dev/shopping",
        headers={"X-API-KEY": SERPER_KEY},
        json={"q": query, "gl": "eg", "hl": "ar", "num": num},
    )
    r.raise_for_status()
    return {
        "products": [
            {
                "title": p.get("title"), "price": p.get("price"),
                "source": p.get("source"), "rating": p.get("rating"),
                "reviews": p.get("ratingCount"), "link": p.get("link"),
            }
            for p in r.json().get("shopping", [])[:num]
        ]
    }


def search_places(query: str, min_rating: float = 4.0, open_now: bool = False) -> dict:
    """Google Places API (New) Text Search, biased to Egypt."""
    r = HTTP.post(
        "https://places.googleapis.com/v1/places:searchText",
        headers={
            "X-Goog-Api-Key": PLACES_KEY,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,places.rating,"
                "places.userRatingCount,places.priceLevel,places.nationalPhoneNumber,"
                "places.googleMapsUri,places.regularOpeningHours.openNow"
            ),
        },
        json={
            "textQuery": query, "languageCode": "ar", "regionCode": "EG",
            "minRating": min_rating, "openNow": open_now, "pageSize": 8,
        },
    )
    r.raise_for_status()
    return {
        "places": [
            {
                "place_id": p.get("id"),
                "name": p.get("displayName", {}).get("text"),
                "address": p.get("formattedAddress"),
                "rating": p.get("rating"),
                "reviews_count": p.get("userRatingCount"),
                "phone": p.get("nationalPhoneNumber"),
                "maps_url": p.get("googleMapsUri"),
            }
            for p in r.json().get("places", [])
        ]
    }


def check_availability(kind: str, venue: str, date: str) -> dict:
    """STUB: slots for padel/cinema/restaurant.
    Route to a venue adapter via n8n (API/booking-system) when available;
    otherwise return {'bookable_online': False} so the agent offers WhatsApp/voice."""
    if not N8N_BASE:
        return {"bookable_online": False, "note": "no provider connected for this venue"}
    r = HTTP.post(f"{N8N_BASE}/availability", json={"kind": kind, "venue": venue, "date": date})
    r.raise_for_status()
    return r.json()


# -------------------------------------------------------------- ACTION tools
def book_slot(kind: str, venue: str, date: str, time: str, party_size: int,
              customer_name: str, customer_phone: str) -> dict:
    """STUB: book via n8n workflow that wraps the venue's API/booking system."""
    r = HTTP.post(f"{N8N_BASE}/book", json=locals())
    r.raise_for_status()
    return r.json()


def send_whatsapp_message(to_phone: str, message: str) -> dict:
    """WhatsApp Cloud API. NOTE: first business-initiated message to a venue must
    use an approved template; free-form text works only inside a 24h window."""
    r = HTTP.post(
        f"https://graph.facebook.com/v21.0/{WA_PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        json={
            "messaging_product": "whatsapp", "to": to_phone.lstrip("+"),
            "type": "text", "text": {"body": message},
        },
    )
    r.raise_for_status()
    return {"sent": True, "id": r.json()["messages"][0]["id"]}


def call_venue_with_ai(to_phone: str, purpose: str, details: str) -> dict:
    """Vapi outbound call. The assistant (configured in Vapi dashboard, Arabic voice)
    receives the task via assistantOverrides variableValues."""
    r = HTTP.post(
        "https://api.vapi.ai/call",
        headers={"Authorization": f"Bearer {VAPI_KEY}"},
        json={
            "assistantId": VAPI_ASSISTANT_ID,
            "phoneNumberId": VAPI_PHONE_ID,
            "customer": {"number": to_phone},
            "assistantOverrides": {"variableValues": {"purpose": purpose, "details": details}},
        },
    )
    r.raise_for_status()
    return {"call_id": r.json().get("id"), "status": "started"}


def add_calendar_event(title: str, start_iso: str, end_iso: str, location: str = "") -> dict:
    """STUB: Google Calendar events.insert with the user's OAuth token
    (scope calendar.events). Implement via google-api-python-client."""
    if N8N_BASE:
        r = HTTP.post(f"{N8N_BASE}/calendar", json=locals())
        r.raise_for_status()
        return r.json()
    return {"created": False, "note": "calendar not connected"}


def create_payment_link(amount_egp: float, description: str) -> dict:
    """STUB: Paymob/Fawry payment link. Money must flow to the venue/merchant, not you,
    unless you hold the proper licenses."""
    r = HTTP.post(f"{N8N_BASE}/payment-link", json=locals())
    r.raise_for_status()
    return r.json()


# ------------------------------------------------------------------ registry
READ_TOOLS = {
    "search_web": search_web,
    "search_shopping": search_shopping,
    "search_places": search_places,
    "check_availability": check_availability,
}
ACTION_IMPL = {
    "book_slot": book_slot,
    "send_whatsapp_message": send_whatsapp_message,
    "call_venue_with_ai": call_venue_with_ai,
    "add_calendar_event": add_calendar_event,
    "create_payment_link": create_payment_link,
}
ACTION_TOOLS = set(ACTION_IMPL)


def summarize_action(name: str, a: dict) -> str:
    if name == "book_slot":
        return f"حجز {a.get('kind')} في {a.get('venue')} يوم {a.get('date')} الساعة {a.get('time')} لعدد {a.get('party_size')}"
    if name == "send_whatsapp_message":
        return f"رسالة واتساب إلى {a.get('to_phone')}: {a.get('message')}"
    if name == "call_venue_with_ai":
        return f"مكالمة بالذكاء الاصطناعي إلى {a.get('to_phone')} بخصوص: {a.get('purpose')}"
    if name == "add_calendar_event":
        return f"إضافة موعد \"{a.get('title')}\" في {a.get('start_iso')}"
    if name == "create_payment_link":
        return f"رابط دفع بمبلغ {a.get('amount_egp')} جنيه: {a.get('description')}"
    return name


# ------------------------------------------------- Gemini function declarations
def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


S = {"type": "string"}
DECLARATIONS = [
    {"name": "search_web", "description": "بحث جوجل في مصر: أسعار، منتجات، صفحات فيسبوك، معلومات عامة.",
     "parameters": _obj({"query": S}, ["query"])},
    {"name": "search_shopping", "description": "مقارنة أسعار منتج في المتاجر المصرية.",
     "parameters": _obj({"query": S}, ["query"])},
    {"name": "search_places", "description": "بحث أماكن على خرائط جوجل (مطاعم، ملاعب، عيادات، مراكز) مع التقييم والعنوان والتليفون.",
     "parameters": _obj({"query": {"type": "string", "description": "مثال: ملاعب بادل في التجمع الخامس"},
                         "min_rating": {"type": "number"}, "open_now": {"type": "boolean"}}, ["query"])},
    {"name": "check_availability", "description": "المواعيد المتاحة لملعب/سينما/مطعم في تاريخ معين.",
     "parameters": _obj({"kind": {"type": "string", "enum": ["padel", "cinema", "restaurant"]},
                         "venue": S, "date": {"type": "string", "description": "YYYY-MM-DD"}},
                        ["kind", "venue", "date"])},
    {"name": "book_slot", "description": "تنفيذ حجز فعلي (بعد تأكيد المستخدم).",
     "parameters": _obj({"kind": {"type": "string", "enum": ["padel", "cinema", "restaurant"]},
                         "venue": S, "date": S, "time": {"type": "string", "description": "HH:MM"},
                         "party_size": {"type": "integer"}, "customer_name": S, "customer_phone": S},
                        ["kind", "venue", "date", "time", "party_size", "customer_name", "customer_phone"])},
    {"name": "send_whatsapp_message", "description": "إرسال رسالة واتساب لمكان للاستفسار أو الحجز.",
     "parameters": _obj({"to_phone": {"type": "string", "description": "بصيغة دولية +20..."}, "message": S},
                        ["to_phone", "message"])},
    {"name": "call_venue_with_ai", "description": "مكالمة صوتية بالذكاء الاصطناعي لمكان مفيهوش حجز إلكتروني.",
     "parameters": _obj({"to_phone": S, "purpose": S, "details": S}, ["to_phone", "purpose", "details"])},
    {"name": "add_calendar_event", "description": "إضافة موعد في Google Calendar.",
     "parameters": _obj({"title": S, "start_iso": S, "end_iso": S, "location": S}, ["title", "start_iso", "end_iso"])},
    {"name": "create_payment_link", "description": "تجهيز رابط دفع للتأكيد.",
     "parameters": _obj({"amount_egp": {"type": "number"}, "description": S}, ["amount_egp", "description"])},
]
