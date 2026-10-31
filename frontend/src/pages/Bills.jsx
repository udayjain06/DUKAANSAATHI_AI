import React, { useState, useRef, useEffect, useCallback } from 'react'
import api, { fmt } from '../api'
import { ErrorMsg, Loading } from '../components/UI'

const ACCEPTED = '.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff,.pdf'

const emptyItem = () => ({ product_name: '', cost_price: '', quantity: 1, unit: 'pcs', amount: '' })

const engineLabel = (engine) => {
  switch (engine) {
    case 'rapidocr': return 'RapidOCR (local, offline)'
    case 'pdf-text': return 'PDF text layer'
    case 'pdf-text+rapidocr': return 'PDF text + OCR'
    case 'none': return 'No text detected'
    default: return engine || '—'
  }
}

export default function Bills() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)
  const [error, setError] = useState(null)
  const [extractedItems, setExtractedItems] = useState([])
  const [billRef, setBillRef] = useState(`BILL-${Date.now().toString().slice(-4)}`)
  const [billId, setBillId] = useState(null)
  const [ocrMeta, setOcrMeta] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [showRawText, setShowRawText] = useState(false)
  const [createExpense, setCreateExpense] = useState(true)
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef(null)

  // Bill history
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState(null)
  const [viewingBill, setViewingBill] = useState(null)
  const [viewingLoading, setViewingLoading] = useState(false)

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true)
    setHistoryError(null)
    try {
      const res = await api.get('/bills/history')
      setHistory(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setHistoryError(err.response?.data?.detail || err.message)
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const handleAddItem = () => {
    setExtractedItems(prev => [...prev, emptyItem()])
  }

  const handleUpdateItem = (idx, field, val) => {
    setExtractedItems(prev => {
      const copy = prev.map(it => ({ ...it }))
      copy[idx][field] = val
      // Keep amount loosely in sync when cost/quantity change
      if ((field === 'cost_price' || field === 'quantity') && !copy[idx].amount) {
        const cost = parseFloat(field === 'cost_price' ? val : copy[idx].cost_price)
        const qty = parseFloat(field === 'quantity' ? val : copy[idx].quantity)
        if (!Number.isNaN(cost) && !Number.isNaN(qty)) {
          copy[idx].amount = Math.round(cost * qty * 100) / 100
        }
      }
      return copy
    })
  }

  const handleRemoveItem = (idx) => {
    setExtractedItems(prev => prev.filter((_, i) => i !== idx))
  }

  const handleUpload = async (fileToUpload) => {
    const targetFile = fileToUpload || file
    if (!targetFile) return
    setUploading(true)
    setError(null)
    setStatusMsg(null)
    setWarnings([])
    setOcrMeta(null)
    setBillId(null)

    const formData = new FormData()
    formData.append('file', targetFile)

    try {
      const res = await api.post('/bills/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })
      const data = res.data || {}
      setBillId(data.bill_id || null)
      if (data.bill_ref) setBillRef(data.bill_ref)
      setOcrMeta({
        engine: data.engine,
        confidence: data.confidence,
        pages: data.pages,
        total_amount: data.total_amount,
        raw_text: data.raw_text || '',
      })
      setWarnings(Array.isArray(data.warnings) ? data.warnings : [])

      if (Array.isArray(data.extracted_items) && data.extracted_items.length > 0) {
        setExtractedItems(data.extracted_items.map(it => ({
          product_name: it.product_name || it.name || '',
          cost_price: it.cost_price ?? '',
          quantity: it.quantity || 1,
          unit: it.unit || 'pcs',
          amount: it.amount ?? '',
        })))
      } else {
        setExtractedItems([])
      }

      setStatusMsg(data.message || 'OCR finished. Review the items below before confirming.')
      loadHistory()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleConfirm = async () => {
    if (extractedItems.length === 0) {
      setError('No items to confirm. Upload a bill or add rows manually.')
      return
    }
    for (const it of extractedItems) {
      if (!String(it.product_name || '').trim() || !(parseFloat(it.cost_price) > 0)) {
        setError('Every item needs a product name and a cost price greater than 0.')
        return
      }
    }

    setConfirming(true)
    setError(null)
    try {
      const payload = {
        items: extractedItems.map(it => ({
          product_name: String(it.product_name).trim(),
          cost_price: parseFloat(it.cost_price),
          quantity: parseFloat(it.quantity) > 0 ? parseFloat(it.quantity) : 1,
          unit: it.unit || 'unit',
          bill_ref: billRef || undefined,
          amount: it.amount !== '' && it.amount != null ? parseFloat(it.amount) : undefined,
        })),
        bill_id: billId || undefined,
        bill_ref: billRef || undefined,
        create_expense: createExpense,
      }
      const res = await api.post('/bills/confirm', payload)
      const d = res.data || {}
      setStatusMsg(
        `Saved ${d.count || extractedItems.length} item(s) to the product catalogue` +
        (d.expense_created ? ` and recorded an expense of ${fmt(d.expense_created.amount)}.` : '.')
      )
      setExtractedItems([])
      setFile(null)
      setBillId(null)
      setOcrMeta(null)
      setWarnings([])
      setShowRawText(false)
      setBillRef(`BILL-${Date.now().toString().slice(-4)}`)
      if (fileInputRef.current) fileInputRef.current.value = ''
      loadHistory()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setConfirming(false)
    }
  }

  const viewBill = async (id) => {
    setViewingLoading(true)
    setViewingBill({ id })
    try {
      const res = await api.get(`/bills/history/${id}`)
      setViewingBill(res.data)
    } catch (err) {
      setViewingBill({ id, error: err.response?.data?.detail || err.message })
    } finally {
      setViewingLoading(false)
    }
  }

  const onDragOver = (e) => {
    e.preventDefault()
    setIsDragOver(true)
  }
  const onDragLeave = () => setIsDragOver(false)
  const onDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      setFile(droppedFile)
      handleUpload(droppedFile)
    }
  }

  const confidencePct = ocrMeta?.confidence != null
    ? Math.round(Number(ocrMeta.confidence) * 100)
    : null
  const totalAmount = extractedItems.reduce((sum, it) => {
    const amt = parseFloat(it.amount)
    if (!Number.isNaN(amt) && amt > 0) return sum + amt
    const cost = parseFloat(it.cost_price)
    const qty = parseFloat(it.quantity)
    return sum + (!Number.isNaN(cost) ? cost * (Number.isNaN(qty) ? 1 : qty) : 0)
  }, 0)

  return (
    <div>
      <div style={{ marginBottom: 22 }}>
        <h2 style={{ fontSize: 20, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em' }}>
          Wholesale Bill & Cost Capture
        </h2>
        <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
          Upload a supplier invoice photo or PDF. Local OCR reads the items, quantities and
          wholesale rates, then updates your product costs once you confirm.
        </p>
      </div>

      {error && <ErrorMsg message={error} />}
      {statusMsg && <div className="alert alert-info">{statusMsg}</div>}

      {/* Upload drop zone */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h3>📸 Upload Invoice / Bill</h3>
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>Runs offline — no data leaves your machine</span>
        </div>
        <div className="card-body">
          <div
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${isDragOver ? 'var(--teal)' : 'var(--border)'}`,
              borderRadius: 'var(--radius)',
              padding: '32px 20px',
              textAlign: 'center',
              background: isDragOver ? 'var(--teal-light)' : 'var(--surface)',
              cursor: 'pointer',
              transition: 'all var(--duration) var(--ease-smooth)',
              marginBottom: 16,
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept={ACCEPTED}
              style={{ display: 'none' }}
              onChange={e => {
                if (e.target.files && e.target.files[0]) {
                  setFile(e.target.files[0])
                }
              }}
            />
            <div style={{ fontSize: 32, marginBottom: 8 }}>📄</div>
            <div style={{ fontWeight: 650, color: 'var(--heading)', fontSize: 14 }}>
              {file ? file.name : 'Drop a supplier bill here or click to browse'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
              JPG, PNG, WEBP, BMP, TIFF or PDF · up to 15 MB
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              disabled={!file || uploading}
              className="btn btn-primary"
              onClick={() => handleUpload()}
            >
              {uploading ? 'Reading bill…' : '🔍 Scan & Extract Items'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={handleAddItem}>
              + Add Row Manually
            </button>
            {file && !uploading && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ color: 'var(--muted)' }}
                onClick={() => {
                  setFile(null)
                  if (fileInputRef.current) fileInputRef.current.value = ''
                }}
              >
                Clear file
              </button>
            )}
          </div>

          {uploading && (
            <div style={{ marginTop: 14, fontSize: 13, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
              Running OCR — this can take a few seconds for photos and multi-page PDFs.
            </div>
          )}

          {ocrMeta && (
            <div style={{
              marginTop: 16,
              padding: '12px 16px',
              background: 'var(--surface-2)',
              borderRadius: 10,
              border: '1px solid var(--border)',
              display: 'flex',
              gap: 22,
              flexWrap: 'wrap',
              fontSize: 12.5,
            }}>
              <div><span style={{ color: 'var(--muted)' }}>Engine: </span><strong>{engineLabel(ocrMeta.engine)}</strong></div>
              <div><span style={{ color: 'var(--muted)' }}>Confidence: </span><strong>{confidencePct != null ? `${confidencePct}%` : '—'}</strong></div>
              <div><span style={{ color: 'var(--muted)' }}>Pages: </span><strong>{ocrMeta.pages ?? '—'}</strong></div>
              <div><span style={{ color: 'var(--muted)' }}>Detected total: </span><strong>{fmt(ocrMeta.total_amount)}</strong></div>
            </div>
          )}

          {warnings.length > 0 && (
            <div className="alert alert-warning" style={{ marginTop: 14 }}>
              <strong>OCR notes:</strong>
              <ul style={{ margin: '6px 0 0 18px', padding: 0 }}>
                {warnings.map((w, i) => <li key={i} style={{ fontSize: 12.5 }}>{w}</li>)}
              </ul>
            </div>
          )}

          {ocrMeta?.raw_text && (
            <div style={{ marginTop: 12 }}>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowRawText(v => !v)}
              >
                {showRawText ? '▾ Hide raw OCR text' : '▸ Show raw OCR text'}
              </button>
              {showRawText && (
                <pre style={{
                  marginTop: 10,
                  maxHeight: 240,
                  overflow: 'auto',
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 10,
                  padding: 14,
                  fontSize: 12,
                  lineHeight: 1.55,
                  whiteSpace: 'pre-wrap',
                  color: 'var(--text)',
                }}>
                  {ocrMeta.raw_text}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Review table */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header" style={{ flexWrap: 'wrap', gap: 10 }}>
          <h3>Review & Confirm Extracted Items</h3>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>Bill Ref:</span>
            <input
              className="form-input"
              style={{ width: 150, padding: '5px 10px', fontSize: 12.5 }}
              value={billRef}
              onChange={e => setBillRef(e.target.value)}
            />
          </div>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: '36%' }}>Product Name</th>
                  <th>Wholesale Cost (₹)</th>
                  <th>Quantity</th>
                  <th>Unit</th>
                  <th>Line Amount (₹)</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {extractedItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
                      No items to review. Upload a bill above, or click “+ Add Row Manually”.
                    </td>
                  </tr>
                ) : (
                  extractedItems.map((item, idx) => (
                    <tr key={idx}>
                      <td>
                        <input
                          className="form-input"
                          style={{ padding: '7px 12px', fontSize: 13 }}
                          value={item.product_name}
                          onChange={e => handleUpdateItem(idx, 'product_name', e.target.value)}
                          placeholder="e.g. Parle-G 100g"
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          className="form-input"
                          style={{ padding: '7px 12px', width: 120, fontSize: 13 }}
                          value={item.cost_price}
                          onChange={e => handleUpdateItem(idx, 'cost_price', e.target.value)}
                          placeholder="Cost ₹"
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="any"
                          min="0"
                          className="form-input"
                          style={{ padding: '7px 12px', width: 86, fontSize: 13 }}
                          value={item.quantity}
                          onChange={e => handleUpdateItem(idx, 'quantity', e.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          className="form-input"
                          style={{ padding: '7px 12px', width: 86, fontSize: 13 }}
                          value={item.unit}
                          onChange={e => handleUpdateItem(idx, 'unit', e.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          className="form-input"
                          style={{ padding: '7px 12px', width: 110, fontSize: 13 }}
                          value={item.amount}
                          onChange={e => handleUpdateItem(idx, 'amount', e.target.value)}
                          placeholder="auto"
                        />
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-ghost btn-sm"
                          style={{ color: 'var(--error)' }}
                          onClick={() => handleRemoveItem(idx)}
                          aria-label="Remove item"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {extractedItems.length > 0 && (
            <div style={{
              padding: '16px 22px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 12,
              flexWrap: 'wrap',
              borderTop: '1px solid var(--border)',
              background: 'var(--surface)',
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button className="btn btn-ghost btn-sm" onClick={handleAddItem} style={{ alignSelf: 'flex-start' }}>
                  + Add Another Row
                </button>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--muted)', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={createExpense}
                    onChange={e => setCreateExpense(e.target.checked)}
                  />
                  Also record this bill as a shop expense ({fmt(totalAmount)})
                </label>
              </div>
              <button className="btn btn-success" onClick={handleConfirm} disabled={confirming}>
                {confirming
                  ? 'Saving…'
                  : `✓ Confirm & Save ${extractedItems.length} Item(s) — ${fmt(totalAmount)}`}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Bill history */}
      <div className="card">
        <div className="card-header">
          <h3>🗂️ Uploaded Bill History</h3>
          <button className="btn btn-ghost btn-sm" onClick={loadHistory} disabled={historyLoading}>
            {historyLoading ? 'Refreshing…' : '↻ Refresh'}
          </button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {historyError && (
            <div style={{ padding: 16 }}>
              <ErrorMsg message={historyError} />
            </div>
          )}
          {historyLoading && history.length === 0 ? (
            <Loading text="Loading bill history…" />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Bill Ref</th>
                    <th>File</th>
                    <th>Status</th>
                    <th>Items</th>
                    <th>Total</th>
                    <th>Confidence</th>
                    <th>Uploaded</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {history.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
                        No bills uploaded yet.
                      </td>
                    </tr>
                  ) : (
                    history.map(b => (
                      <tr key={b.id}>
                        <td style={{ fontWeight: 650, color: 'var(--heading)' }}>{b.bill_ref}</td>
                        <td style={{ color: 'var(--muted)', fontSize: 12.5 }}>{b.file_name || '—'}</td>
                        <td>
                          <span className={`badge ${b.status === 'confirmed' ? 'badge-ok' : b.status === 'failed' ? 'badge-blocked' : 'badge-pending'}`}>
                            {b.status}
                          </span>
                        </td>
                        <td>{b.item_count ?? 0}</td>
                        <td>{fmt(b.total_amount)}</td>
                        <td>{b.confidence != null ? `${Math.round(Number(b.confidence) * 100)}%` : '—'}</td>
                        <td style={{ color: 'var(--muted)', fontSize: 12, whiteSpace: 'nowrap' }}>
                          {String(b.created_at || '').slice(0, 16)}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button className="btn btn-ghost btn-sm" onClick={() => viewBill(b.id)}>
                            View
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Bill detail drawer */}
      {viewingBill && (
        <div
          onClick={e => e.target === e.currentTarget && setViewingBill(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 20, 40, 0.55)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20,
            zIndex: 1000,
          }}
        >
          <div
            className="card"
            style={{ width: '100%', maxWidth: 760, maxHeight: '86vh', overflow: 'auto', margin: 0 }}
          >
            <div className="card-header">
              <h3>{viewingBill.bill_ref || 'Bill detail'}</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setViewingBill(null)}>✕</button>
            </div>
            <div className="card-body">
              {viewingLoading ? (
                <Loading text="Loading bill…" />
              ) : viewingBill.error ? (
                <ErrorMsg message={viewingBill.error} />
              ) : (
                <>
                  <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 12.5, marginBottom: 16 }}>
                    <div><span style={{ color: 'var(--muted)' }}>File: </span><strong>{viewingBill.file_name || '—'}</strong></div>
                    <div><span style={{ color: 'var(--muted)' }}>Engine: </span><strong>{engineLabel(viewingBill.engine)}</strong></div>
                    <div><span style={{ color: 'var(--muted)' }}>Status: </span><strong>{viewingBill.status}</strong></div>
                    <div><span style={{ color: 'var(--muted)' }}>Total: </span><strong>{fmt(viewingBill.total_amount)}</strong></div>
                  </div>

                  <h4 style={{ fontSize: 13, marginBottom: 8 }}>Items</h4>
                  {(viewingBill.items || []).length === 0 ? (
                    <p style={{ fontSize: 13, color: 'var(--muted)' }}>No saved items for this bill.</p>
                  ) : (
                    <div className="table-wrap" style={{ marginBottom: 16 }}>
                      <table>
                        <thead>
                          <tr>
                            <th>Product</th>
                            <th>Cost</th>
                            <th>Qty</th>
                            <th>Unit</th>
                          </tr>
                        </thead>
                        <tbody>
                          {viewingBill.items.map(it => (
                            <tr key={it.id}>
                              <td>{it.product_name}</td>
                              <td>{fmt(it.cost_price)}</td>
                              <td>{it.quantity}</td>
                              <td>{it.unit}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <h4 style={{ fontSize: 13, marginBottom: 8 }}>Raw OCR text</h4>
                  <pre style={{
                    maxHeight: 280,
                    overflow: 'auto',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 10,
                    padding: 14,
                    fontSize: 11.5,
                    lineHeight: 1.55,
                    whiteSpace: 'pre-wrap',
                    color: 'var(--text)',
                  }}>
                    {viewingBill.raw_text || 'No raw text stored for this bill.'}
                  </pre>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
