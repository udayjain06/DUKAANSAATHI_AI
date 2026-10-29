import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export default api

// Helper to format INR
export const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`
export const pct = (n) => `${Number(n || 0).toFixed(1)}%`

