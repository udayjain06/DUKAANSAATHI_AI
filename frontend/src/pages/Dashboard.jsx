import React, { useEffect, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Area, AreaChart
} from 'recharts'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, StatCard, Badge, SyntheticBanner, DataLabel } from '../components/UI'

const TEAL = '#0D9488'
const TEAL_LIGHT = 'rgba(13,148,136,0.08)'
const RED = '#B91C1C'
const WEEKDAY_ORDER = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

const chartTooltipStyle = {
  background: '#fff',
  border: '1px solid #E2E8F0',
  borderRadius: 10,
  boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
  fontSize: 13,
  padding: '8px 12px',
}

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
      <div style={{ marginBottom: 22 }}><SyntheticBanner /></div>

      {/* Summary stats */}
      <div className="stats-grid">
        <StatCard label="Total Revenue (8 wks)" value={fmt(sales.total_revenue)} sub={`Avg ${fmt(sales.avg_daily_revenue)}/day`} accent="accent" />
        <StatCard label="Total Transactions" value={(sales.total_txns || 0).toLocaleString()} sub="8-week period" accent="accent" />
        <StatCard label="Best Day" value={sales.best_day || '—'} sub={`Avg ${fmt(sales.weekday_avg?.[sales.best_day])}`} accent="success" />
        <StatCard label="Worst Day" value={sales.worst_day || '—'} sub={`Dip ${pct(weakDay?.dip_pct)}`} accent="error" />
        <StatCard label="Pending Actions" value={dash.pending_recommendations || 0} sub="Recommendations" accent="warning" />
        <StatCard label="Active Offers" value={dash.active_offers || 0} sub="Running now" accent="accent" />
      </div>

      {/* Charts */}
      <div className="charts-row">
        <div className="card">
          <div className="card-header"><h3>8-Week Revenue Trend</h3></div>
          <div className="card-body" style={{ paddingRight: 8 }}>
            <ResponsiveContainer width="100%" height={230}>
              <AreaChart data={weeklyData}>
                <defs>
                  <linearGradient id="tealGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={TEAL} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={TEAL} stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} />
                <Area type="monotone" dataKey="revenue" stroke={TEAL} strokeWidth={2.5} fill="url(#tealGrad)" dot={{ r: 4, fill: TEAL, strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6, fill: TEAL, stroke: '#fff', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>Weekday Avg Revenue</h3></div>
          <div className="card-body" style={{ paddingRight: 8 }}>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={weekdayData} barSize={32}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} />
                <Bar dataKey="avg" radius={[6,6,0,0]}>
                  {weekdayData.map((e, i) => (
                    <Cell key={i} fill={e.isWeak ? RED : TEAL} opacity={e.isWeak ? 0.85 : 1} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p style={{ fontSize: 11, color: '#94A3B8', marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: RED, display: 'inline-block' }} />
              Weak day highlighted
            </p>
          </div>
        </div>
      </div>

      {/* Weak day + Top products */}
      <div className="charts-row">
        {weakDay && (
          <div className="card">
            <div className="card-header">
              <h3>⚠️ Weak Day Opportunity</h3>
              <Badge status={weakDay.confidence} />
            </div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: 16, marginBottom: 18 }}>
                <div>
                  <div className="stat-label">Day</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: RED, marginTop: 4 }}>{weakDay.weekday}</div>
                </div>
                <div>
                  <div className="stat-label">Sales Dip</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: RED, marginTop: 4 }}>{pct(weakDay.dip_pct)}</div>
                </div>
                <div>
                  <div className="stat-label">Confidence</div>
                  <div style={{ fontSize: 16, fontWeight: 650, color: '#334155', marginTop: 6 }}>{weakDay.confidence}</div>
                </div>
                <div>
                  <div className="stat-label">Consistency</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#334155', marginTop: 6 }}>{weakDay.consistency}</div>
                </div>
              </div>
              <div className="alert alert-warning" style={{ marginBottom: 0 }}>
                Based on 8-week consistent pattern (not statistical significance). Running an offer on <strong>{weakDay.weekday}</strong> could reduce this gap.
              </div>
            </div>
          </div>
        )}

        <div className="card">
          <div className="card-header"><h3>🏆 Top Products</h3></div>
          <div className="card-body">
            {topProducts.length === 0 && <p style={{ color: 'var(--muted)' }}>No product data yet.</p>}
            {topProducts.map((p, i) => (
              <div key={p.product_id} className="list-item">
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--heading)' }}>{p.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>{p.total_units} units sold</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, color: TEAL, fontSize: 14 }}>{fmt(p.total_revenue)}</div>
                  {p.margin_pct != null && <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{pct(p.margin_pct)} margin</div>}
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
              <div key={r.id} className="reco-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 700, color: 'var(--heading)' }}>📅 {r.weak_day}</span>
                    <span style={{ color: RED, fontWeight: 600, fontSize: 13 }}>↓{pct(r.dip_pct)} dip</span>
                    <DataLabel label={r.data_label} />
                  </div>
                  <Badge status={r.margin?.status || 'ok'} />
                </div>
                <p style={{ fontSize: 13, marginTop: 10, color: 'var(--body)', lineHeight: 1.55 }}>
                  {r.explanation?.en || 'View details for full recommendation.'}
                </p>
                <a href="/recommendations" style={{ fontSize: 13, color: TEAL, fontWeight: 600, marginTop: 8, display: 'inline-block' }}>
                  View → Recommendations
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
