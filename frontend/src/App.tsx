import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'

import {
  fetchIncidentsByAddress,
  IncidentLookupError,
  type AddressIncidentLookupResponse,
  type Incident,
  type IncidentLocation,
} from './incidents'
import { hasSupabaseConfig, supabase } from './lib'

const boroughLabels: Record<string, string> = {
  B: 'Brooklyn',
  M: 'Manhattan',
  Q: 'Queens',
  R: 'Staten Island',
  X: 'Bronx',
}

function formatDate(value: string | null): string {
  if (!value) {
    return 'Unknown'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatBoroughCode(code: string): string {
  return boroughLabels[code] ?? code
}

function getIncidentSummary(incident: Incident, location: IncidentLocation): string {
  const specLoc = typeof incident.raw_payload.SpecLoc === 'string' ? incident.raw_payload.SpecLoc : null

  if (specLoc) {
    return specLoc
  }

  if (location.spec_loc) {
    return location.spec_loc
  }

  const crossStreetParts = [location.from_street, location.to_street].filter(Boolean)
  if (crossStreetParts.length === 2) {
    return `Between ${crossStreetParts[0]} and ${crossStreetParts[1]}`
  }

  return location.street_name
}

function LoginPage() {
  const [authError, setAuthError] = useState('')

  async function handleGoogleSignIn() {
    if (!supabase) {
      setAuthError('Supabase is not configured on the frontend.')
      return
    }

    setAuthError('')

    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.href,
      },
    })

    if (error) {
      setAuthError(error.message)
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-slate-900">Hello!</h1>
          <p className="text-slate-500 text-sm">Sign in to access the incident lookup.</p>
        </div>

        <div className="space-y-4">
          <button
            className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-base font-medium text-white hover:bg-slate-700 disabled:opacity-50 transition-colors"
            type="button"
            onClick={handleGoogleSignIn}
            disabled={!hasSupabaseConfig}
          >
            Continue with Google
          </button>

          {!hasSupabaseConfig && (
            <p className="text-sm text-red-600">
              Missing `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` in the frontend environment.
            </p>
          )}

          {authError && (
            <p className="text-sm text-red-600">{authError}</p>
          )}
        </div>
      </div>
    </main>
  )
}

function IncidentCard({
  incident,
  location,
}: {
  incident: Incident
  location: IncidentLocation
}) {
  const summary = getIncidentSummary(incident, location)

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{incident.dataset_name}</p>
          <h2 className="text-lg font-semibold text-slate-900">{incident.external_id}</h2>
        </div>
        <span className="self-start rounded-full bg-slate-900 px-3 py-1 text-xs font-medium uppercase tracking-wide text-white">
          {incident.status}
        </span>
      </div>

      <p className="text-sm text-slate-700">{summary}</p>

      <div className="flex flex-wrap gap-2 text-xs text-slate-600">
        {incident.source && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1">Source: {incident.source}</span>
        )}
        {incident.initiated_by && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1">Initiated by: {incident.initiated_by}</span>
        )}
        <span className="rounded-full bg-slate-100 px-2.5 py-1">Events: {incident.events.length}</span>
      </div>

      <dl className="grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-400">Reported</dt>
          <dd>{formatDate(incident.reported_at)}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-400">Closed</dt>
          <dd>{formatDate(incident.closed_at)}</dd>
        </div>
      </dl>

      <p className="text-xs text-slate-400">
        {location.canonical_address} · {formatBoroughCode(location.boro)}
      </p>
    </div>
  )
}

function IncidentLookup({
  session,
  onSignOut,
}: {
  session: Session
  onSignOut: () => Promise<void>
}) {
  const [address, setAddress] = useState('')
  const [result, setResult] = useState<AddressIncidentLookupResponse | null>(null)
  const [searchedAddress, setSearchedAddress] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSearch(event: { preventDefault(): void }) {
    event.preventDefault()
    if (!address.trim()) {
      return
    }

    const nextAddress = address.trim()

    setLoading(true)
    setError('')
    setResult(null)
    setSearchedAddress(nextAddress)

    try {
      const data = await fetchIncidentsByAddress(nextAddress, session.access_token)
      setResult(data)
    } catch (err) {
      if (err instanceof IncidentLookupError) {
        if (err.status === 401) {
          setError('Your session expired. Please sign in again.')
          return
        }

        if (err.status === 404) {
          setError(`No incidents found for "${nextAddress}".`)
          return
        }

        if (err.status === 400) {
          setError(err.message)
          return
        }
      }

      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const userEmail = session.user.email ?? session.user.user_metadata.email ?? 'Unknown user'

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col items-center px-4">
      <div className="w-full max-w-2xl flex flex-col items-center gap-8 pt-24">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">Incident Lookup</h1>
          <p className="text-slate-500 text-lg">Search an address to see reported incidents</p>
          <div className="flex items-center justify-center gap-3 text-xs text-slate-400">
            <p>Signed in as {userEmail}</p>
            <button
              className="font-medium text-slate-600 hover:text-slate-900"
              type="button"
              onClick={onSignOut}
            >
              Sign out
            </button>
          </div>
        </div>

        <form className="w-full flex gap-2" onSubmit={handleSearch}>
          <input
            className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Enter an address..."
            autoFocus
          />
          <button
            className="rounded-xl bg-slate-900 px-6 py-3 text-base font-medium text-white hover:bg-slate-700 disabled:opacity-50 transition-colors"
            type="submit"
            disabled={loading}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && (
          <p className="text-red-600 text-sm">{error}</p>
        )}

        {result && (
          <div className="w-full space-y-4 pb-12">
            <p className="text-sm text-slate-500">
              {result.incident_count} incident{result.incident_count !== 1 ? 's' : ''} and {result.event_count} event{result.event_count !== 1 ? 's' : ''} found for "{searchedAddress}"
            </p>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Location</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{result.location.canonical_address}</p>
              <p className="mt-1 text-sm text-slate-600">
                Normalized address: {result.normalized_address}
              </p>
              <p className="mt-2 text-sm text-slate-500">
                {formatBoroughCode(result.location.boro)}
                {result.location.spec_loc ? ` · ${result.location.spec_loc}` : ''}
              </p>
            </div>

            {result.incidents.map((incident) => (
              <IncidentCard
                key={incident.id}
                incident={incident}
                location={result.location}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  )
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(!hasSupabaseConfig)

  useEffect(() => {
    if (!supabase) {
      return
    }

    let active = true

    void supabase.auth.getSession().then(({ data }) => {
      if (active) {
        setSession(data.session)
        setReady(true)
      }
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setReady(true)
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  async function handleSignOut() {
    if (!supabase) {
      return
    }

    await supabase.auth.signOut()
  }

  if (!ready) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <p className="text-sm text-slate-500">Loading session...</p>
      </main>
    )
  }

  if (!session) {
    return <LoginPage />
  }

  return <IncidentLookup session={session} onSignOut={handleSignOut} />
}
