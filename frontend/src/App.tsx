import { FormEvent, useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'

import { apiBaseUrl, hasSupabaseConfig, supabase } from './lib'

type EchoResponse = {
  message: string
}

type MeResponse = {
  sub: string | null
  email: string | null
  role: string | null
}

type ErrorResponse = {
  detail?: string
}

export default function App() {
  const [message, setMessage] = useState('Hello from the frontend')
  const [echoResponse, setEchoResponse] = useState<string>('')
  const [meResponse, setMeResponse] = useState<MeResponse | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [status, setStatus] = useState<string>('')

  useEffect(() => {
    if (!supabase) {
      return
    }

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
    })

    return () => subscription.unsubscribe()
  }, [])

  async function handleEchoSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus('Calling POST /api/echo...')

    const response = await fetch(`${apiBaseUrl}/api/echo`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      setStatus(`Echo request failed with status ${response.status}.`)
      return
    }

    const data = (await response.json()) as EchoResponse
    setEchoResponse(data.message)
    setStatus('Echo request completed.')
  }

  async function handleGoogleLogin() {
    if (!supabase) {
      setStatus('Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY first.')
      return
    }

    setStatus('Starting Google sign-in...')

    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
      },
    })

    if (error) {
      setStatus(error.message)
    }
  }

  async function handleLogout() {
    if (!supabase) {
      setStatus('Supabase is not configured.')
      return
    }

    const { error } = await supabase.auth.signOut()

    if (error) {
      setStatus(error.message)
      return
    }

    setMeResponse(null)
    setStatus('Signed out.')
  }

  async function handleGetProfile() {
    if (!session?.access_token) {
      setStatus('Sign in first to call GET /api/me.')
      return
    }

    setStatus('Calling protected endpoint...')

    const response = await fetch(`${apiBaseUrl}/api/me`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
    })

    if (!response.ok) {
      const error = (await response.json().catch(() => ({}))) as ErrorResponse
      setStatus(error.detail ?? `Protected request failed with status ${response.status}.`)
      return
    }

    const data = (await response.json()) as MeResponse
    setMeResponse(data)
    setStatus('Protected request completed.')
  }

  return (
    <main className="min-h-screen bg-slate-100 px-6 py-10 text-slate-900">
      <div className="mx-auto flex max-w-2xl flex-col gap-8 rounded-2xl bg-white p-6 shadow-sm">
        <section className="space-y-3">
          <h1 className="text-2xl font-semibold">Hackathon Starter</h1>
          <p className="text-sm text-slate-600">
            Plain React + FastAPI + Supabase starter for local development.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-medium">Echo API</h2>
          <form className="flex flex-col gap-3" onSubmit={handleEchoSubmit}>
            <input
              className="rounded-md border border-slate-300 px-3 py-2"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Type a message"
            />
            <button
              className="w-fit rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white"
              type="submit"
            >
              Send to POST /api/echo
            </button>
          </form>
          <div className="rounded-md bg-slate-50 p-3 text-sm">
            <span className="font-medium">Response:</span>{' '}
            {echoResponse || 'No response yet.'}
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-medium">Authentication</h2>
          <p className="text-sm text-slate-600">
            Google sign-in is handled by Supabase Auth in the frontend.
          </p>
          {!hasSupabaseConfig ? (
            <p className="text-sm text-amber-700">
              Add `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` to enable auth locally.
            </p>
          ) : null}
          <div className="text-sm">
            <span className="font-medium">Current user:</span>{' '}
            {session?.user?.email ?? 'Signed out'}
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white"
              type="button"
              onClick={handleGoogleLogin}
            >
              Sign in with Google
            </button>
            <button
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium"
              type="button"
              onClick={handleLogout}
            >
              Sign out
            </button>
            <button
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium"
              type="button"
              onClick={handleGetProfile}
            >
              Call GET /api/me
            </button>
          </div>
          <div className="rounded-md bg-slate-50 p-3 text-sm">
            <span className="font-medium">Protected response:</span>{' '}
            {meResponse ? JSON.stringify(meResponse, null, 2) : 'No protected response yet.'}
          </div>
        </section>

        <section className="rounded-md bg-slate-900 p-3 text-sm text-slate-100">
          {status || 'Ready.'}
        </section>
      </div>
    </main>
  )
}
