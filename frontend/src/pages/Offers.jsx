import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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

  if (loading) return <Loading text="Loading active offers & experiments..." />
  if (error) return <ErrorMsg message={error} />

  return (
    <div>
      <div style={{ marginBottom: 22 }}>
        <h2 style={{ fontSize: 20, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em' }}>
          Active Offers & In-Shop Experiments
        </h2>
        <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
          WhatsApp Status-ready marketing copy, printable counter posters with QR codes, and rigorous A/B experiment measurement against control groups.
        </p>
      </div>

      <div className="alert alert-info" style={{ marginBottom: 22 }}>
        <strong>📊 Scientific Measurement Notice:</strong> Net lift is measured by comparing treatment items against similar control products within your shop. All demo results are strictly labelled as simulated.
      </div>

      {offers.length === 0 ? (
        <div className="card" style={{ padding: 48, textAlign: 'center' }}>
          <div style={{ fontSize: 36, marginBottom: 10 }}>🎯</div>
          <h3 style={{ fontSize: 16, fontWeight: 650, color: 'var(--heading)' }}>No active offers yet</h3>
          <p style={{ color: 'var(--muted)', fontSize: 13, maxWidth: 420, margin: '8px auto 20px' }}>
            Approve a recommendation to automatically generate marketing copy, in-shop posters, and experiment tracking.
          </p>
          <Link to="/recommendations" className="btn btn-primary">
            Review Recommendations →
          </Link>
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
                    <strong style={{ fontSize: 15, color: 'var(--heading)' }}>Offer #{o.id}</strong>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                      Valid: {o.valid_from} to {o.valid_to}
                    </div>
                  </div>
                  <Badge status={o.is_active ? 'approved' : 'rejected'} />
                </div>

                <div className="card-body">
                  {/* WhatsApp Status Creative Preview */}
                  <div style={{
                    background: 'linear-gradient(135deg, #3B2FA8 0%, #7B6CF6 100%)',
                    color: '#FFFFFF',
                    padding: 16,
                    borderRadius: 12,
                    marginBottom: 16,
                    boxShadow: '0 10px 28px rgba(123,108,246,0.35)',
                    transition: 'transform var(--duration) var(--ease-smooth)'
                  }}>
                    <div style={{
                      fontSize: 12,
                      color: '#C8F560',
                      fontWeight: 650,
                      marginBottom: 8,
                      display: 'flex',
                      justifyContent: 'space-between',
                      letterSpacing: '0.04em'
                    }}>
                      <span>📱 WHATSAPP STATUS READY</span>
                      <span style={{ background: 'rgba(255,255,255,0.2)', padding: '2px 8px', borderRadius: 10 }}>LIVE</span>
                    </div>
                    <div style={{ fontSize: 15, whiteSpace: 'pre-line', lineHeight: 1.5 }}>
                      {copy.whatsapp || 'Special Offer Available Today! Visit store to avail.'}
                    </div>
                  </div>

                  {/* Units Capping Rule */}
                  <div style={{
                    background: 'var(--surface)',
                    padding: 14,
                    borderRadius: 'var(--radius-sm)',
                    marginBottom: 16,
                    fontSize: 13
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                      <span className="stat-label">Units Cap:</span>
                      <strong style={{ color: 'var(--heading)' }}>{o.units_cap || 40} units</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span className="stat-label">Redeemed:</span>
                      <span style={{ fontWeight: 650, color: 'var(--teal)' }}>{o.units_redeemed || 0} / {o.units_cap || 40}</span>
                    </div>
                    <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 6, lineHeight: 1.4 }}>
                      Offer automatically closes once {o.units_cap || 40} customers redeem to protect your risk budget.
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
        <Modal title="Store Front Counter Poster" onClose={() => setSelectedPoster(null)}>
          <div style={{
            border: '2px dashed var(--teal)',
            padding: 28,
            textAlign: 'center',
            background: 'var(--white)',
            borderRadius: 14
          }}>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--teal)', fontWeight: 800 }}>
              DukaanSaathi Partner Merchant
            </div>
            <h2 style={{ fontSize: 22, color: 'var(--heading)', margin: '14px 0 8px', fontWeight: 800 }}>
              {selectedPoster.headline || 'SPECIAL OFFER'}
            </h2>
            <p style={{ fontSize: 14, color: 'var(--body)', marginBottom: 20 }}>
              {selectedPoster.body || 'Visit today for exclusive discounts!'}
            </p>

            {/* QR Code Placeholder */}
            <div style={{
              margin: '0 auto 16px',
              width: 140,
              height: 140,
              background: '#FFFFFF', color: '#0A0A0A',
              border: '3px solid var(--accent)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 12,
              boxShadow: 'var(--shadow-xs)'
            }}>
              <span style={{ fontSize: 36 }}>📱</span>
              <span style={{ fontSize: 11, fontWeight: 700, marginTop: 4, letterSpacing: '0.04em' }}>PAYTM QR SCAN</span>
            </div>

            <button className="btn btn-success btn-sm" style={{ pointerEvents: 'none' }}>
              {selectedPoster.cta || 'Avail Offer at Counter'}
            </button>

            <div style={{ marginTop: 18, fontSize: 11, color: 'var(--muted)' }}>
              {selectedPoster.disclaimer || '[Simulated poster — printable counter format]'}
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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <span className="badge badge-synthetic">Simulated In-Shop Control</span>
                <DataLabel label={expResult.data_label} />
              </div>

              {/* Net Lift & GP change cards */}
              <div className="grid-2" style={{ marginBottom: 18 }}>
                <div style={{
                  background: 'var(--surface)',
                  padding: 16,
                  borderRadius: 'var(--radius-sm)',
                  borderLeft: '4px solid var(--teal)'
                }}>
                  <div className="stat-label">Net Sales Lift</div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--teal)', marginTop: 4, letterSpacing: '-0.02em' }}>
                    +{pct(expResult.net_lift_pct)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                    Treatment lift minus control lift
                  </div>
                </div>

                <div style={{
                  background: 'var(--surface)',
                  padding: 16,
                  borderRadius: 'var(--radius-sm)',
                  borderLeft: `4px solid ${expResult.gp_change_inr >= 0 ? 'var(--success)' : 'var(--error)'}`
                }}>
                  <div className="stat-label">Gross Profit Change</div>
                  <div style={{
                    fontSize: 26,
                    fontWeight: 800,
                    color: expResult.gp_change_inr >= 0 ? 'var(--success)' : 'var(--error)',
                    marginTop: 4,
                    letterSpacing: '-0.02em'
                  }}>
                    {expResult.gp_change_inr >= 0 ? '+' : ''}{fmt(expResult.gp_change_inr)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                    Net profit after discount expense
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
                      <td><strong style={{ color: 'var(--heading)' }}>Treatment (Offer Items)</strong></td>
                      <td>{expResult.treatment?.before_units}</td>
                      <td>{expResult.treatment?.after_units}</td>
                      <td style={{ color: 'var(--teal)', fontWeight: 700 }}>
                        +{pct(expResult.treatment?.change_pct)}
                      </td>
                    </tr>
                    <tr>
                      <td><strong style={{ color: 'var(--muted)' }}>Control (Similar Items)</strong></td>
                      <td>{expResult.control?.before_units}</td>
                      <td>{expResult.control?.after_units}</td>
                      <td style={{ color: 'var(--muted)', fontWeight: 600 }}>
                        +{pct(expResult.control?.change_pct)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="alert alert-info" style={{ fontSize: 13, marginBottom: 10 }}>
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
