import React, { useEffect, useState } from 'react'
import api, { fmt, pct } from '../api'
import { Loading, ErrorMsg, Modal, Badge } from '../components/UI'

export default function Products() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCat, setSelectedCat] = useState('all')
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

  if (loading) return <Loading text="Loading catalog & costs..." />
  if (error) return <ErrorMsg message={error} />

  const filteredProducts = products.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          p.category.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCat = selectedCat === 'all' || p.category === selectedCat
    return matchesSearch && matchesCat
  })

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22, flexWrap: 'wrap', gap: 14 }}>
        <div>
          <h2 style={{ fontSize: 20, color: 'var(--heading)', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Products & Cost Management
          </h2>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
            Accurate wholesale costs ensure automated margin protection and risk limits for all promotional offers.
          </p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenAdd}>
          + Add New Product
        </button>
      </div>

      {/* Filter and search bar */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 18, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          className="form-input"
          placeholder="🔍 Search products by name or category..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          style={{ maxWidth: 320, padding: '8px 14px', fontSize: 13 }}
        />
        <select
          className="form-select"
          value={selectedCat}
          onChange={e => setSelectedCat(e.target.value)}
          style={{ maxWidth: 180, padding: '8px 12px', fontSize: 13 }}
        >
          <option value="all">All Categories</option>
          <option value="snacks">Snacks</option>
          <option value="beverages">Beverages</option>
          <option value="grocery">Grocery</option>
          <option value="dairy">Dairy</option>
          <option value="household">Household</option>
          <option value="personal_care">Personal Care</option>
          <option value="bakery">Bakery</option>
          <option value="general">General</option>
        </select>
        <span style={{ fontSize: 12, color: 'var(--muted)', marginLeft: 'auto' }}>
          Showing {filteredProducts.length} of {products.length} items
        </span>
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
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: 36, color: 'var(--muted)' }}>
                    No matching products found. Try adjusting filters or add a new product.
                  </td>
                </tr>
              )}
              {filteredProducts.map(p => {
                const margin = p.margin_pct
                return (
                  <tr key={p.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--heading)' }}>{p.name}</div>
                    </td>
                    <td>
                      <span style={{
                        background: 'var(--surface)',
                        color: 'var(--body)',
                        padding: '3px 9px',
                        borderRadius: 6,
                        fontSize: 12.5,
                        fontWeight: 500,
                        textTransform: 'capitalize'
                      }}>
                        {p.category}
                      </span>
                    </td>
                    <td style={{ fontWeight: 650 }}>{fmt(p.sell_price)}</td>
                    <td style={{ color: p.cost_price ? 'var(--body)' : 'var(--error)', fontWeight: p.cost_price ? 500 : 600 }}>
                      {p.cost_price ? fmt(p.cost_price) : 'Missing Cost'}
                    </td>
                    <td>
                      {margin != null ? (
                        <span style={{
                          fontWeight: 700,
                          fontSize: 13,
                          color: margin >= 15 ? 'var(--success)' : margin >= 12 ? 'var(--warning)' : 'var(--error)'
                        }}>
                          {pct(margin)}
                        </span>
                      ) : '—'}
                    </td>
                    <td>
                      <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                        {p.cost_source === 'bill' ? '🧾 Bill OCR' : '✍️ Manual'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${p.is_active ? 'badge-ok' : 'badge-blocked'}`}>
                        {p.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ marginRight: 6 }}
                        onClick={() => handleOpenEdit(p)}
                      >
                        Edit
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        style={{ background: 'var(--error-soft)', color: 'var(--error)', border: 'none' }}
                        onClick={() => handleDelete(p.id)}
                      >
                        Deactivate
                      </button>
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
          title={editing ? "Edit Product Details" : "Add New Product"}
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
                placeholder="e.g. Parle-G 100g, Amul Butter 500g"
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
                  placeholder="Retail price"
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
                  placeholder="Wholesale unit cost"
                />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
              <button type="button" className="btn btn-ghost" onClick={() => setModalOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                {editing ? 'Update Product' : 'Save Product'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
