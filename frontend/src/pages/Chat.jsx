import React, { useState } from 'react'
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

  const quickPrompts = [
    { label: '📉 Sabse kam bikri kab?', prompt: 'Meri dukaan mein sabse kam bikri kis din hoti hai aur kitna dip hai?' },
    { label: '🏷️ Monday offer recommendation', prompt: 'Monday ke liye koi safe discount ya bundle offer suggest karo.' },
    { label: '🧮 Margin protection formula', prompt: 'DukaanSaathi ka margin engine mujhe loss hone se kaise bachata hai?' },
    { label: '🏆 Best selling products', prompt: 'Mere top performing products kaunse hain?' },
  ]

  const handleSend = async (textToSend) => {
    const text = textToSend || input
    if (!text.trim()) return

    const userMsg = {
      sender: 'user',
      text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await api.post('/chat', {
        message: text,
        lang
      })
      const aiMsg = {
        sender: 'ai',
        text: res.data.reply,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setMessages(prev => [...prev, aiMsg])
    } catch (err) {
      const errMsg = {
        sender: 'ai',
        text: 'Maafi, server se connect karne mein samasya aayi. Kripya dubara prayas karein.',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, color: 'var(--heading)' }}>DukaanSaathi AI Voice & Chat Assistant</h2>
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>
            Bilingual shop assistant (Hindi/English). Explains verified calculations and never invents financial figures.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: 'var(--muted)' }}>Language:</span>
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

      {/* Chat Container */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '620px' }}>
        {/* Messages scroll area */}
        <div style={{ flex: 1, padding: 20, overflowY: 'auto', background: '#F8FAFC' }}>
          {messages.map((m, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                justifyContent: m.sender === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: 14,
              }}
            >
              <div style={{
                maxWidth: '75%',
                padding: '12px 16px',
                borderRadius: 12,
                background: m.sender === 'user' ? 'var(--teal)' : 'var(--white)',
                color: m.sender === 'user' ? '#FFFFFF' : 'var(--body)',
                border: m.sender === 'user' ? 'none' : '1px solid var(--border)',
                boxShadow: 'var(--shadow)',
                whiteSpace: 'pre-line',
                fontSize: 14,
                lineHeight: 1.5,
              }}>
                <div style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: m.sender === 'user' ? '#CCFBF1' : 'var(--teal-dark)',
                  marginBottom: 4,
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 12
                }}>
                  <span>{m.sender === 'user' ? 'You' : '🤖 DukaanSaathi AI'}</span>
                  <span style={{ fontWeight: 400, opacity: 0.8 }}>{m.time}</span>
                </div>
                {m.text}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 14 }}>
              <div style={{
                background: 'var(--white)',
                border: '1px solid var(--border)',
                padding: '10px 16px',
                borderRadius: 12,
                fontSize: 13,
                color: 'var(--muted)',
                display: 'flex',
                alignItems: 'center',
                gap: 8
              }}>
                <div className="spinner" style={{ width: 14, height: 14 }} />
                <span>DukaanSaathi dimaag laga raha hai...</span>
              </div>
            </div>
          )}
        </div>

        {/* Quick Prompts */}
        <div style={{ padding: '8px 16px', background: 'var(--white)', borderTop: '1px solid var(--border)', display: 'flex', gap: 8, overflowX: 'auto' }}>
          {quickPrompts.map((q, i) => (
            <button
              key={i}
              className="btn btn-ghost btn-sm"
              style={{ whiteSpace: 'nowrap', fontSize: 12 }}
              onClick={() => handleSend(q.prompt)}
            >
              {q.label}
            </button>
          ))}
        </div>

        {/* Input box */}
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          style={{ padding: 14, background: 'var(--white)', borderTop: '1px solid var(--border)', display: 'flex', gap: 10 }}
        >
          <input
            className="form-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={lang === 'hi' ? 'Apna sawal yahan likhein (jaise: Monday offer batao)...' : 'Type your question here (e.g. recommend a Monday offer)...'}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  )
}

