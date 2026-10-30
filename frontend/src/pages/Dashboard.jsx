import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Area, AreaChart
} from 'recharts'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, Badge, DataLabel, SyntheticBanner } from '../components/UI'
import { Reveal, CountUp } from '../components/Effects'
import { NAV } from '../components/TopNav'

const LIME = '#C8F560'
const RED = '#FF6B6B'
const WEEKDAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const chartTooltipStyle = {
  background: '#17171B',
  border: '1px solid #2C2C34',
  borderRadius: 12,
  boxShadow: '0 12px 32px rgba(0,0,0,0.6)',
  fontSize: 13,
  padding: '8px 12px',
}

const HEADLINE = [
  { t: 'Never' }, { t: 'miss' }, { t: 'a' },
  { t: 'weak', hl: true }, { t: 'day', hl: true },
  { t: 'in' }, { t: 'your' }, { t: 'shop' }, { t: 'again' },
]

function SectionHead({ eyebrow, title, sub }) {
  return (
    <div className="section-head">
      <div className="eyebrow">{eyebrow}</div>
      <h2>{title}</h2>
      {sub && <p>{sub}</p>}
    </div>
  )
}

const RING_R = 34
const RING_C = 2 * Math.PI * RING_R

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [ringOn, setRingOn] = useState(false)

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

  useEffect(() => {
    if (!data) return undefined
    const t = setTimeout(() => setRingOn(true), 500)
    return () => clearTimeout(t)
  }, [data])

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
      isWeak: dash.weak_day?.weekday?.slice(0, 3) === d.slice(0, 3),
    }))
  const topProducts = dash.products?.top || []
  const weakDay = dash.weak_day
  const dip = Math.min(Math.abs(Number(weakDay?.dip_pct) || 0), 100)
  const pendingCount = dash.pending_recommendations || 0

  const axis = { fontSize: 12, fill: '#8B8B97' }

  return (
    <div className="home">
      {/* ───────────── HERO ───────────── */}
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow hero-eyebrow">Merchant intelligence</div>
          <h1 className="hero-title" aria-label="Never miss a weak day in your shop again">
            {HEADLINE.map((w, i) => (
              <span key={i} className="w" style={{ '--i': i }} aria-hidden="true">
                <span className={w.hl ? 'hl' : ''}>{w.t}</span>
              </span>
            ))}
          </h1>
          <p className="hero-sub">
            Spot slow days, price offers safely and grow your margin — all from your last 8 weeks of sales.
          </p>
          <div className="hero-cta">
            <Link to="/recommendations" className="btn btn-primary btn-lg">Get recommendations</Link>
            <div className="hero-note">
              <b>8 weeks</b>
              of sales analysed
            </div>
          </div>
          <div className="hero-chips">
            <span>UPI</span><span>Paytm QR</span><span>WhatsApp Status</span>
          </div>
        </div>

        <div className="hero-visual">
          <div className="hero-card">
            <div className="hc-pill">
              <span className="hc-pill-icon">✦</span>
              <div>
                <b>{pendingCount} pending {pendingCount === 1 ? 'action' : 'actions'}</b>
                <small>Recommendations waiting</small>
              </div>
            </div>

            <div className="hc-top">
              <div className="hc-label">TOTAL REVENUE · 8 WEEKS</div>
              <div className="hc-value"><CountUp value={sales.total_revenue} format={n => fmt(n)} /></div>
              <div className="hc-sub">Avg {fmt(sales.avg_daily_revenue)} / day</div>
            </div>

            <div className="hc-mid">
              <Link to="/sales" className="btn btn-primary btn-sm">Sales analysis</Link>
              <Link to="/products" className="btn btn-dark-outline btn-sm">Products</Link>
            </div>

            <div className="hc-bottom">
              <div className="hc-ring">
                <svg viewBox="0 0 80 80" width="84" height="84">
                  <circle cx="40" cy="40" r={RING_R} className="ring-track" />
                  <circle
                    cx="40" cy="40" r={RING_R}
                    className="ring-fill"
                    strokeDasharray={RING_C}
                    strokeDashoffset={ringOn ? RING_C * (1 - dip / 100) : RING_C}
                    transform="rotate(-90 40 40)"
                  />
                </svg>
                <span>{weakDay ? `${Math.round(dip)}%` : '—'}</span>
              </div>
              <div className="hc-copy">
                <div className="hc-label hc-label-lime">WEAK DAY</div>
                <b>{weakDay ? weakDay.weekday : 'None detected'}</b>
                <small>{weakDay ? 'Sales dip vs. average' : 'Your week looks steady'}</small>
                <Link to="/recommendations" className="hc-btn">Get report</Link>
              </div>
            </div>

            <span className="hc-badge hc-cal">📅</span>
            <span className="hc-badge hc-rupee">₹</span>
          </div>
        </div>
      </section>

      <Reveal className="hero-banner"><SyntheticBanner /></Reveal>

      {/* ───────────── AT A GLANCE ───────────── */}
      <section className="section">
        <Reveal>
          <SectionHead
            eyebrow="At a glance"
            title="Your shop, in simple blocks"
            sub="The numbers that matter, without the noise."
          />
        </Reveal>

        <div className="bento">
          <Reveal className="block b-chart" delay={0}>
            <div className="block-title">8-week revenue trend</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={weeklyData} margin={{ top: 10, right: 8, left: -8, bottom: 0 }}>
                  <defs>
                    <linearGradient id="limeGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={LIME} stopOpacity={0.28} />
                      <stop offset="95%" stopColor={LIME} stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 6" stroke="#22222A" vertical={false} />
                  <XAxis dataKey="name" tick={axis} axisLine={false} tickLine={false} />
                  <YAxis tick={axis} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                  <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} cursor={{ stroke: '#33333C' }} />
                  <Area type="monotone" dataKey="revenue" stroke={LIME} strokeWidth={3} fill="url(#limeGrad)"
                    dot={{ r: 4, fill: LIME, strokeWidth: 3, stroke: '#0F0F12' }}
                    activeDot={{ r: 7, fill: LIME, stroke: '#0F0F12', strokeWidth: 3 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Reveal>

          <Reveal className="block block-light" delay={80}>
            <div className="block-title">Transactions</div>
            <div className="block-num"><CountUp value={sales.total_txns || 0} /></div>
            <div className="block-sub">Across 8 weeks</div>
          </Reveal>

          <Reveal className="block" delay={140}>
            <div className="block-title">Best day</div>
            <div className="block-num green">{sales.best_day || '—'}</div>
            <div className="block-sub">Avg {fmt(sales.weekday_avg?.[sales.best_day])}</div>
          </Reveal>

          <Reveal className="block" delay={200}>
            <div className="block-title">Worst day</div>
            <div className="block-num red">{sales.worst_day || '—'}</div>
            <div className="block-sub">Dip {pct(weakDay?.dip_pct)}</div>
          </Reveal>

          <Reveal className="block block-violet" delay={260}>
            <div className="block-title">Pending actions</div>
            <div className="block-num"><CountUp value={pendingCount} /></div>
            <Link to="/recommendations" className="block-link">Review →</Link>
          </Reveal>
        </div>
      </section>

      {/* ───────────── PATTERNS ───────────── */}
      <section className="section">
        <Reveal>
          <SectionHead
            eyebrow="Weekly pattern"
            title="Which days carry your shop?"
            sub="The weak day is highlighted in red."
          />
        </Reveal>

        <div className="bento">
          <Reveal className="block b-chart">
            <div className="block-title">Weekday average revenue</div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={weekdayData} barSize={34} margin={{ top: 10, right: 8, left: -8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 6" stroke="#22222A" vertical={false} />
                  <XAxis dataKey="name" tick={axis} axisLine={false} tickLine={false} />
                  <YAxis tick={axis} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} />
                  <Tooltip formatter={v => fmt(v)} contentStyle={chartTooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                  <Bar dataKey="avg" radius={[10, 10, 4, 4]}>
                    {weekdayData.map((e, i) => (
                      <Cell key={i} fill={e.isWeak ? RED : LIME} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Reveal>

          <Reveal className="block block-dark b-wide" delay={80}>
            <div className="block-head">
              <div className="block-title">⚠️ Weak day opportunity</div>
              {weakDay && <Badge status={weakDay.confidence} />}
            </div>
            {weakDay ? (
              <>
                <div className="mini-stats">
                  <div><span>Day</span><b className="red">{weakDay.weekday}</b></div>
                  <div><span>Sales dip</span><b className="red">{pct(weakDay.dip_pct)}</b></div>
                  <div><span>Consistency</span><b>{weakDay.consistency}</b></div>
                </div>
                <p className="block-text">
                  Based on an 8-week consistent pattern (not statistical significance). An offer on{' '}
                  <strong>{weakDay.weekday}</strong> could reduce this gap.
                </p>
              </>
            ) : (
              <p className="block-text">No weak day detected yet.</p>
            )}
          </Reveal>

          <Reveal className="block block-lime" delay={140}>
            <div className="block-title">Active offers</div>
            <div className="block-num"><CountUp value={dash.active_offers || 0} /></div>
            <div className="block-sub">Running now</div>
          </Reveal>

          <Reveal className="block block-light" delay={200}>
            <div className="block-title">Check a discount</div>
            <div className="block-sub" style={{ marginTop: 10 }}>See if an offer keeps your margin safe.</div>
            <Link to="/margin" className="block-link">Open calculator →</Link>
          </Reveal>
        </div>
      </section>

      {/* ───────────── PRODUCTS & ACTIONS ───────────── */}
      <section className="section">
        <Reveal>
          <SectionHead
            eyebrow="Products & actions"
            title="What sells, and what to do next"
          />
        </Reveal>

        <div className="split">
          <Reveal className="block">
            <div className="block-title">🏆 Top products</div>
            {topProducts.length === 0 && <p className="block-text">No product data yet.</p>}
            {topProducts.map(p => (
              <div key={p.product_id} className="list-item">
                <div>
                  <div className="li-name">{p.name}</div>
                  <div className="li-sub">{p.total_units} units sold</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="li-amount">{fmt(p.total_revenue)}</div>
                  {p.margin_pct != null && <div className="li-sub">{pct(p.margin_pct)} margin</div>}
                </div>
              </div>
            ))}
          </Reveal>

          <Reveal className="block" delay={100}>
            <div className="block-head">
              <div className="block-title">💡 Pending recommendations</div>
              <Link to="/recommendations" className="block-link inline">See all →</Link>
            </div>
            {(!pending || pending.length === 0) && <p className="block-text">Nothing pending — you're all caught up.</p>}
            {(pending || []).slice(0, 3).map(r => (
              <div key={r.id} className="reco-mini">
                <div className="reco-mini-top">
                  <span className="reco-day">📅 {r.weak_day}</span>
                  <span className="reco-dip">↓{pct(r.dip_pct)} dip</span>
                  <DataLabel label={r.data_label} />
                  <span style={{ marginLeft: 'auto' }}><Badge status={r.margin?.status || 'ok'} /></span>
                </div>
                <p>{r.explanation?.en || 'View details for the full recommendation.'}</p>
              </div>
            ))}
          </Reveal>
        </div>
      </section>

      {/* ───────────── ALL FEATURES ───────────── */}
      <section className="section">
        <Reveal>
          <SectionHead
            eyebrow="Everything in one place"
            title="All your tools, one scroll away"
            sub="Pick any tool below — or use the menu at the top."
          />
        </Reveal>

        <div className="tiles">
          {NAV.filter(n => n.path !== '/').map((n, i) => (
            <Reveal key={n.path} delay={(i % 3) * 90}>
              <Link to={n.path} className="tile">
                <span className="tile-icon">{n.icon}</span>
                <span className="tile-title">{n.label}</span>
                <span className="tile-desc">{n.desc}</span>
                <span className="tile-arrow">↗</span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>
    </div>
  )
}
