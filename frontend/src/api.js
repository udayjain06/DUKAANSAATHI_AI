import axios from 'axios'

// Normalize baseURL so that whether VITE_API_URL is:
// - not set (defaults to '/api' for Vite dev proxy)
// - set to 'https://backend.onrender.com' -> automatically appends '/api'
// - set to 'https://backend.onrender.com/api' -> keeps as is
const rawBase = import.meta.env.VITE_API_URL || '/api'
const cleanBase = rawBase.replace(/\/+$/, '')
const baseURL = cleanBase.endsWith('/api') ? cleanBase : `${cleanBase}/api`

const api = axios.create({
  baseURL,
  timeout: 15000,
})

export default api

// Helper to format INR
export const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`
export const pct = (n) => `${Number(n || 0).toFixed(1)}%`
