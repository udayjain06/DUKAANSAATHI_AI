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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22, flexWrap: 'wrap', gap: 14 }}>
        <div>
          <h2 style={{ fontSize: 20, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Deterministic Margin Engine (Pitch Core)
          </h2>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
            All financial calculations run purely in deterministic Python — strictly no AI hallucinations.
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
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <label className="form-label" style={{ margin: 0 }}>Discount Percentage</label>
                <span style={{ fontWeight: 700, color: 'var(--teal)', fontSize: 13 }}>{discountPct}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="60"
                step="1"
                style={{ width: '100%', accentColor: 'var(--teal)', height: 6, cursor: 'pointer' }}
                value={discountPct}
                onChange={e => setDiscountPct(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <label className="form-label" style={{ margin: 0 }}>Merchant Minimum Required Margin</label>
                <span style={{ fontWeight: 700, color: 'var(--warning)', fontSize: 13 }}>{minMarginPct}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="40"
                step="1"
                style={{ width: '100%', accentColor: 'var(--warning)', height: 6, cursor: 'pointer' }}
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
                  <div style={{ background: 'var(--surface)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
                    <div className="stat-label">Before Discount GP</div>
                    <div style={{ fontSize: 22, fontWeight: 750, color: 'var(--heading)', marginTop: 4, letterSpacing: '-0.02em' }}>
                      {fmt(calcResult.before_gp)}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                      Margin: {pct(calcResult.before_pct)}
                    </div>
                  </div>

                  <div style={{ background: 'var(--surface)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
                    <div className="stat-label">After Discount GP</div>
                    <div style={{
                      fontSize: 22,
                      fontWeight: 750,
                      color: calcResult.after_gp < 0 ? 'var(--error)' : 'var(--teal)',
                      marginTop: 4,
                      letterSpacing: '-0.02em'
                    }}>
                      {fmt(calcResult.after_gp)}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                      Margin: {pct(calcResult.after_pct)}
                    </div>
                  </div>
                </div>

                {/* Margin meter */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
                    <span style={{ color: 'var(--muted)' }}>Margin Safety Meter</span>
                    <span style={{ fontWeight: 600, color: calcResult.status === 'blocked' ? 'var(--error)' : 'var(--success)' }}>
                      {pct(calcResult.after_pct)} (Min: {minMarginPct}%)
                    </span>
                  </div>
                  <div className="margin-meter">
                    <div
                      className="margin-meter-fill"
                      style={{
                        width: `${Math.max(0, Math.min(100, (calcResult.after_pct / 50) * 100))}%`,
                        background: calcResult.status === 'blocked' ? 'var(--error)' : calcResult.status === 'caution' ? 'var(--warning)' : 'var(--success)'
                      }}
                    />
                  </div>
                </div>

                <div style={{
                  background: 'var(--bg)',
                  padding: 14,
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  marginBottom: 16
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: 'var(--muted)' }}>Post-Discount Margin:</span>
                    <strong style={{ fontSize: 14, color: calcResult.status === 'blocked' ? 'var(--error)' : 'var(--success)' }}>
                      {pct(calcResult.after_pct)}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: 'var(--muted)' }}>Required Volume Uplift:</span>
                    <strong style={{ fontSize: 14, color: 'var(--heading)' }}>
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
                  <div className="alert alert-error" style={{ marginBottom: 0 }}>
                    <strong>⛔ Status: Blocked</strong><br />
                    Post-discount margin is below your safety threshold ({minMarginPct}%). Selling at this discount requires excessive sales volume (+{pct(calcResult.required_volume_uplift_pct)}) just to break even on profit!
                    {calcResult.alternative && (
                      <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(255,107,107,0.25)' }}>
                        <strong>✨ Recommended Safe Alternative:</strong><br />
                        {calcResult.alternative.message}
                        <div style={{ marginTop: 8 }}>
                          <button
                            className="btn btn-warning btn-sm"
                            onClick={() => setDiscountPct(calcResult.alternative.discount_pct)}
                          >
                            Apply {calcResult.alternative.discount_pct}% Discount
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {calcResult.status === 'caution' && (
                  <div className="alert alert-warning" style={{ marginBottom: 0 }}>
                    <strong>⚠️ Status: Caution</strong><br />
                    Margin is within 2 points of your minimum threshold. Monitor sales volumes closely.
                  </div>
                )}

                {calcResult.status === 'ok' && (
                  <div className="alert alert-success" style={{ marginBottom: 0 }}>
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
        <div className="card-body" style={{ fontFamily: 'monospace', fontSize: 12.5, background: 'var(--surface)', color: 'var(--heading)', borderRadius: '0 0 var(--radius) var(--radius)' }}>
          <div style={{ padding: '3px 0' }}>gross_profit_per_unit = selling_price - cost_price</div>
          <div style={{ padding: '3px 0' }}>margin_pct            = gross_profit_per_unit / selling_price * 100</div>
          <div style={{ padding: '3px 0' }}>after_discount_price  = selling_price * (1 - discount_pct / 100)</div>
          <div style={{ padding: '3px 0' }}>after_gp              = after_discount_price - cost_price</div>
          <div style={{ padding: '3px 0' }}>required_volume_uplift = (before_gp / after_gp - 1) * 100</div>
          <div style={{ marginTop: 12, color: 'var(--muted)', fontFamily: 'var(--font-sans)', fontSize: 12, lineHeight: 1.5 }}>
            💡 <em>Rule of Thumb:</em> In the ₹100 price / ₹70 cost / 20% discount example, before GP is ₹30 and after GP is ₹10. Because GP drops by 3x, the shopkeeper must sell 3x the volume (200% uplift) just to earn the exact same total rupee profit.
          </div>
        </div>
      </div>
    </div>
  )
}
