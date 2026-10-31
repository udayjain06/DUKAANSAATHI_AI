"""
DukaanSaathi / Paytm AI — Groq Conversational AI Client
Provides fast, intelligent financial guidance in Hindi and English using Groq
LLMs, grounded in the authenticated shopkeeper's real business data.

Environment:
    GROQ_API_KEY   — required to enable the live model
    GROQ_MODEL     — preferred model (falls back automatically)
"""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

# Models confirmed available on the Groq account used by this project.
# The configured GROQ_MODEL is tried first, then these in order.
DEFAULT_MODEL_CHAIN = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "allam-2-7b",
]

MAX_HISTORY_TURNS = 8


def _api_key() -> str:
    return (os.getenv("GROQ_API_KEY") or "").strip()


def _model_chain() -> list[str]:
    preferred = (os.getenv("GROQ_MODEL") or "").strip()
    chain: list[str] = []
    if preferred:
        chain.append(preferred)
    for model in DEFAULT_MODEL_CHAIN:
        if model not in chain:
            chain.append(model)
    return chain


def _currency(value) -> str:
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def _build_context(financial_context: dict | None, lang: str) -> str:
    """Turn the merchant's real metrics into a compact grounding block."""
    if not financial_context:
        return (
            "No business data is available for this merchant yet. "
            "Do not invent numbers — invite them to add products, sales or bills first."
        )

    ctx = financial_context
    shop_name = ctx.get("shop_name") or "this shop"
    shop_type = ctx.get("shop_type") or "retail"
    product_count = int(ctx.get("product_count") or 0)
    has_sales = bool(ctx.get("has_sales") or ctx.get("has_sales_history"))
    tx_count = int(ctx.get("transaction_count") or 0)

    if not has_sales and product_count == 0 and tx_count == 0:
        return (
            f"BUSINESS DATA for {shop_name} ({shop_type}): brand-new account. "
            "Products: 0, Sales: none, Transactions: none. "
            "CRITICAL: Do not fabricate numbers. Tell the merchant to add products in the "
            "Products tab and upload bills / record sales so personalised forecasts unlock."
        )

    lines = [
        f"BUSINESS DATA for {shop_name} ({shop_type}):",
        f"- Active products in catalogue: {product_count}",
        f"- Total recorded revenue: {_currency(ctx.get('total_income'))}",
        f"- Total expenses (ledger): {_currency(ctx.get('total_expense'))}",
        f"- Current balance: {_currency(ctx.get('balance'))}",
        f"- Monthly budget: {_currency(ctx.get('monthly_budget'))}",
        f"- Slowest sales day: {ctx.get('weak_day') or 'still being calculated'}",
    ]

    if ctx.get("weak_day_dip_pct") is not None:
        lines.append(f"- Weak-day dip: {float(ctx['weak_day_dip_pct']):.1f}% vs average")

    if ctx.get("predicted_30_days_total"):
        lines.append(f"- ML forecast (next 30 days spending): {_currency(ctx['predicted_30_days_total'])}")

    if ctx.get("savings_rate_pct") is not None:
        lines.append(f"- Savings rate: {float(ctx['savings_rate_pct']):.1f}%")

    categories = ctx.get("top_categories") or []
    if categories:
        rendered = ", ".join(
            f"{c.get('category')} {_currency(c.get('amount') or c.get('total_amount'))}"
            for c in categories[:4]
        )
        lines.append(f"- Top expense categories: {rendered}")

    trend = ctx.get("monthly_trend") or []
    if trend:
        rendered = ", ".join(
            f"{m.get('label') or m.get('month')}: in {_currency(m.get('income'))} / "
            f"out {_currency(m.get('expense'))}"
            for m in trend[-3:]
        )
        lines.append(f"- Recent monthly trend: {rendered}")

    anomalies = ctx.get("anomalies") or []
    if anomalies:
        rendered = "; ".join(
            f"{a.get('description', 'expense')} {_currency(a.get('amount'))}" for a in anomalies[:3]
        )
        lines.append(f"- Flagged unusual transactions ({len(anomalies)}): {rendered}")

    recent = ctx.get("recent_transactions") or []
    if recent:
        rendered = "; ".join(
            f"{t.get('date', '')} {t.get('type', 'expense')} "
            f"{_currency(t.get('amount'))} {t.get('description', '')}".strip()
            for t in recent[:5]
        )
        lines.append(f"- Last transactions: {rendered}")

    bills = ctx.get("recent_bills") or []
    if bills:
        rendered = "; ".join(
            f"{b.get('bill_ref') or 'bill'} {_currency(b.get('total_amount'))} "
            f"({b.get('item_count', 0)} items)"
            for b in bills[:3]
        )
        lines.append(f"- Recent supplier bills: {rendered}")

    return "\n".join(lines)


