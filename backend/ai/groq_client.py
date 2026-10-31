"""
DukaanSaathi / Paytm AI — Groq Conversational AI Client
Provides fast, intelligent financial guidance in Hindi and English
using Groq's low-latency LLaMA models, grounded in the user's real business data.
"""
from __future__ import annotations
import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def ask_groq_assistant(
    user_message: str,
    lang: str = "en",
    financial_context: dict = None,
) -> str:
    """
    Generate conversational business and financial insights using Groq.
    Grounded exclusively in the authenticated shopkeeper's real metrics.
    Falls back gracefully if GROQ_API_KEY is not configured or errors occur.
    """
    key = GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
    is_hi = lang == "hi"

    # Evaluate whether user has actual data
    has_sales = True
    product_count = 1
    if financial_context:
        has_sales = bool(financial_context.get("has_sales_history") or financial_context.get("has_sales"))
        product_count = int(financial_context.get("product_count", 0))

    if key and key.strip() and key != "YOUR_GROQ_API_KEY":
        try:
            client = Groq(api_key=key.strip())
            
            context_str = ""
            if financial_context:
                shop_name = financial_context.get("shop_name", "My Shop")
                total_income = financial_context.get("total_income", 0)
                balance = financial_context.get("balance", 0)
                weak_day = financial_context.get("weak_day")

                if not has_sales and product_count == 0:
                    context_str = (
                        f"Current Business Status for {shop_name}: Newly opened account. "
                        "Products in catalog: 0. Recorded sales: ₹0. "
                        "CRITICAL INSTRUCTION: The user has not added any products or sales yet. "
                        "Do not fabricate numbers. Explain that they need to add products in the Products tab "
                        "and record transactions/bills to get personalised AI predictions."
                    )
                else:
                    context_str = (
                        f"Current Business Data for {shop_name}: "
                        f"Active Products: {product_count}, Total Revenue: ₹{total_income:,.2f}, "
                        f"Ledger Balance: ₹{balance:,.2f}, Slowest Day: {weak_day or 'Calculating pattern'}."
                    )

            system_prompt = (
                "You are DukaanSaathi AI Financial & Retail Assistant for Indian shopkeepers. "
                "You help merchants understand sales trends, optimize profit margins, manage inventory, and budget smartly. "
                f"Respond naturally in {'Hindi (Devanagari script with polite, encouraging tone)' if is_hi else 'English'}. "
                "Keep responses concise, actionable, and under 4-5 sentences. "
                "Never invent fake sales statistics. Rely only on the shopkeeper's provided numbers.\n"
                f"{context_str}"
            )

            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_tokens=350,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq API call error: {e}. Using fallback assistant.")

    # Intelligent Local Fallback Response Grounded in User State
    msg = user_message.lower()

    if not has_sales and product_count == 0:
        if any(w in msg for w in ["predict", "future", "bhavishya", "bikri", "sale", "weak", "slow"]):
            if is_hi:
                return "आपकी दुकान अभी नई है और इसमें कोई उत्पाद या बिक्री दर्ज नहीं है। सटीक भविष्यवाणी के लिए पहले 'Products' टैब में जाकर उत्पाद जोड़ें।"
            return "Your store is newly registered with no products or sales recorded yet. Please add your catalog in the 'Products' tab to unlock AI forecasts."

    if any(w in msg for w in ["predict", "future", "bhavishya", "kitna kharcha"]):
        if is_hi:
            return "दुकानसाथी एमएल मॉडल आपकी बिक्री और खर्च पैटर्न के आधार पर भविष्यवाणी करता है। नियमित बिक्री दर्ज करके आप सटीक 30-दिन का अनुमान देख सकते हैं।"
        return "DukaanSaathi's ML Ridge Regression model predicts future trends based on your real transactions. Keep your ledger updated to see rolling 30-day forecasts."

    elif any(w in msg for w in ["weak", "slow", "kam bikri", "slow day"]):
        if is_hi:
            return "कम बिक्री वाले दिन का विश्लेषण 'Sales Analysis' में उपलब्ध है। उस दिन के लिए विशेष डिस्काउंट या बंडल ऑफर चलाकर ग्राहकों को आकर्षित करें।"
        return "Your slowest sales days are analyzed under 'Sales Analysis'. You can run targeted bundle offers on these days to boost footfall."

    elif any(w in msg for w in ["margin", "munafa", "profit", "discount"]):
        if is_hi:
            return "दुकानसाथी का मार्जिन इंजन आपके न्यूनतम 15% ग्रॉस प्रॉफिट की रक्षा करता है। कोई भी डिस्काउंट तभी स्वीकृत होता है जब वह सुरक्षित लाभ सीमा में हो।"
        return "DukaanSaathi's deterministic margin engine protects your 15% gross profit floor, ensuring discounts never cause loss."

    elif any(w in msg for w in ["anomaly", "unusual", "alert", "kharcha zyada"]):
        if is_hi:
            return "हमारा Isolation Forest एमएल मॉडल असामान्य या बड़े खर्चों को तुरंत फ्लैग करता है ताकि लेन-देन सुरक्षित रहे।"
        return "Our Isolation Forest ML model monitors your transaction ledger, flagging unusually large transactions as anomalies."

    else:
        if is_hi:
            return "नमस्ते! मैं आपका दुकानसाथी AI सहायक हूँ। अपने उत्पादों, मुनाफ़े के मार्जिन, या दुकान की बिक्री बढ़ाने के बारे में कुछ भी पूछें।"
        return "Hello! I am your DukaanSaathi AI Assistant. Ask me anything about your products, profit margins, weak-day offers, or budgeting."
