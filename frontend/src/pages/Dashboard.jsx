import React, { useEffect, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, StatCard, Badge, SyntheticBanner, DataLabel } from '../components/UI'

const TEAL = '#0D9488'
const ORANGE = '#B45309'
const RED = '#B91C1C'
const GREEN = '#15803D'

const WEEKDAY_ORDER = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      api.get('/sales/summary?weeks=8'),
      api.get('/insights/dashboard'),
      api.get('/recommendation/pending'),
    ])
      .then(([s, d, r]) => setData({ sales: s.data, dash: d.data, pending: r.data }))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Loading dashboard..." />
  if (error) return <ErrorMsg message={error} />
  if (!data) return null

  const { sales, dash, pending } = data
  const weeklyData = (sales.weekly || []).map(w => ({
    name: w.week?.slice(-5) || w.week,
    revenue: Math.round(w.revenue),
    txns: w.txns,
  }))

  const weekdayData = WEEKDAY_ORDER
    .filter(d => sales.weekday_avg?.[d] !== undefined)
    .map(d => ({
      name: d.slice(0, 3),
      avg: Math.round(sales.weekday_avg[d] || 0),
      isWeak: dash.weak_day?.weekday?.slice(0,3) === d.slice(0,3),
    }))

  const topProducts = dash.products?.top || []
  const weakDay = dash.weak_day

  return (
    <div>
      <div style={{ marginBottom: 20 }}><SyntheticBanner /></div>

      {/* Summary stats */}
      <div className="stats-grid">
        <StatCard label="Total Revenue (8 wks)" value={fmt(sales.total_revenue)} sub={`Avg ${fmt(sales.avg_daily_revenue)}/day`} accent="accent" />
        <StatCard label="Total Transactions" value={(sales.total_txns || 0).toLocaleString()} sub="8-week period" accent="accent" />
        <StatCard label="Best Day" value={sales.best_day || '—'} sub={`Avg ${fmt(sales.weekday_avg?.[sales.best_day])}`} accent="success" />
        <StatCard label="Worst Day" value={sales.worst_day || '—'} sub={`Dip ${pct(weakDay?.dip_pct)}`} accent="error" />
        <StatCard label="Pending Recommendations" value={dash.pending_recommendations || 0} sub="Action required" accent="warning" />
        <StatCard label="Active Offers" value={dash.active_offers || 0} sub="Running now" accent="accent" />
      </div>

      {/* Charts row */}
      <div className="charts-row">
        <div className="card">
          <div className="card-header"><h3>📈 8-Week Revenue Trend</h3></div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                <Tooltip formatter={v => fmt(v)} />
                <Line type="monotone" dataKey="revenue" stroke={TEAL} strokeWidth={2.5} dot={{ r: 4, fill: TEAL }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>📅 Weekday Average Revenue</h3></div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weekdayData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                <Tooltip formatter={v => fmt(v)} />
                <Bar dataKey="avg" radius={[4,4,0,0]}>
                  {weekdayData.map((e, i) => (
                    <Cell key={i} fill={e.isWeak ? RED : TEAL} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p style={{ fontSize: 12, color: '#B91C1C', marginTop: 8 }}>🔴 Weak day highlighted</p>
          </div>
        </div>
      </div>

      {/* Weak day alert + top products */}
      <div className="charts-row">
        {weakDay && (
          <div className="card">
            <div className="card-header">
              <h3>⚠️ Weak Day Opportunity</h3>
              <Badge status={weakDay.confidence} />
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 16 }}>
                <div>
                  <div className="stat-label">Day</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: RED }}>{weakDay.weekday}</div>
                </div>
                <div>
                  <div className="stat-label">Sales Dip</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: RED }}>{pct(weakDay.dip_pct)}</div>
                </div>
                <div>
                  <div className="stat-label">Confidence</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: '#334155' }}>{weakDay.confidence}</div>
                </div>
                <div>
                  <div className="stat-label">Consistency</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#334155', marginTop: 6 }}>{weakDay.consistency}</div>
                </div>
              </div>
              <div className="alert alert-warning">
                Based on 8-week consistent pattern (not statistical significance). Running an offer on {weakDay.weekday} could reduce this gap.
              </div>
            </div>
          </div>
        )}

        <div className="card">
          <div className="card-header"><h3>🏆 Top Products</h3></div>
          <div className="card-body">
            {topProducts.length === 0 && <p style={{ color: 'var(--muted)' }}>No product data yet.</p>}
            {topProducts.map((p, i) => (
              <div key={p.product_id} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 0', borderBottom: i < topProducts.length - 1 ? '1px solid #E2E8F0' : 'none'
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>{p.total_units} units sold</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, color: TEAL }}>{fmt(p.total_revenue)}</div>
                  {p.margin_pct != null && <div style={{ fontSize: 12, color: 'var(--muted)' }}>{pct(p.margin_pct)} margin</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Pending recommendations */}
      {pending?.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header"><h3>💡 Pending Recommendations</h3></div>
          <div className="card-body">
            {pending.map(r => (
              <div key={r.id} style={{
                background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8,
                padding: '14px 16px', marginBottom: 10
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                  <div>
                    <span style={{ fontWeight: 700 }}>📅 {r.weak_day}</span>
                    <span style={{ color: RED, marginLeft: 8, fontWeight: 600 }}>↓{pct(r.dip_pct)} dip</span>
                    <span style={{ marginLeft: 10 }}><DataLabel label={r.data_label} /></span>
                  </div>
                  <Badge status={r.margin?.status || 'ok'} />
                </div>
                <p style={{ fontSize: 13, marginTop: 6, color: '#334155' }}>
                  {r.explanation?.en || 'View details for full recommendation.'}
                </p>
                <a href="/recommendations" style={{ fontSize: 13, color: TEAL, fontWeight: 600 }}>View → Recommendations</a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

