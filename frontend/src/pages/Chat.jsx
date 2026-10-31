import React, { useState, useRef, useEffect } from 'react'
import api from '../api'
import { useLanguage } from '../context/LanguageContext'

const nowTime = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

function welcomeMessage(lang) {
  return {
    sender: 'ai',
    text: lang === 'hi'
      ? 'नमस्ते! मैं DukaanSaathi ग्रोक AI सहायक हूँ। अपनी बिक्री, खर्च, बजट, मशीन लर्निंग (ML) भविष्यवाणी, बिल OCR या दुकान के मुनाफ़े के बारे में कुछ भी पूछें।'
      : 'Hello! I am your DukaanSaathi Groq AI assistant. Ask me anything about your sales, expenses, budget, ML forecasts, bill OCR or shop profit margins.',
    time: nowTime(),
    source: 'welcome',
  }
}

export default function Chat() {
  const { lang, setLang } = useLanguage()
  const [messages, setMessages] = useState([welcomeMessage(lang)])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastSource, setLastSource] = useState(null)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const scrollRef = useRef(null)

  // Load persisted chat history for the authenticated user
  useEffect(() => {
    api.get('/chat/history')
      .then(res => {
        if (Array.isArray(res.data) && res.data.length > 0) {
          setMessages(res.data.map(m => ({ ...m, text: m.text || m.message || '' })))
        }
      })
      .catch(() => {})
      .finally(() => setHistoryLoaded(true))
  }, [])

  // Keep the welcome bubble in the chosen language until the first real message
  useEffect(() => {
    if (historyLoaded) return
    setMessages(prev => (
      prev.length === 1 && prev[0].source === 'welcome' ? [welcomeMessage(lang)] : prev
    ))
  }, [lang, historyLoaded])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const quickPrompts = [
    {
      label: '🔮 ML 30-Day Forecast',
      prompt: lang === 'hi'
        ? 'Meri agle 30 dino ki ML spending prediction samjhao aur main paise kaise bacha sakta hoon?'
        : 'Explain my 30-day ML spending prediction and how I can optimise my budget.',
    },
    {
      label: '⚠️ Unusual Transactions',
      prompt: lang === 'hi'
        ? 'Kya mere transactions mein koi unusual ya anomalous kharcha detect hua hai?'
        : 'Were any unusual or anomalous transactions detected in my account recently?',
    },
    {
      label: '📉 Sabse kam bikri kab?',
      prompt: lang === 'hi'
        ? 'Meri dukaan mein sabse kam bikri kis din hoti hai aur kitna dip hai?'
        : 'Which day of the week is slowest for my shop and what is the revenue dip?',
    },
    {
      label: '🏷️ Monday Safe Offer',
      prompt: lang === 'hi'
        ? 'Monday ke liye koi safe discount ya bundle offer suggest karo jo margin safe rakhe.'
        : 'Suggest a safe discount or bundle offer for Monday that protects my profit margin.',
    },
    {
      label: '🧾 Bill OCR',
      prompt: lang === 'hi'
        ? 'Bill upload aur OCR kaise kaam karta hai?'
        : 'How does bill upload and OCR work?',
    },
  ]

  const handleSend = async (textToSend) => {
    const text = (textToSend || input).trim()
    if (!text || loading) return

    setMessages(prev => [...prev, { sender: 'user', text, time: nowTime() }])
    setInput('')
    setLoading(true)

    try {
      // Rich endpoint first (grounded in the user's ledger + merchant metrics)
      let res
      try {
        res = await api.post('/user/chat', { message: text, lang })
      } catch (primaryErr) {
        // Fallback for older backend deployments
        res = await api.post('/chat', { message: text, lang })
      }

      const reply = res.data?.reply || res.data?.message
      const source = res.data?.source || 'groq'
      setLastSource({ source, model: res.data?.model })

      setMessages(prev => [...prev, {
        sender: 'ai',
        text: reply || (lang === 'hi' ? 'कोई उत्तर नहीं मिला।' : 'No response received.'),
        time: nowTime(),
        source,
        model: res.data?.model,
      }])
    } catch (err) {
      setLastSource({ source: 'error' })
      setMessages(prev => [...prev, {
        sender: 'ai',
        text: lang === 'hi'
          ? `माफ़ी, सर्वर से जुड़ने में समस्या आई${err.response?.status ? ` (${err.response.status})` : ''}. कृपया दोबारा प्रयास करें।`
          : `Sorry, I could not reach the server${err.response?.status ? ` (${err.response.status})` : ''}. Please try again.`,
        time: nowTime(),
        source: 'error',
      }])
    } finally {
      setLoading(false)
    }
  }

  const online = lastSource?.source === 'groq'

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 22, gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: 22, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em', margin: 0 }}>
              AI Financial Assistant
            </h2>
            <span style={{
              background: online ? 'rgba(16, 185, 129, 0.12)' : 'rgba(0, 186, 242, 0.12)',
              color: online ? '#10B981' : '#00BAF2',
              fontSize: 11,
              fontWeight: 700,
              padding: '3px 9px',
              borderRadius: '999px',
              border: `1px solid ${online ? 'rgba(16, 185, 129, 0.3)' : 'rgba(0, 186, 242, 0.3)'}`,
            }}>
              {online ? '● Groq online' : '⚡ Groq AI + offline fallback'}
            </span>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
            Bilingual advisor (Hindi / English) grounded in your real sales, expenses and ML forecasts.
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

      <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '620px', overflow: 'hidden' }}>
        <div ref={scrollRef} style={{ flex: 1, padding: 22, overflowY: 'auto', background: 'var(--bg)' }}>
          {messages.map((m, idx) => (
            <div
              key={m.id || idx}
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
                {m.text || m.message}
                <div
                  style={{
                    fontSize: 10.5,
                    marginTop: 6,
                    textAlign: 'right',
                    color: m.sender === 'user' ? 'rgba(0, 41, 112, 0.7)' : 'var(--muted)',
                  }}
                >
                  {m.source === 'groq' && m.model ? `via ${m.model} · ` : ''}
                  {m.source === 'offline' ? 'offline assistant · ' : ''}
                  {m.time || ''}
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
                <span>{lang === 'hi' ? 'सोच रहा है...' : 'Thinking...'}</span>
              </div>
            </div>
          )}
        </div>

        <div style={{
          padding: '10px 18px',
          borderTop: '1px solid var(--border)',
          background: 'var(--surface)',
          display: 'flex',
          gap: 8,
          overflowX: 'auto',
          whiteSpace: 'nowrap',
        }}>
          {quickPrompts.map((qp, i) => (
            <button
              key={i}
              type="button"
              className="btn btn-sm btn-ghost"
              style={{ fontSize: 12, padding: '5px 12px', flexShrink: 0 }}
              onClick={() => handleSend(qp.prompt)}
              disabled={loading}
            >
              {qp.label}
            </button>
          ))}
        </div>

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
            placeholder={lang === 'hi'
              ? 'यहाँ सवाल लिखें (जैसे: मेरा 30 दिनों का बजट कैसा है?)...'
              : 'Type your question (e.g. How is my 30-day budget?)...'}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSend() }}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            style={{ minWidth: 90 }}
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            {loading ? '...' : (lang === 'hi' ? 'पूछें' : 'Send')}
          </button>
        </div>
      </div>
    </div>
  )
}
