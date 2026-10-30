import React, { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, Cell
} from 'recharts'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, StatCard, Badge, SyntheticBanner, DataLabel } from '../components/UI'

const TEAL = '#0D9488'
const RED = '#B91C1C'
const WEEKDAY_ORDER = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

const chartTooltipStyle = {
  background: '#ffffff',
  border: '1px solid #E2E8F0',
  borderRadius: 10,
  boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
  fontSize: 13,
  padding: '8px 12px',
}

export default function SalesAnalysis() {
  const [sales, setSales] = useState(null)
  const [weak, setWeak] = useState(null)
  const [products, setProducts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [weeks, setWeeks] = useState(8)

  const load = (w) => {
    setLoading(true)
    Promise.all([
      api.get(`/sales/summary?weeks=${w}`),
      api.get('/insights/weak-day'),
      api.get('/insights/products'),
    ])
      .then(([s, wd, p]) => { setSales(s.data); setWeak(wd.data); setProducts(p.data) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(weeks) }, [weeks])

  if (loading) return <Loading text="Analysing sales trends..." />
  if (error) return <ErrorMsg message={error} />

  const weekdayData = WEEKDAY_ORDER
    .filter(d => sales.weekday_avg?.[d] !== undefined)
    .map(d => {
      const isWeak = weak?.all_weekdays?.find(x => x.weekday === d)?.is_weak
      return { name: d.slice(0,3), full: d, avg: Math.round(sales.weekday_avg[d] || 0), isWeak }
    })

  const weeklyData = (sales.weekly || []).map(w => ({
    name: w.week?.slice(-5) || w.week,
    revenue: Math.round(w.revenue),
    txns: w.txns,
  }))

  const allWeekdays = weak?.all_weekdays || []
  const primaryWeak = weak?.primary_weak_day

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <SyntheticBanner />
      </div>

      <div style={{ marginBottom: 20, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)' }}>Analysis Window:</span>
        <div style={{ display: 'inline-flex', background: 'var(--surface)', padding: 3, borderRadius: 10, gap: 4 }}>
          {[4, 8, 12].map(w => (
            <button
              key={w}
              className={`btn btn-sm ${weeks === w ? 'btn-primary' : 'btn-ghost'}`}
              style={{
                borderRadius: 7,
                boxShadow: weeks === w ? '0 1px 3px rgba(13,148,136,0.25)' : 'none',
                border: 'none',
              }}
              onClick={() => setWeeks(w)}
            >
              {w} Weeks
            </button>
          ))}
        </div>
        <DataLabel label={sales.data_label || 'synthetic'} />
      </div>

      <div className="stats-grid">
        <StatCard label="Total Revenue" value={fmt(sales.total_revenue)} sub={`${weeks}-week window`} accent="accent" />
        <StatCard label="Total Transactions" value={(sales.total_txns || 0).toLocaleString()} sub="Verified sales bills" accent="accent" />
        <StatCard label="Avg Daily Revenue" value={fmt(sales.avg_daily_revenue)} sub="Across all days" accent="accent" />
        <StatCard label="Best Day" value={sales.best_day || '—'} sub={`₹${Math.round(sales.weekday_avg?.[sales.best_day] || 0).toLocaleString()} avg`} accent="success" />
        <StatCard label="Worst Day" value={sales.worst_day || '—'} sub={primaryWeak ? `${pct(primaryWeak.dip_pct)} dip` : 'Identified'} accent="error" />
      </div>

      {/* Weekly trend */}
      <div className="card" style={{ marginBottom: 22 }}>
        <div className="card-header"><h3>📈 Weekly Revenue Trend</h3></div>
        <div className="card-body" style={{ paddingRight: 10 }}>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={weeklyData}>
              <defs>
                <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={TEAL} stopOpacity={0.16} />
                  <stop offset="95%" stopColor={TEAL} stopOpacity={0.01} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
              <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} />
              <Area type="monotone" dataKey="revenue" stroke={TEAL} strokeWidth={2.5} fill="url(#salesGrad)" dot={{ r: 4, fill: TEAL, strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6, fill: TEAL, stroke: '#fff', strokeWidth: 2 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Weekday analysis */}
      <div className="charts-row">
        <div className="card">
          <div className="card-header"><h3>📅 Weekday Average Revenue</h3></div>
          <div className="card-body" style={{ paddingRight: 10 }}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={weekdayData} barSize={30}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                <Tooltip formatter={v => fmt(v)} labelFormatter={l => weekdayData.find(d => d.name === l)?.full || l} contentStyle={chartTooltipStyle} />
                <Bar dataKey="avg" radius={[6,6,0,0]}>
                  {weekdayData.map((e, i) => (
                    <Cell key={i} fill={e.isWeak ? RED : TEAL} opacity={e.isWeak ? 0.85 : 1} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Weak day table */}
        <div className="card">
          <div className="card-header">
            <h3>🔍 Weak Day Detection</h3>
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>Threshold: dip &gt; 10%</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Day</th><th>Avg ₹</th><th>Dip %</th><th>Consistency</th><th>Confidence</th></tr>
                </thead>
                <tbody>
                  {allWeekdays.map(d => (
                    <tr key={d.weekday}>
                      <td style={{ fontWeight: d.is_weak ? 700 : 500, color: d.is_weak ? RED : 'var(--heading)' }}>
                        {d.is_weak ? '⚠️ ' : ''}{d.weekday}
                      </td>
                      <td>{fmt(d.day_avg)}</td>
                      <td style={{ color: d.dip_pct > 10 ? RED : 'var(--success)', fontWeight: 650 }}>
                        {d.dip_pct > 0 ? `-${pct(d.dip_pct)}` : `+${pct(-d.dip_pct)}`}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--muted)' }}>{d.consistency}</td>
                      <td><Badge status={d.confidence} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: 11, color: 'var(--muted)', padding: '10px 18px', borderTop: '1px solid var(--border-subtle)' }}>
              ⓘ Consistent pattern over {weeks} weeks. Baseline calculated as mean of non-dip days.
            </p>
          </div>
        </div>
      </div>

      {/* Product insights */}
      {products && (
        <div className="charts-row">
          <div className="card">
            <div className="card-header"><h3>🏆 Top Performing Products</h3></div>
            <div className="card-body" style={{ padding: 0 }}>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Product</th><th>Revenue</th><th>Units</th><th>Margin</th></tr></thead>
                  <tbody>
                    {products.top.map(p => (
                      <tr key={p.product_id}>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--heading)' }}>{p.name}</div>
                          <span style={{ fontSize: 11, color: 'var(--muted)' }}>{p.category}</span>
                        </td>
                        <td style={{ fontWeight: 700, color: TEAL }}>{fmt(p.total_revenue)}</td>
                        <td>{p.total_units}</td>
                        <td style={{ fontWeight: 600 }}>{p.margin_pct != null ? pct(p.margin_pct) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><h3>📉 Low Performing Products</h3></div>
            <div className="card-body" style={{ padding: 0 }}>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Product</th><th>Revenue</th><th>Units</th><th>Margin</th></tr></thead>
                  <tbody>
                    {products.low.length === 0 && (
                      <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--muted)', padding: '24px' }}>All active products showing healthy volume</td></tr>
                    )}
                    {products.low.map(p => (
                      <tr key={p.product_id}>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--heading)' }}>{p.name}</div>
                          <span style={{ fontSize: 11, color: 'var(--muted)' }}>{p.category}</span>
                        </td>
                        <td style={{ fontWeight: 700, color: RED }}>{fmt(p.total_revenue)}</td>
                        <td>{p.total_units}</td>
                        <td style={{ fontWeight: 600 }}>{p.margin_pct != null ? pct(p.margin_pct) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
