import React, { useEffect, useState } from 'react'
import api, { fmt } from '../api'
import { Loading, ErrorMsg, Badge, Modal } from '../components/UI'

export default function Payment() {
  const [plansData, setPlansData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedPlan, setSelectedPlan] = useState('monthly')
  const [initiating, setInitiating] = useState(false)
  const [paytmPayload, setPaytmPayload] = useState(null)
  const [checkOrderId, setCheckOrderId] = useState('')
  const [orderStatus, setOrderStatus] = useState(null)
  const [statusLoading, setStatusLoading] = useState(false)

  const loadPlans = () => {
    setLoading(true)
    api.get('/payment/plans')
      .then(r => setPlansData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadPlans() }, [])

  const handleInitiate = async (planId) => {
    setInitiating(true)
    setError(null)
    setPaytmPayload(null)

    try {
      const res = await api.post('/payment/initiate', { plan: planId || selectedPlan })
      setPaytmPayload(res.data)
      setCheckOrderId(res.data.order_id)
    } catch (err) {
      const resp = err.response?.data
      if (resp?.error === 'payment_not_configured') {
        setError(resp.message)
      } else {
        setError(resp?.detail || err.message)
      }
    } finally {
      setInitiating(false)
    }
  }

  const handleCheckStatus = async () => {
    if (!checkOrderId.trim()) return
    setStatusLoading(true)
    try {
      const res = await api.get(`/payment/status/${checkOrderId.trim()}`)
      setOrderStatus(res.data)
    } catch (err) {
      alert(err.response?.data?.detail || err.message)
    } finally {
      setStatusLoading(false)
    }
  }

  const handleProceedToPaytmGateway = () => {
    if (!paytmPayload) return
    const form = document.createElement('form')
    form.setAttribute('method', 'post')
    form.setAttribute('action', paytmPayload.txn_url)
    form.setAttribute('name', 'paytm_form')

    for (const key in paytmPayload.paytm_params) {
      if (Object.prototype.hasOwnProperty.call(paytmPayload.paytm_params, key)) {
        const input = document.createElement('input')
        input.setAttribute('type', 'hidden')
        input.setAttribute('name', key)
        input.setAttribute('value', paytmPayload.paytm_params[key])
        form.appendChild(input)
      }
    }

    document.body.appendChild(form)
    form.submit()
  }

  if (loading) return <Loading text="Loading subscription details..." />

  const isConfigured = plansData?.configured

  return (
    <div>
      <div style={{ marginBottom: 22 }}>
        <h2 style={{ fontSize: 20, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em' }}>
          DukaanSaathi Pro — Subscription & Paytm Gateway
        </h2>
        <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
          Official server-side Paytm Payment Gateway integration with checksum verification & status enquiry.
        </p>
      </div>

      {!isConfigured ? (
        <div className="alert alert-warning" style={{ marginBottom: 24 }}>
          <strong>⚠️ Paytm Merchant Credentials Required:</strong><br />
          To process live or staging payments, supply your <code>PAYTM_MID</code> and <code>PAYTM_MERCHANT_KEY</code> in the backend <code>.env</code> file.
          <div style={{ marginTop: 6, fontSize: 12.5, lineHeight: 1.5 }}>
            Obtain test credentials from: <a href="https://business.paytm.com/" target="_blank" rel="noreferrer" style={{ textDecoration: 'underline', color: 'var(--teal-dark)', fontWeight: 600 }}>https://business.paytm.com/</a>.
            The backend architecture, HMAC checksum generation, callback webhook, and verification routes are fully built and ready.
          </div>
        </div>
      ) : (
        <div className="alert alert-success" style={{ marginBottom: 24 }}>
          <strong>✓ Paytm Gateway Active:</strong> Environment: <code>{plansData?.env || 'staging'}</code>. Ready to process real transactions.
        </div>
      )}

      {error && <ErrorMsg message={error} />}

      {/* Subscription Plans */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20, marginBottom: 30 }}>
        {(plansData?.plans || []).map(p => {
          const isSelected = selectedPlan === p.id
          return (
            <div
              key={p.id}
              className="card"
              style={{
                border: isSelected ? '2px solid var(--teal)' : '1px solid var(--border)',
                cursor: 'pointer',
                position: 'relative',
                transform: isSelected ? 'translateY(-2px)' : 'none',
                boxShadow: isSelected ? 'var(--shadow-md)' : 'var(--shadow)',
                transition: 'all var(--duration) var(--ease-smooth)'
              }}
              onClick={() => setSelectedPlan(p.id)}
            >
              {isSelected && (
                <div style={{
                  position: 'absolute', top: -10, right: 18,
                  background: 'var(--teal)', color: '#fff',
                  fontSize: 10.5, fontWeight: 700, padding: '2px 9px', borderRadius: 'var(--radius-full)',
                  letterSpacing: '0.04em'
                }}>
                  RECOMMENDED
                </div>
              )}
              <div className="card-header">
                <h3>{p.name}</h3>
              </div>
              <div className="card-body">
                <div style={{ fontSize: 30, fontWeight: 800, color: 'var(--heading)', marginBottom: 8, letterSpacing: '-0.02em' }}>
                  {fmt(p.amount)}
                </div>
                <ul style={{ paddingLeft: 18, fontSize: 13, color: 'var(--body)', lineHeight: 1.8 }}>
                  <li>Automated weak-day opportunity alerts</li>
                  <li>Deterministic margin loss protection</li>
                  <li>WhatsApp Status & counter poster generator</li>
                  <li>In-shop control group experiment analysis</li>
                  <li>Priority AI Assistant support</li>
                </ul>
                <button
                  className={`btn ${isSelected ? 'btn-primary' : 'btn-ghost'}`}
                  style={{ width: '100%', marginTop: 20 }}
                  disabled={initiating}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleInitiate(p.id)
                  }}
                >
                  {initiating && isSelected ? 'Creating Order...' : `Subscribe for ${fmt(p.amount)}`}
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Transaction Details Modal if Order Initiated */}
      {paytmPayload && (
        <Modal
          title={`Paytm Payment Order: ${paytmPayload.order_id}`}
          onClose={() => setPaytmPayload(null)}
          footer={
            <>
              <button className="btn btn-ghost" onClick={() => setPaytmPayload(null)}>Cancel</button>
              <button className="btn btn-success" onClick={handleProceedToPaytmGateway}>
                Proceed to Paytm Payment Gateway →
              </button>
            </>
          }
        >
          <div>
            <div className="alert alert-info" style={{ fontSize: 13, marginBottom: 14 }}>
              Backend generated order #{paytmPayload.order_id} with secure HMAC-SHA256 checksum signature.
            </div>
            <div style={{ background: 'var(--surface)', padding: 16, borderRadius: 'var(--radius-sm)', fontSize: 13, marginBottom: 16 }}>
              <div style={{ marginBottom: 4 }}><strong>Plan:</strong> {paytmPayload.plan}</div>
              <div style={{ marginBottom: 4 }}><strong>Amount:</strong> {fmt(paytmPayload.amount)}</div>
              <div style={{ marginBottom: 4 }}><strong>Environment:</strong> {paytmPayload.env}</div>
              <div style={{ marginBottom: 8 }}><strong>Gateway Target:</strong> <code style={{ fontSize: 11 }}>{paytmPayload.txn_url}</code></div>
              <div><strong>Checksum (HMAC):</strong></div>
              <code style={{ fontSize: 11, wordBreak: 'break-all', display: 'block', background: '#E2E8F0', padding: 8, borderRadius: 6, marginTop: 4 }}>
                {paytmPayload.paytm_params?.CHECKSUMHASH}
              </code>
            </div>
            <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>
              Proceeding opens the official Paytm staging checkout. After payment, Paytm sends server-to-server webhook callback to <code>/api/payment/callback</code>.
            </p>
          </div>
        </Modal>
      )}

      {/* Check Order Status Section */}
      <div className="card">
        <div className="card-header">
          <h3>🔍 Server-Side Payment Status Verification</h3>
        </div>
        <div className="card-body">
          <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14 }}>
            Never trusts client claims. Verifies directly against database post-callback & Paytm status enquiry API.
          </p>
          <div style={{ display: 'flex', gap: 10, maxWidth: 500, marginBottom: 18, flexWrap: 'wrap' }}>
            <input
              className="form-input"
              placeholder="Enter Order ID (e.g. DS_123456...)"
              value={checkOrderId}
              onChange={e => setCheckOrderId(e.target.value)}
              style={{ flex: 1, minWidth: 200 }}
            />
            <button
              className="btn btn-primary"
              disabled={statusLoading || !checkOrderId.trim()}
              onClick={handleCheckStatus}
            >
              {statusLoading ? 'Verifying...' : 'Check Status'}
            </button>
          </div>

          {orderStatus && (
            <div style={{ background: 'var(--surface)', padding: 18, borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <strong style={{ fontSize: 15, color: 'var(--heading)' }}>Order #{orderStatus.order_id}</strong>
                <Badge status={orderStatus.status === 'SUCCESS' ? 'ok' : orderStatus.status === 'FAILED' ? 'blocked' : 'caution'} />
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.7 }}>
                <div><strong>Amount:</strong> {fmt(orderStatus.amount)}</div>
                <div><strong>Plan:</strong> {orderStatus.plan}</div>
                <div><strong>Paytm Txn ID:</strong> {orderStatus.txn_id || 'Pending Gateway Completion'}</div>
                <div><strong>Created:</strong> {orderStatus.created_at}</div>
                <div><strong>Verified At:</strong> {orderStatus.verified_at || 'Awaiting Webhook Callback'}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
