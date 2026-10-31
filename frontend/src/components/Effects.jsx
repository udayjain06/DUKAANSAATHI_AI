import React, { useEffect, useRef, useState } from 'react'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/* ───────────────────────── Loading screen ───────────────────────── */
const STATUS = [
  'Reading your sales…',
  'Spotting weak days…',
  'Checking your margins…',
  'Almost ready…',
]

export function Loader({ onReveal, onDone }) {
  const [progress, setProgress] = useState(0)
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    const total = prefersReducedMotion() ? 700 : 2600
    const start = performance.now()
    let raf
    let t1
    let t2
    let finished = false

    const finish = () => {
      if (finished) return
      finished = true
      setProgress(100)
      setLeaving(true)
      t1 = setTimeout(() => onReveal && onReveal(), 150)
      t2 = setTimeout(() => onDone && onDone(), 950)
    }

    const tick = (now) => {
      if (finished) return
      const t = Math.min((now - start) / total, 1)
      setProgress(Math.round((1 - Math.pow(1 - t, 3)) * 100))
      if (t < 1) {
        raf = requestAnimationFrame(tick)
      } else {
        finish()
      }
    }
    raf = requestAnimationFrame(tick)
    // Fallback: requestAnimationFrame is paused in background tabs, which would
    // otherwise leave the splash screen stuck forever.
    const guard = setTimeout(finish, total + 600)

    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(guard)
      clearTimeout(t1)
      clearTimeout(t2)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const status = STATUS[Math.min(Math.floor(progress / 26), STATUS.length - 1)]

  return (
    <div className={`loader ${leaving ? 'leave' : ''}`} role="status" aria-label="Loading">
      <div className="loader-stage">
        <span className="loader-ring r1" />
        <span className="loader-ring r2" />
        <span className="loader-orbit o1"><i /></span>
        <span className="loader-orbit o2"><i /></span>
        <div className="loader-mark">D</div>
      </div>

      <h1 className="loader-word" aria-label="DukaanSaathi AI">
        {'DukaanSaathi'.split('').map((c, i) => (
          <span key={i} style={{ animationDelay: `${300 + i * 55}ms` }}>{c}</span>
        ))}
        <em style={{ animationDelay: `${300 + 12 * 55}ms` }}> AI</em>
      </h1>
      <p className="loader-tag">Merchant Intelligence Platform</p>

      <div className="loader-bar"><i style={{ width: `${progress}%` }} /></div>
      <div className="loader-meta">
        <span>{status}</span>
        <b>{progress}%</b>
      </div>
    </div>
  )
}

/* ───────────────────────── Cursor follower ───────────────────────── */
export function Cursor() {
  const dot = useRef(null)
  const ring = useRef(null)

  useEffect(() => {
    const fine = window.matchMedia && window.matchMedia('(pointer: fine)').matches
    if (!fine || prefersReducedMotion()) return undefined

    document.body.classList.add('has-cursor')
    let x = -100, y = -100, rx = -100, ry = -100, raf

    const onMove = (e) => {
      x = e.clientX
      y = e.clientY
      if (dot.current) {
        dot.current.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`
        dot.current.classList.add('on')
      }
      ring.current && ring.current.classList.add('on')
    }
    const loop = () => {
      rx += (x - rx) * 0.16
      ry += (y - ry) * 0.16
      if (ring.current) {
        ring.current.style.transform = `translate3d(${rx}px, ${ry}px, 0) translate(-50%, -50%)`
      }
      raf = requestAnimationFrame(loop)
    }
    const onOver = (e) => {
      const el = e.target
      if (!el || !el.closest || !ring.current) return
      ring.current.classList.toggle(
        'hover',
        !!el.closest('a, button, [role="button"], .nav-item, .tile, .quick-prompt-pill, select, label')
      )
      ring.current.classList.toggle('text', !!el.closest('input, textarea'))
    }
    const onDown = () => ring.current && ring.current.classList.add('down')
    const onUp = () => ring.current && ring.current.classList.remove('down')
    const onLeave = () => {
      dot.current && dot.current.classList.remove('on')
      ring.current && ring.current.classList.remove('on')
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseover', onOver)
    window.addEventListener('mousedown', onDown)
    window.addEventListener('mouseup', onUp)
    document.documentElement.addEventListener('mouseleave', onLeave)
    raf = requestAnimationFrame(loop)

    return () => {
      document.body.classList.remove('has-cursor')
      cancelAnimationFrame(raf)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseover', onOver)
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('mouseup', onUp)
      document.documentElement.removeEventListener('mouseleave', onLeave)
    }
  }, [])

  return (
    <>
      <div ref={ring} className="cursor-ring" aria-hidden="true"><i /></div>
      <div ref={dot} className="cursor-dot" aria-hidden="true" />
    </>
  )
}

/* ───────────────────────── Animated background ───────────────────────── */
export function Background() {
  return (
    <div className="bg-anim" aria-hidden="true">
      <span className="blob b1" />
      <span className="blob b2" />
      <span className="blob b3" />
      <span className="bg-grid" />
    </div>
  )
}

/* ───────────────────────── Scroll progress bar ───────────────────────── */
export function ScrollProgress() {
  const bar = useRef(null)
  useEffect(() => {
    const onScroll = () => {
      const h = document.documentElement
      const max = h.scrollHeight - h.clientHeight
      const p = max > 0 ? h.scrollTop / max : 0
      if (bar.current) bar.current.style.transform = `scaleX(${p})`
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])
  return <div className="scroll-progress"><i ref={bar} /></div>
}

/* ───────────────────────── Reveal on scroll ───────────────────────── */
export function Reveal({ as: Tag = 'div', delay = 0, className = '', style, children, ...rest }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    if (!('IntersectionObserver' in window)) {
      el.classList.add('in')
      return undefined
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('in')
          io.disconnect()
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -5% 0px' }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return (
    <Tag ref={ref} className={`reveal ${className}`} style={{ '--d': `${delay}ms`, ...style }} {...rest}>
      {children}
    </Tag>
  )
}

/* ───────────────────────── Count-up number ───────────────────────── */
export function CountUp({ value, format, duration = 1400 }) {
  const [v, setV] = useState(0)
  useEffect(() => {
    const target = Number(value) || 0
    if (prefersReducedMotion()) { setV(target); return undefined }
    const start = performance.now()
    let raf
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1)
      setV(target * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value, duration])
  const n = Math.round(v)
  return <>{format ? format(n) : n.toLocaleString('en-IN')}</>
}