def _system_prompt(lang: str, financial_context: dict | None) -> str:
    is_hi = lang == "hi"
    language_rule = (
        "LANGUAGE: reply in natural Hindi (Devanagari script) only, polite and encouraging, "
        "using simple words an Indian shopkeeper understands. Even if earlier messages are in "
        "English, answer in Hindi."
        if is_hi else
        "LANGUAGE: reply in clear, simple English only, suitable for an Indian shopkeeper. "
        "Even if earlier messages are in Hindi, answer in English."
    )
    return (
        "You are DukaanSaathi AI, a warm financial and retail assistant for Indian "
        "small-business owners (kirana stores, bakeries and retailers).\n"
        "You help with: sales trends, profit margins, discounts, inventory, supplier bills, "
        "expense tracking, budgeting and the ML forecasts shown in the app.\n"
        f"{language_rule}\n"
        "Rules:\n"
        "1. Use ONLY the business data given below. Never invent sales figures, bills or forecasts.\n"
        "2. If a number is missing, say it is not available yet and explain where to add it.\n"
        "3. Be concise: 2-5 short sentences or a short bullet list. Be practical and specific.\n"
        "4. If the user asks about a feature, point to the exact tab (Dashboard, Sales, Products, "
        "Bills, Recommendations, Offers, Margin, Payment).\n"
        "5. Never claim statistical significance. Forecasts are estimates.\n"
        f"\n{_build_context(financial_context, lang)}\n"
    )


def _call_groq(messages: list[dict]) -> tuple[str, str] | None:
    """Try the model chain; return (reply, model) or None."""
    key = _api_key()
    if not key or key == "YOUR_GROQ_API_KEY":
        return None
    try:
        from groq import Groq
    except Exception as exc:  # pragma: no cover
        logger.warning("Groq SDK unavailable: %s", exc)
        return None

    try:
        client = Groq(api_key=key)
    except Exception as exc:  # pragma: no cover
        logger.warning("Groq client init failed: %s", exc)
        return None

    last_error = None
    for model in _model_chain():
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.35,
                max_tokens=450,
            )
            reply = (completion.choices[0].message.content or "").strip()
            if reply:
                return reply, model
        except Exception as exc:
            last_error = exc
            message = str(exc)
            # Retry with the next model for model/availability issues only
            if any(token in message for token in ("model_not_found", "does not exist", "404", "429", "rate_limit")):
                logger.warning("Groq model %s unavailable (%s); trying next.", model, message[:160])
                continue
            logger.warning("Groq call failed on %s: %s", model, message[:200])
            break

    if last_error:
        logger.warning("Groq unavailable, using local fallback: %s", last_error)
    return None


# ---------------------------------------------------------------------------
# Offline fallback
# ---------------------------------------------------------------------------

