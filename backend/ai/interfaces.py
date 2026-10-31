"""
Groq-backed AI helpers: explanations, offer copy, chat, and bill OCR.

Every function degrades to a deterministic local fallback when GROQ_API_KEY
is not configured, so the application never breaks without AI credentials.
"""
from __future__ import annotations
import json
import os
from typing import Optional

DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _api_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def ai_is_configured() -> bool:
    key = _api_key()
    return bool(key) and key not in {"YOUR_GROQ_API_KEY", "your_groq_api_key_here"}


def _chat(
    messages: list[dict],
    *,
    model: Optional[str] = None,
    max_tokens: int = 350,
    temperature: float = 0.3,
    json_mode: bool = False,
) -> Optional[str]:
    """Call Groq and return text, or None on any failure/missing key."""
    if not ai_is_configured():
        return None
    try:
        from groq import Groq

        kwargs = {
            "model": model or os.getenv("GROQ_MODEL", DEFAULT_MODEL),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        completion = Groq(api_key=_api_key()).chat.completions.create(**kwargs)
        return (completion.choices[0].message.content or "").strip()
    except Exception:
        return None


def _lang_name(lang: str) -> str:
    return "Hindi" if lang == "hi" else "English"


def ai_explain(facts: dict, lang: str) -> str:
    """Explain a recommendation in hi/en. Falls back to a template."""
    text = _chat(
        [
            {
                "role": "system",
                "content": (
                    "You are DukaanSaathi AI, a business assistant for small Indian shop owners. "
                    f"Reply in {_lang_name(lang)} in 2-3 short sentences. "
                    "Use only the supplied facts and never invent numbers."
                ),
            },
            {"role": "user", "content": f"Explain this recommendation: {json.dumps(facts, default=str)}"},
        ],
        max_tokens=220,
    )
    if text:
        return text

    weak_day = facts.get("weak_day", "Monday")
    dip_pct = facts.get("dip_pct", 0) or 0
    max_loss = facts.get("max_loss_inr", 0) or 0
    units_cap = facts.get("units_cap")
    margin = facts.get("margin_after_pct", 0) or 0
    cap_text = f"first {units_cap} customers" if units_cap else "a limited number of customers"

    if lang == "hi":
        return (
            f"{weak_day} ko bikri {dip_pct:.1f}% kam hoti hai. "
            f"Offer de kar is din zyada customers laayein. "
            f"Offer sirf {cap_text} ke liye — maximum loss ₹{max_loss}, margin {margin:.1f}% rahega."
        )
    return (
        f"Sales drop {dip_pct:.1f}% on {weak_day}. "
        f"Run this offer to attract more footfall. "
        f"Capped at {cap_text} — max loss ₹{max_loss}, margin stays {margin:.1f}%."
    )


def ai_make_offer_copy(offer: dict, lang: str) -> dict:
    """Generate WhatsApp / poster copy for an offer."""
    items = ", ".join(offer.get("items", ["product"]))
    discount = offer.get("discount_pct", 10)
    price = offer.get("bundle_price") or offer.get("discounted_price", "")

    text = _chat(
        [
            {
                "role": "system",
                "content": (
                    "You write short promotional copy for Indian small shops. "
                    f"Write in {_lang_name(lang)}. Return only JSON with keys "
                    '"whatsapp", "headline", "cta".'
                ),
            },
            {
                "role": "user",
                "content": f"Products: {items}; Discount: {discount}%; Price: {price}",
            },
        ],
        max_tokens=220,
        json_mode=True,
    )
    if text:
        try:
            start = text.find("{")
            data = json.loads(text[start:]) if start >= 0 else {}
            if data.get("whatsapp") and data.get("headline"):
                return {
                    "whatsapp": str(data["whatsapp"]),
                    "headline": str(data["headline"]),
                    "cta": str(data.get("cta", "Visit Now")),
                }
        except Exception:
            pass

    return _template_copy(items, discount, price, lang)


def _template_copy(items, discount, price, lang) -> dict:
    if lang == "hi":
        return {
            "whatsapp": f"Aaj ka offer: {items} par {discount}% choot!\n"
                        f"Sirf aaj ke liye ₹{price} mein paayein.\nJaldi aayein, limited stock!",
            "headline": f"{discount}% CHOOT — Sirf Aaj!",
            "cta": "Abhi Lein",
        }
    return {
        "whatsapp": f"Today's offer: {discount}% off on {items}!\n"
                    f"Get it for just ₹{price} today only.\nHurry — limited stock!",
        "headline": f"{discount}% OFF — Today Only!",
        "cta": "Grab Now",
    }


def ai_extract_intent(message: str) -> dict:
    """Extract intent from a chat message (local, deterministic)."""
    message_lower = message.lower()
    if any(w in message_lower for w in ["offer", "discount", "deal"]):
        intent = "get_recommendation"
    elif any(w in message_lower for w in ["sale", "bikri", "revenue"]):
        intent = "get_sales_summary"
    elif any(w in message_lower for w in ["margin", "profit", "munafa"]):
        intent = "get_margin_info"
    elif any(w in message_lower for w in ["weak", "slow", "kam bikri"]):
        intent = "get_weak_day"
    else:
        intent = "general_query"
    return {"intent": intent, "confidence": 0.8}


def ai_chat(message: str, lang: str, context: Optional[dict] = None) -> str:
    """Answer a merchant's question. Falls back to a templated response."""
    context_line = ""
    if context:
        context_line = f"\nMerchant data (use only these numbers): {json.dumps(context, default=str)}"

    text = _chat(
        [
            {
                "role": "system",
                "content": (
                    "You are DukaanSaathi AI, a helpful business assistant for small Indian shop owners. "
                    f"Answer in {_lang_name(lang)}. Be concise, practical, and encouraging. "
                    "Never invent sales numbers or claim statistical significance. "
                    "If asked about data, only use the merchant data supplied."
                    f"{context_line}"
                ),
            },
            {"role": "user", "content": message},
        ],
        max_tokens=320,
    )
    if text:
        return text

    intent = ai_extract_intent(message)["intent"]
    if lang == "hi":
        responses = {
            "get_recommendation": "Apni dukaan ke liye best offer dekhne ke liye 'Recommendations' section mein jaayein.",
            "get_sales_summary": "Apni bikri ka chart dashboard par dekh sakte hain.",
            "get_margin_info": "Margin calculator mein apne product ka data daalein — ye discount ke baad bacha munafa batayega.",
            "get_weak_day": "Sabse kam bikri wala din 'Dashboard' par dikhta hai.",
            "general_query": "Namaste! Main DukaanSaathi AI hoon. Apni dukaan ke baare mein kuch bhi poochh sakte hain.",
        }
    else:
        responses = {
            "get_recommendation": "Visit the 'Recommendations' section to see the best offer for your shop.",
            "get_sales_summary": "Your sales chart is visible on the Dashboard.",
            "get_margin_info": "Use the Margin Calculator with your product data to see post-discount profit.",
            "get_weak_day": "Your weakest sales day is shown on the Dashboard.",
            "general_query": "Hello! I am DukaanSaathi AI. Ask me anything about your shop.",
        }
    return responses.get(intent, responses["general_query"])


def ai_extract_bill_items(
    image_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> list[dict]:
    """Extract line items from a bill image / PDF using the local OCR pipeline."""
    try:
        from ai.ocr import extract_bill

        result = extract_bill(image_bytes, filename=filename, content_type=content_type)
        return result.get("items", [])
    except Exception:
        return []
