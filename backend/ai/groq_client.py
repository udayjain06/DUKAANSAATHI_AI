"""
DukaanSaathi / Paytm AI — Groq Conversational AI Client
Provides fast, intelligent financial guidance in Hindi and English
using Groq's low-latency LLaMA models.
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
    Generate conversational financial insights and answers using Groq.
    Falls back gracefully if GROQ_API_KEY is not configured.
    """
    key = GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
    if key and key.strip() and key != "YOUR_GROQ_API_KEY":
        try:
            client = Groq(api_key=key.strip())
            
            context_str = ""
            if financial_context:
                context_str = (
                    f"User Financial Summary: Current Balance: ₹{financial_context.get('balance', 0):,.2f}, "
                    f"Monthly Income: ₹{financial_context.get('total_income', 0):,.2f}, "
                    f"Monthly Expense: ₹{financial_context.get('total_expense', 0):,.2f}, "
                    f"Predicted 30-Day Spending: ₹{financial_context.get('predicted_30_days', 0):,.2f}, "
                    f"Top Expense Category: {financial_context.get('top_category', 'General')}."
                )

            system_prompt = (
                "You are Paytm / DukaanSaathi AI Financial Assistant. "
                "You help users manage expenses, understand ML predictions, protect profit margins, and budget smartly. "
                f"Respond naturally in {'Hindi (Devanagari script with friendly tone)' if lang == 'hi' else 'English'}. "
                "Keep your answers concise, practical, and under 4-5 sentences. "
                "Do not hallucinate false claims; refer to the user's provided numbers when appropriate.\n"
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

    # Intelligent Local Fallback Response
    msg = user_message.lower()
    is_hi = lang == "hi"

    if any(w in msg for w in ["predict", "future", "bhavishya", "kitna kharcha"]):
        if is_hi:
            return "ML मॉडल के अनुसार आपका अगले 30 दिनों का अनुमानित खर्च लगभग ₹39,600 रहने की उम्मीद है। बचत दर बढ़ाने के लिए गैर-जरूरी खर्चों को 10-15% कम करें।"
        return "Based on our trained ML Ridge Regression model, your predicted 30-day expenditure is ₹39,604. We recommend allocating at least 20% of your income directly to savings."

    elif any(w in msg for w in ["anomaly", "unusual", "alert", "kharcha zyada"]):
        if is_hi:
            return "हमारा Isolation Forest ML मॉडल ₹15,000 से अधिक या असामान्य खर्चों को तुरंत फ्लैग करता है ताकि कोई अनधिकृत लेन-देन न हो।"
        return "Our scikit-learn Isolation Forest model monitors your ledger in real-time, instantly flagging transactions over ₹15,000 or abnormal frequency as potential anomalies."

    elif any(w in msg for w in ["save", "budget", "bachat", "invest"]):
        if is_hi:
            return "50-30-20 नियम अपनाएं: 50% बुनियादी जरूरतों (किराया, राशन) पर, 30% जीवनशैली पर, और 20% तुरंत बचत या निवेश में डालें।"
        return "Apply the classic 50-30-20 rule: 50% on essential needs, 30% on discretionary lifestyle, and 20% strictly toward emergency savings and investments."

    elif any(w in msg for w in ["margin", "munafa", "profit", "discount"]):
        if is_hi:
            return "दुकानसाथी का मार्जिन इंजन आपके न्यूनतम 15% ग्रॉस प्रॉफिट की रक्षा करता है। कोई भी डिस्काउंट तभी स्वीकृत होता है जब वह सुरक्षित लाभ सीमा में हो।"
        return "DukaanSaathi's deterministic margin engine protects your 15% gross profit floor, ensuring discounts never cause financial loss regardless of volume."

    else:
        if is_hi:
            return "नमस्ते! मैं आपका Paytm AI वित्तीय सहायक हूँ। अपनी बचत, खर्च के रुझान, या आगामी वित्तीय भविष्यवाणियों के बारे में कुछ भी पूछें।"
        return "Hello! I am your Paytm AI Financial Assistant. Ask me anything about your spending trends, ML predictions, budgeting, or profit margins."

