import React from 'react'

export function Spinner() {
  return <div className="spinner" />
}

export function Loading({ text = 'Loading...' }) {
  return (
    <div className="loading-container">
      <Spinner />
      <span>{text}</span>
    </div>
  )
}

export function ErrorMsg({ message }) {
  if (!message) return null
  return <div className="alert alert-error">{message}</div>
}

export function Badge({ status }) {
  const map = {
    ok: 'badge-ok', caution: 'badge-caution', blocked: 'badge-blocked',
    pending: 'badge-pending', approved: 'badge-approved', rejected: 'badge-rejected',
    modified: 'badge-modified', synthetic: 'badge-synthetic',
  }
  return <span className={`badge ${map[status] || 'badge-pending'}`}>{status}</span>
}

export function DataLabel({ label }) {
  return <span className="data-label">📊 {label}</span>
}

export function SyntheticBanner() {
  return (
    <div className="alert alert-info" style={{ marginBottom: 0, marginTop: 0 }}>
      <strong>📊 Synthetic / Demo Data</strong> — All figures are generated with a fixed random seed for demonstration purposes. Not real business data.
    </div>
  )
}

export function Modal({ title, children, onClose, footer }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  )
}

export function StatCard({ label, value, sub, accent }) {
  const cls = accent ? `stat-card ${accent}` : 'stat-card'
  return (
    <div className={cls}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

