"""
Shared interface contracts between engine and ai modules.
Phase 0: fake implementations. Member 3 replaces these with Claude API calls.
"""
from __future__ import annotations
import os


def ai_explain(facts: dict, lang: str) -> str:
    """Explain a recommendation in hi/en. Falls back to template if Claude unavailable."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key and api_key != "your_anthropic_api_key_here":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            lang_name = "Hindi" if lang == "hi" else "English"
            prompt = (
                f"You are DukaanSaathi AI assistant. Explain this business recommendation in {lang_name} "
                f"in 2-3 short sentences for a small shop owner. Keep it simple and actionable.\n"
                f"Facts: {facts}"
            )
            msg = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except Exception:
            pass

    # Template fallback
    weak_day = facts.get("weak_day", "Monday")
    dip_pct = facts.get("dip_pct", 0)
    max_loss = facts.get("max_loss_inr", 0)
    units_cap = facts.get("units_cap", "N/A")
    margin = facts.get("margin_after_pct", 0)

    if lang == "hi":
        return (
            f"{weak_day} ko {dip_pct:.1f}% kam bikri hoti hai. "
            f"Offer de kar is din mein aur customers laao. "
            f"Sirf {units_cap} customers ke liye—max loss ₹{max_loss}, margin {margin:.1f}% rahega."
        )
    return (
        f"Sales drop {dip_pct:.1f}% on {weak_day}. "
        f"Run this offer to attract more footfall. "
        f"Capped at {units_cap} customers — max loss ₹{max_loss}, margin stays {margin:.1f}%."
    )


def ai_make_offer_copy(offer: dict, lang: str) -> dict:
    """Generate WhatsApp / poster copy for an offer."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    items = ", ".join(offer.get("items", ["product"]))
    discount = offer.get("discount_pct", 10)
    price = offer.get("bundle_price") or offer.get("discounted_price", "")

    if api_key and api_key != "your_anthropic_api_key_here":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            lang_name = "Hindi" if lang == "hi" else "English"
            prompt = (
                f"Create WhatsApp Status text and a short poster headline for this offer in {lang_name}:\n"
                f"Products: {items}, Discount: {discount}%, Price: {price}.\n"
                f"Return JSON: {{\"whatsapp\": \"...\", \"headline\": \"...\", \"cta\": \"...\"}}"
            )
            msg = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            import json
            text = msg.content[0].text.strip()
            start = text.find("{")
            return json.loads(text[start:]) if start >= 0 else _template_copy(items, discount, price, lang)
        except Exception:
            pass

    return _template_copy(items, discount, price, lang)


def _template_copy(items, discount, price, lang) -> dict:
    if lang == "hi":
        return {
            "whatsapp": f"🎉 Aaj ka offer: {items} par {discount}% choot!\n"
                        f"Sirf aaj ke liye ₹{price} mein paao.\nJaldi aao, limited stock! 🛍️",
            "headline": f"{discount}% CHOOT — Sirf Aaj!",
            "cta": "Abhi Lao",
        }
    return {
        "whatsapp": f"🎉 Today's offer: {discount}% off on {items}!\n"
                    f"Get it for just ₹{price} today only.\nHurry — limited stock! 🛍️",
        "headline": f"{discount}% OFF — Today Only!",
        "cta": "Grab Now",
    }


def ai_extract_intent(message: str) -> dict:
    """Extract intent from a chat message."""
    message_lower = message.lower()
    if any(w in message_lower for w in ["offer", "discount", "deal"]):
        intent = "get_recommendation"
    elif any(w in message_lower for w in ["sale", "bikri", "revenue"]):
        intent = "get_sales_summary"
    elif any(w in message_lower for w in ["margin", "profit", "munafa"]):
        intent = "get_margin_info"
    elif any(w in message_lower for w in ["weak", "slow", "slow day", "kam bikri"]):
        intent = "get_weak_day"
    else:
        intent = "general_query"
    return {"intent": intent, "confidence": 0.8}


def ai_chat(message: str, lang: str, context: dict = None) -> str:
    """Answer a merchant's question. Falls back to templated response."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key and api_key != "your_anthropic_api_key_here":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            lang_name = "Hindi" if lang == "hi" else "English"
            system = (
                "You are DukaanSaathi AI, a helpful business assistant for small Indian shop owners. "
                f"Answer in {lang_name}. Be concise, practical, and encouraging. "
                "Never invent sales numbers or claim statistical significance. "
                "If asked about data, say you can only see what the merchant has entered."
            )
            msg = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                system=system,
                messages=[{"role": "user", "content": message}],
            )
            return msg.content[0].text.strip()
        except Exception:
            pass

    intent = ai_extract_intent(message)["intent"]
    if lang == "hi":
        responses = {
            "get_recommendation": "Apni dukaan ke liye best offer dekhne ke liye 'Recommendation' section mein jaayein.",
            "get_sales_summary": "Apni bikri ka chart dashboard par dekh sakte hain.",
            "get_margin_info": "Margin calculator mein apne products ka data daalo — ye aapko batayega discount ke baad kitna munafa bachega.",
            "get_weak_day": "Sabse kam bikri wala din 'Dashboard' par dikhta hai.",
            "general_query": "Namaste! Main DukaanSaathi AI hun. Apni dukaan ke baare mein kuch bhi poochh sakte hain.",
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

