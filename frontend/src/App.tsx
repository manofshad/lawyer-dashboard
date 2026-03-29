import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'

import {
  fetchIncidentsByAddress,
  IncidentLookupError,
  type AddressIncidentLookupResponse,
  type Incident,
  type IncidentEvent,
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
  if (!value) return 'Unknown'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatBoroughCode(code: string): string {
  return boroughLabels[code] ?? code
}

function formatEventLabel(event: IncidentEvent): string {
  if (event.event_label) return event.event_label
  return event.event_type
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

// ─── Navbar ──────────────────────────────────────────────────────────────────

function Navbar({
  userEmail,
  onSignOut,
}: {
  userEmail?: string
  onSignOut?: () => Promise<void>
}) {
  return (
    <nav
      className="w-full px-8 py-4 flex items-center justify-between border-b"
      style={{ background: '#1B3A6B', borderColor: '#163060' }}
    >
      <span
        className="text-xl font-bold tracking-wide select-none"
        style={{ color: '#FFFFFF' }}
      >
        NYCLegal
      </span>

      {userEmail && onSignOut && (
        <div className="flex items-center gap-4">
          <span className="text-sm hidden sm:block" style={{ color: '#A8C0E0' }}>
            {userEmail}
          </span>
          <button
            type="button"
            onClick={onSignOut}
            className="text-sm font-medium px-3 py-1.5 rounded-lg border transition-opacity hover:opacity-80"
            style={{ borderColor: '#3A6BA8', color: '#FFFFFF' }}
          >
            Sign out
          </button>
        </div>
      )}
    </nav>
  )
}

// ─── Login ───────────────────────────────────────────────────────────────────

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
      options: { redirectTo: window.location.href },
    })
    if (error) setAuthError(error.message)
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#EFF3F8' }}>
      <Navbar />

      <main className="flex-1 flex items-center justify-center px-4">
        <div
          className="w-full max-w-sm rounded-2xl border p-8 space-y-6"
          style={{ background: '#FFFFFF', borderColor: '#E2E8F0', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
        >
          <div className="space-y-1">
            <h1
              className="text-2xl font-bold"
              style={{ color: '#1A2B3C' }}
            >
              Welcome
            </h1>
            <p className="text-sm" style={{ color: '#718096' }}>
              Sign in to access the incident lookup.
            </p>
          </div>

          <div className="space-y-4">
            <button
              type="button"
              onClick={handleGoogleSignIn}
              disabled={!hasSupabaseConfig}
              className="w-full rounded-xl px-4 py-2.5 text-base font-semibold transition-opacity hover:opacity-85 disabled:opacity-40"
              style={{ background: '#2B72D7', color: '#FFFFFF' }}
            >
              Continue with Google
            </button>

            {!hasSupabaseConfig && (
              <p className="text-sm" style={{ color: '#C0504A' }}>
                Missing Supabase environment configuration.
              </p>
            )}
            {authError && (
              <p className="text-sm" style={{ color: '#C0504A' }}>
                {authError}
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

// ─── Timeline ────────────────────────────────────────────────────────────────

type TimelineEvent = IncidentEvent & {
  incidentExternalId: string
  sortIndex: number
}

function buildTimelineEvents(incidents: Incident[]): TimelineEvent[] {
  return incidents
    .flatMap((incident, incidentIndex) =>
      incident.events.map((event, eventIndex) => ({
        ...event,
        incidentExternalId: incident.external_id,
        sortIndex: incidentIndex * 1000 + eventIndex,
      })),
    )
    .sort((left, right) => {
      const leftTime = new Date(left.event_at).getTime()
      const rightTime = new Date(right.event_at).getTime()
      const leftValid = Number.isFinite(leftTime)
      const rightValid = Number.isFinite(rightTime)
      if (!leftValid && !rightValid) return left.sortIndex - right.sortIndex
      if (!leftValid) return 1
      if (!rightValid) return -1
      if (leftTime !== rightTime) return leftTime - rightTime
      return left.sortIndex - right.sortIndex
    })
}

function getTimelineDotColor(event: TimelineEvent): string {
  const label = event.event_label?.trim().toLowerCase()

  if (label === 'reported') return '#3DAA6A'
  if (label === 'closed') return '#C0504A'
  return '#A0AEC0'
}

function IncidentTimeline({ incidents }: { incidents: Incident[] }) {
  const timelineEvents = buildTimelineEvents(incidents)

  if (timelineEvents.length === 0) {
    return (
      <p className="text-sm py-4" style={{ color: '#718096' }}>
        No events recorded for this address.
      </p>
    )
  }

  return (
    <div className="pt-4">
      <div className="relative pl-8">
        {/* Vertical line */}
        <div
          aria-hidden="true"
          className="absolute bottom-0 left-3 top-0 w-px"
          style={{ background: '#E2E8F0' }}
        />

        <ol className="space-y-7">
          {timelineEvents.map((event) => {
            const dotColor = getTimelineDotColor(event)

            return (
              <li key={event.id} className="relative">
                {/* Timeline dot */}
                <span
                  aria-hidden="true"
                  className="absolute left-[-1.625rem] top-[0.35rem] h-3 w-3 rounded-full border-2"
                  style={{ background: dotColor, borderColor: '#FFFFFF' }}
                />

                {/* Date */}
                <p
                  className="text-xs uppercase tracking-[0.18em]"
                  style={{ color: '#A0AEC0' }}
                >
                  {formatDate(event.event_at)}
                </p>

                {/* Event label row */}
                <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <p className="text-base font-medium" style={{ color: '#1A2B3C' }}>
                    {formatEventLabel(event)}
                  </p>
                  <p className="text-sm" style={{ color: '#718096' }}>
                    {event.incidentExternalId}
                  </p>
                </div>
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}

// ─── Location + Incident Card ─────────────────────────────────────────────────

function LocationIncidentCard({
  result,
  searchedAddress,
}: {
  result: AddressIncidentLookupResponse
  searchedAddress: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="w-full space-y-4">
      <p className="text-sm" style={{ color: '#718096' }}>
        Results for &ldquo;{searchedAddress}&rdquo;
      </p>

      <div
        className="w-full rounded-xl border overflow-hidden"
        style={{ background: '#FFFFFF', borderColor: '#E2E8F0', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
      >
        {/* Location info */}
        <div className="px-5 pt-5 pb-4 space-y-1">
          <p className="text-xs uppercase tracking-[0.18em]" style={{ color: '#A0AEC0' }}>
            Location
          </p>
          <p className="text-lg font-semibold" style={{ color: '#1A2B3C' }}>
            {result.location.canonical_address}
          </p>
          <p className="text-sm" style={{ color: '#718096' }}>
            Normalized: {result.normalized_address}
          </p>
          <p className="text-sm" style={{ color: '#A0AEC0' }}>
            {formatBoroughCode(result.location.boro)}
            {result.location.spec_loc ? ` · ${result.location.spec_loc}` : ''}
          </p>
        </div>

        {/* Divider + toggle */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-3 border-t transition-colors hover:bg-gray-50"
          style={{ borderColor: '#E2E8F0' }}
        >
          <div className="flex flex-wrap items-center gap-3">
            <span
              className="text-sm font-semibold"
              style={{ color: '#2D3748' }}
            >
              Incident Timeline
            </span>
            <span
              className="text-xs px-2.5 py-0.5 rounded-full"
              style={{ background: '#EFF3F8', color: '#718096' }}
            >
              {result.incident_count} incident{result.incident_count !== 1 ? 's' : ''} &middot;{' '}
              {result.event_count} event{result.event_count !== 1 ? 's' : ''}
            </span>
          </div>

          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#A0AEC0"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              flexShrink: 0,
              transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s ease',
            }}
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        {/* Collapsible timeline */}
        {open && (
          <div className="px-5 pb-6 border-t" style={{ borderColor: '#E2E8F0' }}>
            <IncidentTimeline incidents={result.incidents} />
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Incident Lookup ─────────────────────────────────────────────────────────

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

  const userEmail =
    session.user.email ?? session.user.user_metadata.email ?? 'Unknown user'

  async function handleSearch(event: { preventDefault(): void }) {
    event.preventDefault()
    if (!address.trim()) return
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
        if (err.status === 401) { setError('Your session expired. Please sign in again.'); return }
        if (err.status === 404) { setError(`No incidents found for "${nextAddress}".`); return }
        if (err.status === 400) { setError(err.message); return }
      }
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#EFF3F8' }}>
      <Navbar userEmail={userEmail} onSignOut={onSignOut} />

      <main className="flex-1 flex flex-col items-center px-4 pt-14 pb-12">
        <div className="w-full max-w-2xl flex flex-col items-center gap-8">
          {/* Heading */}
          <div className="text-center space-y-2">
            <h1
              className="text-4xl font-bold"
              style={{ color: '#1A2B3C' }}
            >
              Incident Lookup
            </h1>
            <p className="text-lg" style={{ color: '#718096' }}>
              Search an address to see reported incidents
            </p>
          </div>

          {/* Search */}
          <form className="w-full flex gap-2" onSubmit={handleSearch}>
            <input
              className="flex-1 rounded-xl border px-4 py-3 text-base focus:outline-none focus:ring-2"
              style={{
                background: '#FFFFFF',
                borderColor: '#CBD5E0',
                color: '#1A2B3C',
              }}
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Enter an address..."
              autoFocus
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-xl px-6 py-3 text-base font-semibold transition-opacity hover:opacity-85 disabled:opacity-40"
              style={{ background: '#2B72D7', color: '#FFFFFF' }}
            >
              {loading ? 'Searching…' : 'Search'}
            </button>
          </form>

          {error && (
            <p className="text-sm" style={{ color: '#C0504A' }}>
              {error}
            </p>
          )}

          {result && (
            <LocationIncidentCard result={result} searchedAddress={searchedAddress} />
          )}
        </div>
      </main>
    </div>
  )
}

// ─── App root ─────────────────────────────────────────────────────────────────

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(!hasSupabaseConfig)

  useEffect(() => {
    if (!supabase) return
    let active = true
    void supabase.auth.getSession().then(({ data }) => {
      if (active) { setSession(data.session); setReady(true) }
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setReady(true)
    })
    return () => { active = false; subscription.unsubscribe() }
  }, [])

  async function handleSignOut() {
    if (!supabase) return
    await supabase.auth.signOut()
  }

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#EFF3F8' }}>
        <p className="text-sm" style={{ color: '#718096' }}>Loading session…</p>
      </div>
    )
  }

  if (!session) return <LoginPage />

  return <IncidentLookup session={session} onSignOut={handleSignOut} />
}
