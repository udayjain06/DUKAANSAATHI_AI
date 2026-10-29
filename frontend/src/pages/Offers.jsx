import React, { useEffect, useState } from 'react'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, Badge, DataLabel, Modal } from '../components/UI'

export default function Offers() {
  const [offers, setOffers] = useState([])
  const [experiments, setExperiments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedExp, setSelectedExp] = useState(null)
  const [expResult, setExpResult] = useState(null)
  const [expLoading, setExpLoading] = useState(false)
  const [selectedPoster, setSelectedPoster] = useState(null)

  const load = () => {
    setLoading(true)
    Promise.all([
      api.get('/offer'),
      api.get('/experiments'),
    ])
      .then(([o, e]) => {
        setOffers(o.data)
        setExperiments(e.data)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleViewExperiment = async (expId) => {
    setSelectedExp(expId)
    setExpLoading(true)
    try {
      const res = await api.get(`/experiments/${expId}/result`)
      setExpResult(res.data)
    } catch (err) {
      alert(err.response?.data?.detail || err.message)
    } finally {
      setExpLoading(false)
    }
  }

  if (loading) return <Loading text="Loading active offers and experiments..." />
  if (error) return <ErrorMsg message={error} />

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, color: 'var(--heading)' }}>Active Offers & In-Shop Experiments</h2>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>
          WhatsApp Status-ready creatives, printable posters with QR code, and rigorous A/B experiment measurement against shop control groups.
        </p>
      </div>

      <div className="alert alert-info" style={{ marginBottom: 20 }}>
        <strong>📊 Scientific Measurement Notice:</strong> Net lift is measured by comparing treatment items against similar control products within your shop. All demo results are strictly labelled as simulated.
      </div>

      {offers.length === 0 ? (
        <div className="card" style={{ padding: 40, textAlign: 'center' }}>
          <p style={{ color: 'var(--muted)', marginBottom: 12 }}>No active offers created yet.</p>
          <a href="/recommendations" className="btn btn-primary">
            Review & Approve a Recommendation First →
          </a>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20, marginBottom: 30 }}>
          {offers.map(o => {
            const copy = o.copy || {}
            const poster = o.poster || {}
            const exp = experiments.find(e => e.offer_id === o.id)

            return (
              <div key={o.id} className="card">
                <div className="card-header">
                  <div>
                    <strong>Offer #{o.id}</strong>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      Valid: {o.valid_from} to {o.valid_to}
                    </div>
                  </div>
                  <Badge status={o.is_active ? 'approved' : 'rejected'} />
                </div>

                <div className="card-body">
                  {/* WhatsApp Status Creative Preview */}
                  <div style={{
                    background: '#075E54',
                    color: '#FFFFFF',
                    padding: 16,
                    borderRadius: 10,
                    marginBottom: 16,
                    fontFamily: 'system-ui',
                    boxShadow: '0 2px 8px rgba(7,94,84,0.25)'
                  }}>
                    <div style={{ fontSize: 11, color: '#A7F3D0', fontWeight: 600, marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
                      <span>📱 WhatsApp Status Ready Copy</span>
                      <span>🟢 Live</span>
                    </div>
                    <div style={{ fontSize: 14, whiteSpace: 'pre-line', lineHeight: 1.4 }}>
                      {copy.whatsapp || 'Special Offer Available Today!'}
                    </div>
                  </div>

                  {/* Units Capping Rule */}
                  <div style={{ background: 'var(--bg)', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 13 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span className="stat-label">Maximum Units Cap:</span>
                      <strong style={{ color: 'var(--heading)' }}>{o.units_cap || 40} units</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span className="stat-label">Redeemed:</span>
                      <span style={{ fontWeight: 600, color: 'var(--teal)' }}>{o.units_redeemed || 0} / {o.units_cap || 40}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                      Offer automatically closes once {o.units_cap || 40} customers redeem to protect merchant risk budget.
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 10 }}>
                    <button
                      className="btn btn-outline btn-sm"
                      style={{ flex: 1 }}
                      onClick={() => setSelectedPoster(poster)}
                    >
                      🖨️ View Poster / QR
                    </button>
                    {exp && (
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ flex: 1 }}
                        onClick={() => handleViewExperiment(exp.id)}
                      >
                        🔬 View Results
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Poster Preview Modal */}
      {selectedPoster && (
        <Modal title="Store Front Poster Preview" onClose={() => setSelectedPoster(null)}>
          <div style={{
            border: '3px dashed var(--teal)',
            padding: 24,
            textAlign: 'center',
            background: 'var(--white)',
            borderRadius: 8
          }}>
            <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--teal-dark)', fontWeight: 800 }}>
              DukaanSaathi Partner Shop
            </div>
            <h2 style={{ fontSize: 24, color: 'var(--heading)', margin: '12px 0 8px' }}>
              {selectedPoster.headline || 'SPECIAL OFFER'}
            </h2>
            <p style={{ fontSize: 15, color: 'var(--body)', marginBottom: 20 }}>
              {selectedPoster.body || 'Visit today for exclusive discounts!'}
            </p>

            {/* QR Code Placeholder */}
            <div style={{
              margin: '0 auto 16px',
              width: 140,
              height: 140,
              background: '#F8FAFC',
              border: '2px solid #0F172A',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 8
            }}>
              <span style={{ fontSize: 36 }}>📱</span>
              <span style={{ fontSize: 10, fontWeight: 700, marginTop: 4 }}>SCAN WITH PAYTM</span>
            </div>

            <button className="btn btn-success btn-sm" style={{ pointerEvents: 'none' }}>
              {selectedPoster.cta || 'Avail Offer at Counter'}
            </button>

            <div style={{ marginTop: 16, fontSize: 11, color: 'var(--muted)' }}>
              {selectedPoster.disclaimer || '[Simulated poster — printable format]'}
            </div>
          </div>
        </Modal>
      )}

      {/* Experiment Results Modal */}
      {selectedExp && (
        <Modal
          title={`Experiment Results (ID: ${selectedExp})`}
          onClose={() => { setSelectedExp(null); setExpResult(null); }}
        >
          {expLoading ? (
            <Loading text="Retrieving in-shop experiment calculations..." />
          ) : expResult ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <span className="badge badge-synthetic">Simulated In-Shop Control</span>
                <DataLabel label={expResult.data_label} />
              </div>

              {/* Net Lift & GP change cards */}
              <div className="grid-2" style={{ marginBottom: 16 }}>
                <div style={{ background: 'var(--bg)', padding: 14, borderRadius: 8, borderLeft: '4px solid var(--teal)' }}>
                  <div className="stat-label">Net Sales Lift</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--teal)', marginTop: 4 }}>
                    +{pct(expResult.net_lift_pct)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                    Treatment change minus control change
                  </div>
                </div>

                <div style={{ background: 'var(--bg)', padding: 14, borderRadius: 8, borderLeft: '4px solid var(--success)' }}>
                  <div className="stat-label">Gross Profit Change</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: expResult.gp_change_inr >= 0 ? 'var(--success)' : 'var(--error)', marginTop: 4 }}>
                    {expResult.gp_change_inr >= 0 ? '+' : ''}{fmt(expResult.gp_change_inr)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                    Total after-cost profit impact
                  </div>
                </div>
              </div>

              {/* Treatment vs Control comparison */}
              <div className="table-wrap" style={{ marginBottom: 16 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Group</th>
                      <th>Before Units</th>
                      <th>After Units</th>
                      <th>Lift %</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>Treatment (Offer Items)</strong></td>
                      <td>{expResult.treatment?.before_units}</td>
                      <td>{expResult.treatment?.after_units}</td>
                      <td style={{ color: 'var(--teal)', fontWeight: 700 }}>
                        +{pct(expResult.treatment?.change_pct)}
                      </td>
                    </tr>
                    <tr>
                      <td><strong>Control (Similar Items)</strong></td>
                      <td>{expResult.control?.before_units}</td>
                      <td>{expResult.control?.after_units}</td>
                      <td style={{ color: 'var(--muted)', fontWeight: 600 }}>
                        +{pct(expResult.control?.change_pct)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="alert alert-info" style={{ fontSize: 13, marginBottom: 8 }}>
                <strong>💡 Engine Interpretation:</strong> {expResult.interpretation}
              </div>

              <div style={{ fontSize: 11, color: 'var(--muted)', fontStyle: 'italic' }}>
                ⚠️ {expResult.disclaimer}
              </div>
            </div>
          ) : null}
        </Modal>
      )}
    </div>
  )
}

