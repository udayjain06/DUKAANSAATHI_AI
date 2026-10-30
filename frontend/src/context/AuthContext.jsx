import React, { createContext, useContext, useEffect, useState } from 'react'
import { supabase, isSupabaseConfigured } from '../supabase'
import api from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 1. Initial local/saved session check
    const savedDemoUser = localStorage.getItem('paytm_demo_user')
    if (savedDemoUser) {
      try {
        const parsed = JSON.parse(savedDemoUser)
        setUser(parsed)
        api.defaults.headers.common['X-User-Id'] = parsed.id
        api.defaults.headers.common['X-User-Email'] = parsed.email
      } catch (e) {
        localStorage.removeItem('paytm_demo_user')
      }
    }

    if (isSupabaseConfigured()) {
      supabase.auth.getSession().then(({ data: { session } }) => {
        setSession(session)
        if (session?.user) {
          setUser(session.user)
          api.defaults.headers.common['X-User-Id'] = session.user.id
          api.defaults.headers.common['X-User-Email'] = session.user.email
        }
        setLoading(false)
      })

      const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        setSession(session)
        if (session?.user) {
          setUser(session.user)
          api.defaults.headers.common['X-User-Id'] = session.user.id
          api.defaults.headers.common['X-User-Email'] = session.user.email
        } else if (!localStorage.getItem('paytm_demo_user')) {
          setUser(null)
          delete api.defaults.headers.common['X-User-Id']
          delete api.defaults.headers.common['X-User-Email']
        }
        setLoading(false)
      })

      return () => subscription.unsubscribe()
    } else {
      setLoading(false)
    }
  }, [])

  const signUp = async (email, password, fullName) => {
    if (isSupabaseConfigured()) {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { full_name: fullName } },
      })
      if (error) throw error
      return data
    } else {
      // Demo authentication mode
      const demoUser = {
        id: `user_${Math.random().toString(36).substring(2, 9)}`,
        email,
        user_metadata: { full_name: fullName || email.split('@')[0] },
      }
      setUser(demoUser)
      localStorage.setItem('paytm_demo_user', JSON.stringify(demoUser))
      api.defaults.headers.common['X-User-Id'] = demoUser.id
      api.defaults.headers.common['X-User-Email'] = demoUser.email
      return { user: demoUser }
    }
  }

  const signIn = async (email, password) => {
    if (isSupabaseConfigured()) {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
      return data
    } else {
      const demoUser = {
        id: `user_${Math.random().toString(36).substring(2, 9)}`,
        email,
        user_metadata: { full_name: email.split('@')[0].toUpperCase() },
      }
      setUser(demoUser)
      localStorage.setItem('paytm_demo_user', JSON.stringify(demoUser))
      api.defaults.headers.common['X-User-Id'] = demoUser.id
      api.defaults.headers.common['X-User-Email'] = demoUser.email
      return { user: demoUser }
    }
  }

  const signOut = async () => {
    if (isSupabaseConfigured()) {
      await supabase.auth.signOut()
    }
    setUser(null)
    setSession(null)
    localStorage.removeItem('paytm_demo_user')
    delete api.defaults.headers.common['X-User-Id']
    delete api.defaults.headers.common['X-User-Email']
  }

  const resetPassword = async (email) => {
    if (isSupabaseConfigured()) {
      const { error } = await supabase.auth.resetPasswordForEmail(email)
      if (error) throw error
    }
    return { success: true }
  }

  return (
    <AuthContext.Provider value={{ user, session, loading, signUp, signIn, signOut, resetPassword }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
