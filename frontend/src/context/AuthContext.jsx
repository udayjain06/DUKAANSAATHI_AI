import React, { createContext, useContext, useEffect, useState } from 'react'
import api, { TOKEN_KEY } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [merchant, setMerchant] = useState(null)
  const [loading, setLoading] = useState(true)

  const verifySession = async () => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setUser(null)
      setMerchant(null)
      setLoading(false)
      return
    }

    try {
      const res = await api.get('/auth/me')
      if (res.data?.user) {
        setUser(res.data.user)
        setMerchant(res.data.merchant)
      }
    } catch (err) {
      localStorage.removeItem(TOKEN_KEY)
      setUser(null)
      setMerchant(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    verifySession()

    const handleExpired = () => {
      setUser(null)
      setMerchant(null)
    }

    window.addEventListener('auth:expired', handleExpired)
    return () => window.removeEventListener('auth:expired', handleExpired)
  }, [])

  const signUp = async (email, password, fullName, shopName, shopType) => {
    const res = await api.post('/auth/signup', {
      email,
      password,
      full_name: fullName,
      shop_name: shopName,
      shop_type: shopType || 'kirana',
    })
    if (res.data?.token) {
      localStorage.setItem(TOKEN_KEY, res.data.token)
      setUser(res.data.user)
      setMerchant(res.data.merchant)
    }
    return res.data
  }

  const signIn = async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    if (res.data?.token) {
      localStorage.setItem(TOKEN_KEY, res.data.token)
      setUser(res.data.user)
      setMerchant(res.data.merchant)
    }
    return res.data
  }

  const signInDemo = async () => {
    const res = await api.post('/auth/demo')
    if (res.data?.token) {
      localStorage.setItem(TOKEN_KEY, res.data.token)
      setUser(res.data.user)
      setMerchant(res.data.merchant)
    }
    return res.data
  }

  const signOut = async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // Ignore network errors on logout
    }
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('paytm_demo_user')
    setUser(null)
    setMerchant(null)
  }

  const resetPassword = async (email) => {
    // Password reset notification
    return { success: true, message: 'Password reset request received.' }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        merchant,
        loading,
        signUp,
        signIn,
        signInDemo,
        signOut,
        resetPassword,
        refreshSession: verifySession,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
