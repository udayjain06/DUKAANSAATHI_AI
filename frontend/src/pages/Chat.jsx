import React, { useState, useRef, useEffect } from 'react'
import api from '../api'
import { useLanguage } from '../context/LanguageContext'

export default function Chat() {
  const { lang, setLang } = useLanguage()
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: lang === 'hi' 
        ? 'नमस्ते! मैं DukaanSaathi Groq AI सहायक हूँ। अपने खर्च, बजट, मशीन लर्निंग (ML) भविष्यवाणी या दुकान के मुनाफ़े के बारे में कोई भी सवाल पूछें।'
        : 'Hello! I am your DukaanSaathi Groq AI Assistant. Ask any question regarding your spending, monthly budget, scikit-learn ML spending predictions, or shop profit margins.',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const quickPrompts = [
    { 
      label: '🔮 ML 30-Day Forecast', 
      prompt: lang === 'hi' 
        ? 'Meri agle 30 dino ki ML spending prediction samjhao aur main paise kaise bacha sakta hoon?' 
        : 'Explain my 30-day ML spending prediction and how I can optimize my budget.' 
    },
    { 
      label: '⚠️ Unusual Transactions', 
      prompt: lang === 'hi'
        ? 'Kya mere transactions mein koi unusual ya anomalous kharcha detect hua hai?'
        : 'Were any unusual or anomalous transactions detected in my account recently?'
    },
    { 
      label: '📉 Sabse kam bikri kab?', 
      prompt: lang === 'hi'
        ? 'Meri dukaan mein sabse kam bikri kis din hoti hai aur kitna dip hai?'
        : 'Which day of the week is slowest for my shop and what is the revenue dip?'
    },
    { 
      label: '🏷️ Monday Safe Offer', 
      prompt: lang === 'hi'
        ? 'Monday ke liye koi safe discount ya bundle offer suggest karo jo margin safe rakhe.'
        : 'Suggest a safe discount or bundle offer for Monday that protects my profit margin.'
    },
  ]

  const handleSend = async (textToSend) => {
    const text = textToSend || input
    if (!text.trim()) return

    const userMsg = {
      sender: 'user', text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      // First attempt Groq AI endpoint
      let res
      try {
        res = await api.post('/user/chat', { message: text, lang })
      } catch {
        res = await api.post('/chat', { message: text, lang })
      }
      setMessages(prev => [...prev, {
        sender: 'ai', text: res.data.reply,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    } catch {
      setMessages(prev => [...prev, {
        sender: 'ai',
        text: lang === 'hi' 
          ? 'माफी, सर्वर से जुड़ने में समस्या आई। कृपया दोबारा प्रयास करें।'
          : 'Sorry, could not connect to the server. Please try again.',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 22, gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h2 style={{ fontSize: 22, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em', margin: 0 }}>
              AI Financial Assistant
            </h2>
            <span style={{
              background: 'rgba(0, 186, 242, 0.12)',
              color: '#00BAF2',
              fontSize: 11,
              fontWeight: 700,
              padding: '3px 9px',
              borderRadius: '999px',
              border: '1px solid rgba(0, 186, 242, 0.3)'
            }}>
              ⚡ Powered by Groq LLaMA
            </span>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
            Bilingual AI advisor (Hindi / English). Explains ML predictions, anomalies, budgeting, and profit protection.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--muted)', marginRight: 4 }}>Language:</span>
          <button
            className={`btn btn-sm ${lang === 'hi' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setLang('hi')}
          >
            🇮🇳 हिंदी
          </button>
          <button
            className={`btn btn-sm ${lang === 'en' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setLang('en')}
          >
            🇬🇧 English
          </button>
        </div>
      </div>

      {/* Chat container */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '620px', overflow: 'hidden' }}>
        {/* Messages */}
        <div ref={scrollRef} style={{
          flex: 1, padding: 22, overflowY: 'auto',
          background: 'var(--bg)'
        }}>
          {messages.map((m, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                justifyContent: m.sender === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: 16,
              }}
            >
              <div
                style={{
                  maxWidth: '78%',
                  padding: '14px 18px',
                  borderRadius: 16,
                  fontSize: 14,
                  lineHeight: 1.6,
                  background: m.sender === 'user' ? '#00BAF2' : 'var(--surface)',
                  color: m.sender === 'user' ? '#002970' : 'var(--text)',
                  border: m.sender === 'user' ? 'none' : '1px solid var(--border)',
                  boxShadow: 'var(--shadow-sm)',
                  fontWeight: m.sender === 'user' ? 600 : 400,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {m.text}
                <div
                  style={{
                    fontSize: 10.5,
                    marginTop: 6,
                    textAlign: 'right',
                    color: m.sender === 'user' ? 'rgba(0, 41, 112, 0.7)' : 'var(--muted)',
                  }}
                >
                  {m.time}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 14 }}>
              <div style={{
                padding: '12px 18px',
                borderRadius: 16,
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                color: 'var(--muted)',
                fontSize: 13,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                <span>Groq AI is thinking...</span>
              </div>
            </div>
          )}
        </div>

        {/* Quick prompt suggestions */}
        <div style={{
          padding: '10px 18px',
          borderTop: '1px solid var(--border)',
          background: 'var(--surface)',
          display: 'flex',
          gap: 8,
          overflowX: 'auto',
          whiteSpace: 'nowrap'
        }}>
          {quickPrompts.map((qp, i) => (
            <button
              key={i}
              type="button"
              className="btn btn-sm btn-ghost"
              style={{ fontSize: 12, padding: '5px 12px', flexShrink: 0 }}
              onClick={() => handleSend(qp.prompt)}
            >
              {qp.label}
            </button>
          ))}
        </div>

        {/* Input box */}
        <div style={{
          padding: 16,
          borderTop: '1px solid var(--border)',
          background: 'var(--surface)',
          display: 'flex',
          gap: 10,
        }}>
          <input
            className="form-input"
            style={{ flex: 1 }}
            placeholder={lang === 'hi' ? 'यहाँ सवाल लिखें (जैसे: मेरा 30 दिनों का बजट कैसा है?)...' : 'Type your question (e.g. How is my 30-day budget?)...'}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSend() }}
          />
          <button
            className="btn btn-primary"
            style={{ minWidth: 90 }}
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            {loading ? 'Sending...' : (lang === 'hi' ? 'पूछें' : 'Send')}
          </button>
        </div>
      </div>
    </div>
  )
}
