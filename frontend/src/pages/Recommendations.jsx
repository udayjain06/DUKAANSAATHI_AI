import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, Badge, DataLabel, Modal } from '../components/UI'

export default function Recommendations() {
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [modifyModalRec, setModifyModalRec] = useState(null)
  const [modifiedDiscount, setModifiedDiscount] = useState('')

  const load = () => {
    setLoading(true)
    api.get('/recommendation')
      .then(r => setRecs(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const res = await api.post('/recommendation')
      if (res.data?.status === 'insufficient_data') {
        alert(res.data.message)
      } else {
        load()
      }
    } catch (err) {
      alert(err.response?.data?.detail || err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleDecision = async (id, decision, modifiedOffer = null) => {
    try {
      await api.post(`/recommendation/${id}/decision`, {
        decision,
        modified_offer: modifiedOffer
      })
      if (decision === 'approved') {
        alert("Offer approved! Head over to 'Offers & Experiments' to view your marketing poster and experiment tracking.")
      }
      load()
    } catch (err) {
      alert(err.response?.data?.detail || err.message)
    }
  }

  const handleSaveModification = () => {
    if (!modifyModalRec) return
    const disc = parseFloat(modifiedDiscount)
    if (isNaN(disc) || disc <= 0 || disc > 80) {
      alert("Please provide a valid discount between 1% and 80%.")
      return
    }
    const currentOffer = modifyModalRec.offer || {}
    const modifiedOffer = {
      ...currentOffer,
      discount_pct: disc,
      custom_merchant_override: true,
      note: `Merchant adjusted discount to ${disc}%`
    }
    handleDecision(modifyModalRec.id, 'modified', modifiedOffer)
    setModifyModalRec(null)
  }

  if (loading) return <Loading text="Evaluating margins & recommendations..." />
  if (error) return <ErrorMsg message={error} />

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22, flexWrap: 'wrap', gap: 14 }}>
        <div>
          <h2 style={{ fontSize: 20, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em' }}>
            AI Recommendation Engine
          </h2>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
            Deterministic financial calculations prevent loss: strictly verified margins, required volume uplift & customer risk caps.
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={generating}
        >
          {generating ? 'Calculating...' : '+ Generate New Recommendation'}
        </button>
      </div>

      {recs.length === 0 ? (
        <div className="card" style={{ padding: 48, textAlign: 'center' }}>
          <div style={{ fontSize: 36, marginBottom: 10 }}>💡</div>
          <h3 style={{ fontSize: 16, fontWeight: 650, color: 'var(--heading)' }}>No recommendations yet</h3>
          <p style={{ color: 'var(--muted)', fontSize: 13, maxWidth: 400, margin: '8px auto 20px' }}>
            Generate intelligent discount and bundle recommendations based on your store's weak sales days.
          </p>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
            Generate First Recommendation
          </button>
        </div>
      ) : (
        recs.map(r => {
          const offer = r.offer || {}
          const margin = r.margin || {}
          const risk = r.risk || {}
          const expl = r.explanation || {}

          return (
            <div key={r.id} className="card" style={{ marginBottom: 22 }}>
              <div className="card-header">
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--heading)' }}>
                    Recommendation #{r.id}
                  </span>
                  <span style={{ color: 'var(--error)', fontWeight: 600, fontSize: 13 }}>
                    Target: {r.weak_day} (Dip: {pct(r.dip_pct)})
                  </span>
                  <DataLabel label={r.data_label} />
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <span style={{ fontSize: 11.5, color: 'var(--muted)', fontWeight: 600 }}>Margin:</span>
                  <Badge status={margin.status || 'ok'} />
                  <span style={{ fontSize: 11.5, color: 'var(--muted)', fontWeight: 600, marginLeft: 4 }}>Decision:</span>
                  <Badge status={r.status} />
                </div>
              </div>

              <div className="card-body">
                {/* Offer Details Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 14, marginBottom: 18 }}>
                  <div style={{ background: 'var(--surface)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
                    <div className="stat-label">Offer Type & Products</div>
                    <div style={{ fontWeight: 700, color: 'var(--heading)', marginTop: 5, fontSize: 14 }}>
                      {offer.type === 'bundle' ? '📦 Bundle Offer' : '🏷️ Product Discount'}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--body)', marginTop: 4, fontWeight: 500 }}>
                      {offer.items ? offer.items.join(' + ') : '—'}
                    </div>
                  </div>

                  <div style={{ background: 'var(--surface)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
                    <div className="stat-label">Pricing</div>
                    <div style={{ display: 'flex', gap: 14, marginTop: 5 }}>
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>Original</div>
                        <div style={{ fontWeight: 600, textDecoration: 'line-through', color: 'var(--muted)', fontSize: 14 }}>
                          {offer.original_price ? fmt(offer.original_price) : (offer.individual_prices ? fmt(offer.individual_prices.reduce((a,b)=>a+b,0)) : '—')}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>Offer Price</div>
                        <div style={{ fontWeight: 700, color: 'var(--teal)', fontSize: 14 }}>
                          {offer.discounted_price ? fmt(offer.discounted_price) : (offer.bundle_price ? fmt(offer.bundle_price) : '—')}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>Discount</div>
                        <div style={{ fontWeight: 700, color: 'var(--warning)', fontSize: 14 }}>
                          {pct(offer.discount_pct)}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: 'var(--surface)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
                    <div className="stat-label">Gross Margin & Uplift</div>
                    <div style={{ fontSize: 13, marginTop: 5 }}>
                      <span style={{ color: 'var(--muted)' }}>Before:</span> <strong>{pct(margin.before_pct)}</strong> (GP {fmt(margin.before_gp)})<br />
                      <span style={{ color: 'var(--muted)' }}>After:</span> <span style={{ color: margin.status === 'blocked' ? 'var(--error)' : 'var(--success)', fontWeight: 700 }}>
                        {pct(margin.after_pct)}
                      </span> (GP {fmt(margin.after_gp)})
                    </div>
                    {margin.required_volume_uplift_pct != null && (
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                        Req. Volume Uplift: +{pct(margin.required_volume_uplift_pct)}
                      </div>
                    )}
                  </div>

                  <div style={{ background: 'var(--surface)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
                    <div className="stat-label">Risk Budget & Units Cap</div>
                    <div style={{ fontSize: 13, marginTop: 5 }}>
                      <span style={{ color: 'var(--muted)' }}>Budget:</span> <strong>{fmt(risk.risk_budget_inr || 400)}</strong><br />
                      <span style={{ color: 'var(--muted)' }}>Max Loss:</span> <span style={{ color: 'var(--error)', fontWeight: 700 }}>{fmt(risk.max_loss_inr)}</span><br />
                      <span style={{ color: 'var(--muted)' }}>Cap:</span> <span style={{ fontWeight: 700 }}>{risk.units_cap || 'No limit'} units</span>
                    </div>
                  </div>
                </div>

                {/* Blocked Alert & Alternative suggestion */}
                {margin.status === 'blocked' && (
                  <div className="alert alert-error" style={{ marginBottom: 16 }}>
                    <strong>⛔ Minimum Margin Violated:</strong> Post-discount margin ({pct(margin.after_pct)}) drops below your minimum threshold ({pct(margin.min_required_pct)}).
                    {margin.alternative && (
                      <div style={{ marginTop: 6, fontWeight: 600 }}>
                        💡 Safer Alternative: {margin.alternative.message} (Resulting margin: {pct(margin.alternative.after_margin_pct)})
                      </div>
                    )}
                  </div>
                )}

                {/* Explanations in Hindi & English */}
                <div style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  padding: 16,
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: 16
                }}>
                  <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--heading)', marginBottom: 8, letterSpacing: '0.02em' }}>
                    💬 AI EXPLANATION (VERIFIED ENGINE FACTS)
                  </div>
                  <div style={{ fontSize: 13, marginBottom: 6, color: 'var(--body)', lineHeight: 1.55 }}>
                    <strong style={{ color: 'var(--heading)' }}>🇮🇳 हिंदी:</strong> {expl.hi || '—'}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--body)', lineHeight: 1.55 }}>
                    <strong style={{ color: 'var(--heading)' }}>🇬🇧 English:</strong> {expl.en || '—'}
                  </div>
                </div>

                {/* Actions: Approve / Modify / Reject */}
                {r.status === 'pending' ? (
                  <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDecision(r.id, 'rejected')}
                    >
                      ✕ Reject
                    </button>
                    <button
                      className="btn btn-warning btn-sm"
                      onClick={() => {
                        setModifyModalRec(r)
                        setModifiedDiscount(offer.discount_pct || 10)
                      }}
                    >
                      ✏️ Modify Discount
                    </button>
                    <button
                      className="btn btn-success"
                      onClick={() => handleDecision(r.id, 'approved')}
                    >
                      ✓ Approve Offer
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
                    <span style={{ fontSize: 13, color: 'var(--muted)' }}>
                      Decision recorded: <strong style={{ textTransform: 'capitalize', color: 'var(--heading)' }}>{r.status}</strong>
                    </span>
                    {r.status === 'approved' && (
                      <Link to="/offers" className="btn btn-outline btn-sm">
                        Go to Active Offers & Experiments →
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })
      )}

      {/* Modify Modal */}
      {modifyModalRec && (
        <Modal
          title={`Modify Recommendation #${modifyModalRec.id}`}
          onClose={() => setModifyModalRec(null)}
          footer={
            <>
              <button className="btn btn-ghost" onClick={() => setModifyModalRec(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSaveModification}>Save Modification</button>
            </>
          }
        >
          <div className="form-group">
            <label className="form-label">Custom Discount Percentage (%)</label>
            <input
              type="number"
              step="0.5"
              min="1"
              max="80"
              className="form-input"
              value={modifiedDiscount}
              onChange={e => setModifiedDiscount(e.target.value)}
            />
            <small style={{ color: 'var(--muted)', marginTop: 6, display: 'block', fontSize: 12 }}>
              Changing the discount updates the post-discount margin. Ensure it respects your minimum profit threshold.
            </small>
          </div>
        </Modal>
      )}
    </div>
  )
}