def _fallback_reply(user_message: str, lang: str, financial_context: dict | None) -> str:
    is_hi = lang == "hi"
    msg = (user_message or "").lower()
    ctx = financial_context or {}

    product_count = int(ctx.get("product_count") or 0)
    has_sales = bool(ctx.get("has_sales") or ctx.get("has_sales_history"))
    tx_count = int(ctx.get("transaction_count") or 0)

    if not has_sales and product_count == 0 and tx_count == 0:
        if any(w in msg for w in ["predict", "future", "भविष्य", "bhavishya", "bikri", "sale", "बिक्री"]):
            if is_hi:
                return ("आपकी दुकान अभी नई है और इसमें कोई उत्पाद या बिक्री दर्ज नहीं है। "
                        "सटीक भविष्यवाणी के लिए पहले 'उत्पाद' टैब में उत्पाद जोड़ें और बिल अपलोड करें।")
            return ("Your store is newly registered with no products or sales yet. "
                    "Add your catalogue in the Products tab and upload supplier bills to unlock AI forecasts.")
        if is_hi:
            return ("नमस्ते! मैं आपका दुकानसाथी AI सहायक हूँ। शुरुआत करने के लिए 'उत्पाद' टैब में "
                    "अपना सामान जोड़ें, फिर 'बिल' टैब से सप्लायर बिल अपलोड करें।")
        return ("Hello! I am your DukaanSaathi AI assistant. To get started, add your products "
                "in the Products tab, then upload supplier bills in the Bills tab.")

    if any(w in msg for w in ["predict", "future", "forecast", "bhavishya", "भविष्य", "kharcha", "खर्च"]):
        forecast = ctx.get("predicted_30_days_total")
        if forecast:
            if is_hi:
                return (f"एमएल मॉडल के अनुसार अगले 30 दिनों का अनुमानित खर्च लगभग {_currency(forecast)} है। "
                        "यह अनुमान आपके दर्ज किए गए लेन-देन पर आधारित है, इसलिए नियमित रूप से बिक्री और बिल दर्ज करते रहें।")
            return (f"Based on your recorded transactions, the ML model estimates about "
                    f"{_currency(forecast)} of spending over the next 30 days. Keep your ledger "
                    f"updated for sharper forecasts.")
        if is_hi:
            return ("भविष्यवाणी के लिए कुछ लेन-देन चाहिए। 'डैशबोर्ड' पर खर्च या बिक्री दर्ज करें, "
                    "फिर मैं 7 और 30 दिनों का अनुमान दिखा सकूँगा।")
        return ("I need a few transactions to forecast. Record expenses or sales on the Dashboard "
                "and I can show 7-day and 30-day estimates.")

    if any(w in msg for w in ["weak", "slow", "kam bikri", "कम बिक्री", "धीमा"]):
        weak_day = ctx.get("weak_day")
        if weak_day:
            if is_hi:
                return (f"आपकी सबसे कम बिक्री {weak_day} को होती है। उस दिन बंडल ऑफर या छोटा "
                        "डिस्काउंट चलाकर ग्राहकों को आकर्षित करें — 'सुझाव' टैब में तैयार सलाह देखें।")
            return (f"Your slowest day is {weak_day}. Run a small bundle offer or discount on that "
                    f"day to lift footfall — see the Recommendations tab for a ready plan.")
        if is_hi:
            return "कम बिक्री वाले दिन का विश्लेषण 'बिक्री विश्लेषण' पेज पर उपलब्ध है।"
        return "Your slowest sales days are analysed on the Sales Analysis page."

    if any(w in msg for w in ["margin", "munafa", "profit", "मुनाफ़ा", "मार्जिन", "discount", "छूट"]):
        if is_hi:
            return ("दुकानसाथी का मार्जिन इंजन आपके न्यूनतम ग्रॉस प्रॉफिट की रक्षा करता है। "
                    "'मार्जिन कैलकुलेटर' में कीमत और छूट डालकर सुरक्षित लाभ देखें।")
        return ("DukaanSaathi's margin engine protects your minimum gross profit. Use the Margin "
                "Calculator to test a discount before you offer it.")

    if any(w in msg for w in ["anomaly", "unusual", "alert", "असामान्य", "zyada kharcha"]):
        count = ctx.get("anomaly_count")
        if is_hi:
            return (f"Isolation Forest मॉडल ने {count or 0} लेन-देन असामान्य पाए हैं। "
                    "इन्हें 'डैशबोर्ड' के हाल के लेन-देन में देखें।")
        return (f"The Isolation Forest model flagged {count or 0} transaction(s) as unusually large. "
                f"Review them in the recent transactions list on the Dashboard.")

    if any(w in msg for w in ["bill", "बिल", "invoice", "receipt", "ocr"]):
        if is_hi:
            return ("'बिल' टैब में जाकर सप्लायर बिल की फोटो या PDF अपलोड करें। OCR उससे सामान, "
                    "मात्रा और लागत निकालकर आपके उत्पादों की लागत अपडेट कर देगा।")
        return ("Open the Bills tab and upload a supplier bill photo or PDF. OCR extracts the items, "
                "quantities and rates, then updates your product cost prices after you confirm.")

    if any(w in msg for w in ["sale", "बिक्री", "revenue", "kamai", "कमाई", "business", "dhanda"]):
        income = ctx.get("total_income")
        if income:
            if is_hi:
                return (f"अब तक दर्ज कुल बिक्री {_currency(income)} है और कुल खर्च {_currency(ctx.get('total_expense'))} है। "
                        "विस्तृत ट्रेंड 'बिक्री विश्लेषण' पेज पर देखें।")
            return (f"Total recorded revenue is {_currency(income)} against {_currency(ctx.get('total_expense'))} "
                    f"in expenses. See the Sales Analysis page for the full trend.")
        if is_hi:
            return "अभी कोई बिक्री दर्ज नहीं है। 'डैशबोर्ड' से बिक्री जोड़ें या बिल अपलोड करें।"
        return "No sales are recorded yet. Add sales from the Dashboard or upload supplier bills."

    if is_hi:
        return ("मैं आपका दुकानसाथी AI सहायक हूँ। आप मुझसे बिक्री, खर्च, मुनाफ़े, बिल/OCR, "
                "बजट या एमएल भविष्यवाणी के बारे में पूछ सकते हैं।")
    return ("I am your DukaanSaathi AI assistant. Ask me about sales, expenses, profit margins, "
            "bill OCR, budgeting or the ML forecasts.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ask_groq_assistant_ex(
    user_message: str,
    lang: str = "en",
    financial_context: dict | None = None,
    history: list[dict] | None = None,
) -> dict:
    """
    Chat with the merchant. Returns:
        {"reply": str, "source": "groq" | "offline", "model": str | None}
    """
    messages: list[dict] = [
        {"role": "system", "content": _system_prompt(lang, financial_context)}
    ]

    if history:
        for past in history[-MAX_HISTORY_TURNS:]:
            role = "assistant" if (past.get("sender") or past.get("role")) in ("ai", "assistant") else "user"
            content = (past.get("message") or past.get("content") or "").strip()
            if content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})
    result = _call_groq(messages)
    if result:
        reply, model = result
        return {"reply": reply, "source": "groq", "model": model}

    return {
        "reply": _fallback_reply(user_message, lang, financial_context),
        "source": "offline",
        "model": None,
    }


def ask_groq_assistant(
    user_message: str,
    lang: str = "en",
    financial_context: dict | None = None,
    history: list[dict] | None = None,
) -> str:
    """Backwards-compatible wrapper returning only the reply text."""
    return ask_groq_assistant_ex(
        user_message, lang=lang, financial_context=financial_context, history=history
    )["reply"]
