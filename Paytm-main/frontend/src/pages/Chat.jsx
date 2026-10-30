import React, { useState, useRef, useEffect } from 'react'
import api from '../api'

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: 'नमस्ते! मैं DukaanSaathi AI हूँ। अपनी दुकान की बिक्री, मुनाफ़ा (margin) या ऑफ़र के बारे में कोई भी सवाल पूछें।\n\nHello! I am DukaanSaathi AI. Ask any question about your shop sales, profit margins, or promotional offers.',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ])
  const [input, setInput] = useState('')
  const [lang, setLang] = useState('hi')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const quickPrompts = [
    { label: '📉 Sabse kam bikri kab?', prompt: 'Meri dukaan mein sabse kam bikri kis din hoti hai aur kitna dip hai?' },
    { label: '🏷️ Monday offer', prompt: 'Monday ke liye koi safe discount ya bundle offer suggest karo.' },
    { label: '🧮 Margin protection', prompt: 'DukaanSaathi ka margin engine mujhe loss hone se kaise bachata hai?' },
    { label: '🏆 Top products', prompt: 'Mere top performing products kaunse hain?' },
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
      const res = await api.post('/chat', { message: text, lang })
      setMessages(prev => [...prev, {
        sender: 'ai', text: res.data.reply,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    } catch {
      setMessages(prev => [...prev, {
        sender: 'ai',
        text: 'Maafi, server se connect karne mein samasya aayi. Kripya dubara prayas karein.',
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
          <h2 style={{ fontSize: 20, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em' }}>
            AI Chat Assistant
          </h2>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
            Bilingual assistant (Hindi / English). Explains verified calculations, never invents financial figures.
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
                marginBottom: 14,
              }}
            >
              <div className={`chat-bubble ${m.sender}`}>
                <div style={{
                  fontSize: 12, fontWeight: 700, marginBottom: 6,
                  display: 'flex', justifyContent: 'space-between', gap: 14,
                  color: m.sender === 'user' ? 'rgba(255,255,255,0.7)' : 'var(--accent)',
                  letterSpacing: '0.02em',
                }}>
                  <span>{m.sender === 'user' ? 'You' : '🤖 DukaanSaathi AI'}</span>
                  <span style={{ fontWeight: 400, opacity: 0.7 }}>{m.time}</span>
                </div>
                {m.text}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 14 }}>
              <div className="chat-bubble ai" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div className="spinner" style={{ width: 14, height: 14 }} />
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>DukaanSaathi dimaag laga raha hai...</span>
              </div>
            </div>
          )}
        </div>

        {/* Quick Prompts */}
        <div style={{
          padding: '10px 18px',
          background: 'var(--white)',
          borderTop: '1px solid var(--border)',
          display: 'flex', gap: 8, overflowX: 'auto',
        }}>
          {quickPrompts.map((q, i) => (
            <button
              key={i}
              className="quick-prompt-pill"
              onClick={() => handleSend(q.prompt)}
            >
              {q.label}
            </button>
          ))}
        </div>

        {/* Input */}
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend() }}
          style={{
            padding: '14px 18px',
            background: 'var(--white)',
            borderTop: '1px solid var(--border)',
            display: 'flex', gap: 10,
          }}
        >
          <input
            className="form-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={lang === 'hi' ? 'Apna sawal yahan likhein...' : 'Type your question here...'}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
