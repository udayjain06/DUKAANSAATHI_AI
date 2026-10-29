import React, { useState } from 'react'
import api, { fmt } from '../api'
import { ErrorMsg } from '../components/UI'

export default function Bills() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)
  const [error, setError] = useState(null)
  const [extractedItems, setExtractedItems] = useState([])
  const [billRef, setBillRef] = useState(`BILL-${Date.now().toString().slice(-4)}`)

  // Manual row addition if AI is unavailable or for missing items
  const handleAddItem = () => {
    setExtractedItems([
      ...extractedItems,
      { product_name: '', cost_price: '', quantity: 1, unit: 'pcs' }
    ])
  }

  const handleUpdateItem = (idx, field, val) => {
    const copy = [...extractedItems]
    copy[idx][field] = val
    setExtractedItems(copy)
  }

  const handleRemoveItem = (idx) => {
    setExtractedItems(extractedItems.filter((_, i) => i !== idx))
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    setError(null)
    setStatusMsg(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await api.post('/bills/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (res.data.extracted_items && res.data.extracted_items.length > 0) {
        setExtractedItems(res.data.extracted_items.map(it => ({
          product_name: it.name || it.product_name,
          cost_price: it.cost_price,
          quantity: it.quantity || 1,
          unit: it.unit || 'pcs'
        })))
        setStatusMsg(`Successfully extracted ${res.data.extracted_items.length} items via AI OCR. Please review and confirm.`)
      } else {
        setStatusMsg("AI OCR completed (no items detected or template mode active). You can manually enter wholesale bill items below.")
        // Add a sample template row so the user can easily start
        if (extractedItems.length === 0) {
          setExtractedItems([
            { product_name: 'Tata Tea Gold 250g', cost_price: 115, quantity: 10, unit: 'pack' },
            { product_name: 'Fortune Sunflower Oil 1L', cost_price: 130, quantity: 15, unit: 'bottle' }
          ])
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleConfirm = async () => {
    if (extractedItems.length === 0) {
      alert("No items to confirm.")
      return
    }
    for (let it of extractedItems) {
      if (!it.product_name || !it.cost_price) {
        alert("Please ensure all items have a product name and valid cost price.")
        return
      }
    }

    try {
      const payload = {
        items: extractedItems.map(it => ({
          product_name: it.product_name,
          cost_price: parseFloat(it.cost_price),
          quantity: parseFloat(it.quantity || 1),
          unit: it.unit || 'unit',
          bill_ref: billRef
        }))
      }
      const res = await api.post('/bills/confirm', payload)
      alert(`Success! Confirmed ${res.data.count} items. Product costs and catalogue updated.`)
      setExtractedItems([])
      setFile(null)
      setStatusMsg("Items saved to catalogue with cost source: 'bill'.")
    } catch (err) {
      alert(err.response?.data?.detail || err.message)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, color: 'var(--heading)' }}>Wholesale Bill & Cost Capture</h2>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>
          Upload supplier invoice / distributor bill photos. The AI extracts items, wholesale costs, and updates your inventory automatically.
        </p>
      </div>

      {error && <ErrorMsg message={error} />}
      {statusMsg && <div className="alert alert-info">{statusMsg}</div>}

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header"><h3>📸 Upload Bill Photo / Invoice</h3></div>
        <div className="card-body">
          <form onSubmit={handleUpload} style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="file"
              accept="image/*,.pdf"
              className="form-input"
              style={{ maxWidth: 360 }}
              onChange={e => setFile(e.target.files[0])}
            />
            <button
              type="submit"
              disabled={!file || uploading}
              className="btn btn-primary"
            >
              {uploading ? 'Extracting via AI...' : 'Scan & Extract Items'}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={handleAddItem}
            >
              + Add Row Manually
            </button>
          </form>
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--muted)' }}>
            Supports JPG, PNG invoices. If AI API key is not configured, reliable template fallback allows instant manual correction.
          </div>
        </div>
      </div>

      {/* Extracted items table for review & confirmation */}
      <div className="card">
        <div className="card-header">
          <h3>Review & Confirm Extracted Items</h3>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: 'var(--muted)' }}>Bill Ref:</span>
            <input
              className="form-input"
              style={{ width: 140, padding: '4px 8px', fontSize: 13 }}
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
                  <th style={{ width: '40%' }}>Product Name</th>
                  <th>Wholesale Cost (₹)</th>
                  <th>Quantity</th>
                  <th>Unit</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {extractedItems.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
                      No items to review. Upload a bill or click "+ Add Row Manually" above.
                    </td>
                  </tr>
                ) : (
                  extractedItems.map((item, idx) => (
                    <tr key={idx}>
                      <td>
                        <input
                          className="form-input"
                          style={{ padding: '6px 10px' }}
                          value={item.product_name}
                          onChange={e => handleUpdateItem(idx, 'product_name', e.target.value)}
                          placeholder="e.g. Parle-G 100g"
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          className="form-input"
                          style={{ padding: '6px 10px', width: 120 }}
                          value={item.cost_price}
                          onChange={e => handleUpdateItem(idx, 'cost_price', e.target.value)}
                          placeholder="Cost ₹"
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          className="form-input"
                          style={{ padding: '6px 10px', width: 80 }}
                          value={item.quantity}
                          onChange={e => handleUpdateItem(idx, 'quantity', e.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          className="form-input"
                          style={{ padding: '6px 10px', width: 90 }}
                          value={item.unit}
                          onChange={e => handleUpdateItem(idx, 'unit', e.target.value)}
                        />
                      </td>
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleRemoveItem(idx)}
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
            <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'flex-end', gap: 12, borderTop: '1px solid var(--border)' }}>
              <button className="btn btn-ghost" onClick={handleAddItem}>+ Add Another Row</button>
              <button className="btn btn-success" onClick={handleConfirm}>
                ✓ Confirm & Save {extractedItems.length} Items to Inventory
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

