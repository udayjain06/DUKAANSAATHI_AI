import React, { useEffect, useState } from 'react'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, Modal } from '../components/UI'

export default function Products() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ name: '', category: 'grocery', sell_price: '', cost_price: '', cost_source: 'manual' })

  const load = () => {
    setLoading(true)
    api.get('/products')
      .then(r => setProducts(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleOpenAdd = () => {
    setEditing(null)
    setForm({ name: '', category: 'grocery', sell_price: '', cost_price: '', cost_source: 'manual' })
    setModalOpen(true)
  }

  const handleOpenEdit = (p) => {
    setEditing(p.id)
    setForm({
      name: p.name,
      category: p.category,
      sell_price: p.sell_price,
      cost_price: p.cost_price || '',
      cost_source: p.cost_source || 'manual',
    })
    setModalOpen(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const payload = {
        name: form.name,
        category: form.category,
        sell_price: parseFloat(form.sell_price),
        cost_price: form.cost_price ? parseFloat(form.cost_price) : null,
        cost_source: form.cost_source,
      }
      if (editing) {
        await api.put(`/products/${editing}`, payload)
      } else {
        await api.post('/products', payload)
      }
      setModalOpen(false)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || err.message)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Deactivate this product?')) return
    try {
      await api.delete(`/products/${id}`)
      load()
    } catch (err) {
      alert(err.message)
    }
  }

  if (loading) return <Loading text="Loading products..." />
  if (error) return <ErrorMsg message={error} />

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, color: 'var(--heading)' }}>Products & Cost Management</h2>
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>Accurate cost prices enable automated margin calculations & risk capping</p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenAdd}>+ Add Product</button>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Category</th>
                <th>Selling Price</th>
                <th>Cost Price</th>
                <th>Gross Margin</th>
                <th>Cost Source</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center', padding: 24, color: 'var(--muted)' }}>No products found. Add your first product.</td></tr>
              )}
              {products.map(p => {
                const margin = p.margin_pct
                return (
                  <tr key={p.id}>
                    <td><strong>{p.name}</strong></td>
                    <td><span style={{ background: '#E2E8F0', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>{p.category}</span></td>
                    <td style={{ fontWeight: 600 }}>{fmt(p.sell_price)}</td>
                    <td style={{ color: p.cost_price ? '#334155' : 'var(--error)' }}>
                      {p.cost_price ? fmt(p.cost_price) : 'Missing'}
                    </td>
                    <td>
                      {margin != null ? (
                        <span style={{
                          fontWeight: 700,
                          color: margin >= 15 ? 'var(--success)' : margin >= 12 ? 'var(--warning)' : 'var(--error)'
                        }}>
                          {pct(margin)}
                        </span>
                      ) : '—'}
                    </td>
                    <td>
                      <span style={{ fontSize: 12, color: 'var(--muted)', textTransform: 'capitalize' }}>
                        {p.cost_source === 'bill' ? '🧾 Bill OCR' : '✍️ Manual'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${p.is_active ? 'badge-ok' : 'badge-blocked'}`}>
                        {p.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <button className="btn btn-ghost btn-sm" style={{ marginRight: 6 }} onClick={() => handleOpenEdit(p)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p.id)}>Deactivate</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {modalOpen && (
        <Modal
          title={editing ? "Edit Product" : "Add Product"}
          onClose={() => setModalOpen(false)}
        >
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Product Name *</label>
              <input
                className="form-input"
                required
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Parle-G 100g"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select
                className="form-select"
                value={form.category}
                onChange={e => setForm({ ...form, category: e.target.value })}
              >
                <option value="snacks">Snacks</option>
                <option value="beverages">Beverages</option>
                <option value="grocery">Grocery</option>
                <option value="dairy">Dairy</option>
                <option value="household">Household</option>
                <option value="personal_care">Personal Care</option>
                <option value="bakery">Bakery</option>
                <option value="general">General</option>
              </select>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Selling Price (₹) *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.1"
                  required
                  className="form-input"
                  value={form.sell_price}
                  onChange={e => setForm({ ...form, sell_price: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Cost Price (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="form-input"
                  value={form.cost_price}
                  onChange={e => setForm({ ...form, cost_price: e.target.value })}
                  placeholder="Wholesale cost"
                />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
              <button type="button" className="btn btn-ghost" onClick={() => setModalOpen(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">{editing ? 'Update' : 'Save Product'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

