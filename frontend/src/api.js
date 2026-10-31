import axios from 'axios'

// Normalize baseURL so that whether VITE_API_URL is:
// - not set (defaults to '/api' for Vite dev proxy)
// - set to 'https://backend.onrender.com' -> automatically appends '/api'
// - set to 'https://backend.onrender.com/api' -> keeps as is
const rawBase = import.meta.env.VITE_API_URL || '/api'
const cleanBase = rawBase.replace(/\/+$/, '')
const baseURL = cleanBase.endsWith('/api') ? cleanBase : `${cleanBase}/api`

export const TOKEN_KEY = 'dukaansaathi_auth_token'

const api = axios.create({
  baseURL,
  timeout: 15000,
})

// Automatically attach JWT token to all requests & normalize paths
api.interceptors.request.use((config) => {
  if (config.url) {
    // If baseURL already ends with /api, strip redundant leading /api from endpoint path
    if (baseURL.endsWith('/api') && config.url.startsWith('/api/')) {
      config.url = config.url.slice(4)
    }
  }
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => Promise.reject(error))

// Handle session expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const isAuthUrl = error.config?.url?.includes('/auth/login') || error.config?.url?.includes('/auth/signup')
      if (!isAuthUrl) {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem('paytm_demo_user')
        if (window.location.pathname !== '/auth') {
          // Allow current UI to update without hard refresh loop
          window.dispatchEvent(new CustomEvent('auth:expired'))
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api

// Helper to format INR
export const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`
export const pct = (n) => `${Number(n || 0).toFixed(1)}%`
