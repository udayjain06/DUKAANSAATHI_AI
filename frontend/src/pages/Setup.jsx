import React, { useEffect, useState } from 'react'
import api from '../api'
import { Loading, ErrorMsg } from '../components/UI'

export default function Setup() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [form, setForm] = useState({
    name: 'Sharma General Store',
    shop_type: 'kirana',
    min_margin_pct: 15.0,
    language: 'hi',
    risk_budget_inr: 400.0,
    phone: '9999999999',
  })

  useEffect(() => {
    api.get('/merchant/profile')
      .then(r => {
        setForm({
          name: r.data.name || 'Sharma General Store',
          shop_type: r.data.shop_type || 'kirana',
          min_margin_pct: r.data.min_margin_pct || 15.0,
          language: r.data.language || 'hi',
          risk_budget_inr: r.data.risk_budget_inr || 400.0,
          phone: r.data.phone || '',
        })
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccessMsg(null)
    try {
      await api.post('/merchant/setup', {
        name: form.name,
        shop_type: form.shop_type,
        min_margin_pct: parseFloat(form.min_margin_pct),
        language: form.language,
        risk_budget_inr: parseFloat(form.risk_budget_inr),
        phone: form.phone,
      })
      setSuccessMsg('Shop settings updated successfully!')
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleResetDatabase = async () => {
    if (!window.confirm('Reset and re-seed the demo database? All data will be restored to default 8-week synthetic sales.')) {
      return
    }
    setResetting(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api.post('/reset')
      setSuccessMsg(res.data.message || 'Database reset successfully!')
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setResetting(false)
    }
  }

  if (loading) return <Loading text="Loading shop settings..." />

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, color: 'var(--heading)' }}>Shop Configuration & Demo Controls</h2>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>
          Configure shop category, minimum profit margin thresholds, risk budgets, and language.
        </p>
      </div>

      {error && <ErrorMsg message={error} />}
      {successMsg && <div className="alert alert-success">{successMsg}</div>}

      <div className="grid-2">
        {/* Setup Form */}
        <div className="card">
          <div className="card-header">
            <h3>Merchant Profile</h3>
          </div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Shop Name</label>
                <input
                  className="form-input"
                  required
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Shop Category</label>
                <select
                  className="form-select"
                  value={form.shop_type}
                  onChange={e => setForm({ ...form, shop_type: e.target.value })}
                >
                  <option value="kirana">Kirana / General Store</option>
                  <option value="bakery">Bakery / Confectionery</option>
                </select>
                <small style={{ color: 'var(--muted)', marginTop: 4, display: 'block' }}>
                  Determines synthetic data baseline and wholesale product categories.
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Minimum Required Gross Margin (%)</label>
                <input
                  type="number"
                  step="0.5"
                  min="5"
                  max="50"
                  required
                  className="form-input"
                  value={form.min_margin_pct}
                  onChange={e => setForm({ ...form, min_margin_pct: e.target.value })}
                />
                <small style={{ color: 'var(--muted)', marginTop: 4, display: 'block' }}>
                  Offers producing margins below this threshold will be blocked to protect profit.
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Risk Budget per Offer (₹)</label>
                <input
                  type="number"
                  step="10"
                  min="50"
                  required
                  className="form-input"
                  value={form.risk_budget_inr}
                  onChange={e => setForm({ ...form, risk_budget_inr: e.target.value })}
                />
                <small style={{ color: 'var(--muted)', marginTop: 4, display: 'block' }}>
                  Controls the maximum permitted customer unit cap: <code>units_cap = budget / loss_per_unit</code>.
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Preferred Language</label>
                <select
                  className="form-select"
                  value={form.language}
                  onChange={e => setForm({ ...form, language: e.target.value })}
                >
                  <option value="hi">हिंदी (Hindi)</option>
                  <option value="en">English</option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={saving}
                style={{ width: '100%', marginTop: 8 }}
              >
                {saving ? 'Saving...' : 'Save Configuration'}
              </button>
            </form>
          </div>
        </div>

        {/* Demo Database Controls */}
        <div className="card">
          <div className="card-header">
            <h3>🔄 Demo Management & Seed Reset</h3>
          </div>
          <div className="card-body">
            <div className="alert alert-info">
              <strong>Fixed Random Seed (seed=42):</strong> Results remain 100% reproducible for judges and live demonstrations.
            </div>
            <p style={{ fontSize: 13, color: 'var(--body)', marginBottom: 16 }}>
              Need to restart the live demo from scratch? Click below to reset all tables and re-seed 8 weeks of synthetic sales with Monday dips, weekend boosts, and salary window patterns.
            </p>
            <button
              className="btn btn-warning"
              disabled={resetting}
              onClick={handleResetDatabase}
              style={{ width: '100%' }}
            >
              {resetting ? 'Resetting Database...' : '⚡ One-Click Reset & Re-Seed Database'}
            </button>

            <div style={{ marginTop: 24, padding: 14, background: '#F1F5F9', borderRadius: 8, fontSize: 12 }}>
              <strong style={{ color: 'var(--heading)' }}>Expected Pattern Highlights:</strong>
              <ul style={{ paddingLeft: 18, marginTop: 6, lineHeight: 1.6, color: 'var(--body)' }}>
                <li>Mondays: 12% to 18% sales dip (weak-day trigger)</li>
                <li>Dates 1-7: Salary-window purchasing bump (+10-15%)</li>
                <li>Weekends: Friday-Sunday higher footfall</li>
                <li>All data tagged with <code>is_synthetic: true</code></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

