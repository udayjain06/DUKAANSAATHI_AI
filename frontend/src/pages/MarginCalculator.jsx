import React, { useState, useEffect } from 'react'
import api, { fmt, pct } from '../api'
import { Badge } from '../components/UI'

export default function MarginCalculator() {
  const [sellPrice, setSellPrice] = useState(100)
  const [costPrice, setCostPrice] = useState(70)
  const [discountPct, setDiscountPct] = useState(20)
  const [minMarginPct, setMinMarginPct] = useState(15)
  const [calcResult, setCalcResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const runCalculation = async () => {
    setLoading(true)
    try {
      const res = await api.post('/margin/check', {
        sell_price: parseFloat(sellPrice),
        cost_price: parseFloat(costPrice),
        discount_pct: parseFloat(discountPct),
        min_margin_pct: parseFloat(minMarginPct),
      })
      setCalcResult(res.data)
    } catch (err) {
      alert(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    runCalculation()
  }, [sellPrice, costPrice, discountPct, minMarginPct])

  const loadSpecExample = () => {
    setSellPrice(100)
    setCostPrice(70)
    setDiscountPct(20)
    setMinMarginPct(15)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, color: 'var(--heading)' }}>Deterministic Margin Engine (Pitch Core)</h2>
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>
            All financial calculations run purely in deterministic Python — strictly no AI hallucination.
          </p>
        </div>
        <button className="btn btn-outline btn-sm" onClick={loadSpecExample}>
          ⚡ Load Official Spec Example (₹100 / ₹70 / 20%)
        </button>
      </div>

      <div className="grid-2">
        {/* Controls Card */}
        <div className="card">
          <div className="card-header">
            <h3>Input Parameters</h3>
          </div>
          <div className="card-body">
            <div className="form-group">
              <label className="form-label">Selling Price (₹)</label>
              <input
                type="number"
                step="1"
                min="1"
                className="form-input"
                value={sellPrice}
                onChange={e => setSellPrice(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Cost Price (₹)</label>
              <input
                type="number"
                step="1"
                min="0"
                className="form-input"
                value={costPrice}
                onChange={e => setCostPrice(e.target.value)}
              />
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Discount Percentage: {discountPct}%</label>
              </div>
              <input
                type="range"
                min="0"
                max="60"
                step="1"
                style={{ width: '100%', accentColor: 'var(--teal)' }}
                value={discountPct}
                onChange={e => setDiscountPct(e.target.value)}
              />
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Merchant Minimum Required Margin: {minMarginPct}%</label>
              </div>
              <input
                type="range"
                min="5"
                max="40"
                step="1"
                style={{ width: '100%', accentColor: 'var(--warning)' }}
                value={minMarginPct}
                onChange={e => setMinMarginPct(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Results Card */}
        <div className="card">
          <div className="card-header">
            <h3>Real-Time Calculation Output</h3>
            {calcResult && <Badge status={calcResult.status} />}
          </div>
          <div className="card-body">
            {calcResult ? (
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 18 }}>
                  <div style={{ background: 'var(--bg)', padding: 12, borderRadius: 8 }}>
                    <div className="stat-label">Before Discount GP</div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--heading)' }}>
                      {fmt(calcResult.before_gp)}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      Margin: {pct(calcResult.before_pct)}
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg)', padding: 12, borderRadius: 8 }}>
                    <div className="stat-label">After Discount GP</div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: calcResult.after_gp < 0 ? 'var(--error)' : 'var(--teal)' }}>
                      {fmt(calcResult.after_gp)}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      Margin: {pct(calcResult.after_pct)}
                    </div>
                  </div>
                </div>

                <div style={{ background: '#F8FAFC', padding: 14, borderRadius: 8, border: '1px solid var(--border)', marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: 'var(--muted)' }}>Post-Discount Margin:</span>
                    <strong style={{ fontSize: 15, color: calcResult.status === 'blocked' ? 'var(--error)' : 'var(--success)' }}>
                      {pct(calcResult.after_pct)}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: 'var(--muted)' }}>Required Volume Uplift:</span>
                    <strong style={{ fontSize: 15, color: 'var(--heading)' }}>
                      {calcResult.required_volume_uplift_pct != null ? `+${pct(calcResult.required_volume_uplift_pct)}` : 'N/A'}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, color: 'var(--muted)' }}>Status Evaluation:</span>
                    <Badge status={calcResult.status} />
                  </div>
                </div>

                {/* Status rules explanation */}
                {calcResult.status === 'blocked' && (
                  <div className="alert alert-error">
                    <strong>⛔ Status: Blocked</strong><br />
                    Post-discount margin is below your safety threshold ({minMarginPct}%). Selling at this discount requires excessive sales volume (+{pct(calcResult.required_volume_uplift_pct)}) just to break even on profit!
                    {calcResult.alternative && (
                      <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(185,28,28,0.2)' }}>
                        <strong>✨ Recommended Safe Alternative:</strong><br />
                        {calcResult.alternative.message}
                        <button
                          className="btn btn-warning btn-sm"
                          style={{ marginTop: 6 }}
                          onClick={() => setDiscountPct(calcResult.alternative.discount_pct)}
                        >
                          Apply {calcResult.alternative.discount_pct}% Discount
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {calcResult.status === 'caution' && (
                  <div className="alert alert-warning">
                    <strong>⚠️ Status: Caution</strong><br />
                    Margin is within 2 points of your minimum threshold. Monitor sales volumes closely.
                  </div>
                )}

                {calcResult.status === 'ok' && (
                  <div className="alert alert-success">
                    <strong>✓ Status: Healthy</strong><br />
                    Post-discount margin comfortably exceeds your {minMarginPct}% threshold.
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* Formula Documentation Card */}
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <h3>📐 Official Spec Formulas (Hackathon Standard)</h3>
        </div>
        <div className="card-body" style={{ fontFamily: 'monospace', fontSize: 13, background: '#F1F5F9', color: '#0F172A' }}>
          <div>gross_profit_per_unit = selling_price - cost_price</div>
          <div>margin_pct            = gross_profit_per_unit / selling_price * 100</div>
          <div>after_discount_price  = selling_price * (1 - discount_pct / 100)</div>
          <div>after_gp              = after_discount_price - cost_price</div>
          <div>required_volume_uplift = (before_gp / after_gp - 1) * 100</div>
          <div style={{ marginTop: 10, color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: 12 }}>
            💡 <em>Rule of Thumb:</em> In the ₹100 price / ₹70 cost / 20% discount example, before GP is ₹30 and after GP is ₹10. Because GP drops by 3x, the shopkeeper must sell 3x the volume (200% uplift) just to earn the exact same total rupee profit.
          </div>
        </div>
      </div>
    </div>
  )
}

