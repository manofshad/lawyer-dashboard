import { useEffect, useRef, useState, type MouseEvent, type RefObject } from 'react'
import type { Session } from '@supabase/supabase-js'
import maplibregl from 'maplibre-gl'

import {
  fetchLiabilityAnalysis,
  fetchIncidentsByAddress,
  type AddressIncidentLookupResponse,
  type CaseStrength,
  type IncidentMapData,
  type Incident,
  type IncidentEvent,
  IncidentLookupError,
  type LiabilityAnalysisResponse,
} from './incidents'
import { hasMapStyleConfig, hasSupabaseConfig, mapStyleUrl, supabase } from './lib'

const boroughLabels: Record<string, string> = {
  B: 'Brooklyn',
  M: 'Manhattan',
  Q: 'Queens',
  R: 'Staten Island',
  X: 'Bronx',
}

function parseDateValue(value: string): Date | null {
  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)

  if (dateOnlyMatch) {
    const [, year, month, day] = dateOnlyMatch
    const parsed = new Date(Number(year), Number(month) - 1, Number(day))
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }

  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function formatDate(value: string | null): string {
  if (!value) return 'Unknown'
  const parsed = parseDateValue(value)
  if (!parsed) return value

  const useUtcCalendarDate = /T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value)
  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...(useUtcCalendarDate ? { timeZone: 'UTC' } : {}),
  })
}

function isValidDate(value: string): boolean {
  return parseDateValue(value) !== null
}

function formatBoroughCode(code: string): string {
  return boroughLabels[code] ?? code
}

function formatLiabilitySignal(signal: LiabilityAnalysisResponse['liability_signal']): string {
  return signal === 'likely_liable' ? 'Likely liable' : 'Likely not liable'
}

function formatCaseStrength(strength: CaseStrength): string {
  if (strength === 'strong') return 'Strong'
  if (strength === 'maybe') return 'Maybe'
  return 'Weak'
}

function getStrengthClassName(strength: CaseStrength): string {
  if (strength === 'strong') return 'badge-success'
  if (strength === 'maybe') return 'badge-warning'
  return 'badge-danger'
}

function formatEventLabel(event: IncidentEvent): string {
  if (event.event_label) return event.event_label
  return event.event_type
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function getIncidentDurationDays(incident: Incident): number | null {
  if (!incident.reported_at || !incident.closed_at) return null

  const reportedAt = parseDateValue(incident.reported_at)
  const closedAt = parseDateValue(incident.closed_at)

  if (!reportedAt || !closedAt) return null

  const millisecondsPerDay = 24 * 60 * 60 * 1000
  const diffInDays = Math.round((closedAt.getTime() - reportedAt.getTime()) / millisecondsPerDay)

  if (diffInDays < 0) return null

  return diffInDays
}

function formatDurationLabel(days: number): string {
  return `${days} ${days === 1 ? 'day' : 'days'} open`
}

function getLongestIncidentDurationDays(incidents: Incident[]): number | null {
  const durations = incidents
    .map(getIncidentDurationDays)
    .filter((duration): duration is number => duration !== null)

  if (durations.length === 0) return null

  return Math.max(...durations)
}

type TimelineEvent = IncidentEvent & {
  kind: 'backend'
  incidentDurationDays: number | null
  incidentExternalId: string
  key: string
  sortIndex: number
}

type ClientIncidentTimelineEvent = {
  kind: 'client-incident'
  event_at: string
  incidentExternalId: string
  key: string
  label: string
  sortIndex: number
}

type TimelineItem = TimelineEvent | ClientIncidentTimelineEvent

function buildTimelineEvents(incidents: Incident[], clientIncidentDate: string): TimelineItem[] {
  const timelineEvents: TimelineItem[] = incidents.flatMap((incident, incidentIndex) =>
    incident.events.map((event, eventIndex) => {
      const durationDays = getIncidentDurationDays(incident)

      return {
        ...event,
        kind: 'backend' as const,
        incidentDurationDays: durationDays,
        incidentExternalId: incident.external_id,
        key: `event-${event.id}`,
        sortIndex: incidentIndex * 1000 + eventIndex,
      }
    }),
  )

  if (clientIncidentDate && isValidDate(clientIncidentDate)) {
    timelineEvents.push({
      kind: 'client-incident',
      event_at: clientIncidentDate,
      incidentExternalId: 'Client incident',
      key: `client-incident-${clientIncidentDate}`,
      label: 'Client Incident',
      sortIndex: -1,
    })
  }

  return timelineEvents.sort((left, right) => {
    const leftTime = parseDateValue(left.event_at)?.getTime() ?? Number.NaN
    const rightTime = parseDateValue(right.event_at)?.getTime() ?? Number.NaN
    const leftValid = Number.isFinite(leftTime)
    const rightValid = Number.isFinite(rightTime)
    if (!leftValid && !rightValid) return left.sortIndex - right.sortIndex
    if (!leftValid) return 1
    if (!rightValid) return -1
    if (leftTime !== rightTime) return leftTime - rightTime
    return left.sortIndex - right.sortIndex
  })
}

function getTimelineDotClassName(event: TimelineItem): string {
  if (event.kind === 'client-incident') return 'timeline-dot-client'

  const label = event.event_label?.trim().toLowerCase()

  if (label === 'reported') return 'timeline-dot-reported'
  if (label === 'closed') return 'timeline-dot-closed'
  return 'timeline-dot-neutral'
}

function getTimelineLabel(event: TimelineItem): string {
  if (event.kind === 'client-incident') return event.label
  return formatEventLabel(event)
}

function TopBar({
  userEmail,
  onSignOut,
}: {
  userEmail?: string
  onSignOut?: () => Promise<void>
}) {
  return (
    <header className="app-topbar">
      <div className="app-shell app-topbar-inner">
        <div className="brand-block">
          <div className="brand-mark">NY</div>
          <div>
            <p className="eyebrow">Municipal liability review</p>
            <p className="brand-title">NYCLegal</p>
          </div>
        </div>

        {userEmail && onSignOut && (
          <div className="topbar-actions">
            <div className="user-chip">
              <span className="user-chip-label">Signed in</span>
              <span className="user-chip-value">{userEmail}</span>
            </div>
            <button type="button" onClick={onSignOut} className="button-secondary">
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

function LoginPage() {
  const [authError, setAuthError] = useState('')

  async function handleGoogleSignIn() {
    if (!supabase) {
      setAuthError('Supabase is not configured on the frontend.')
      return
    }

    setAuthError('')
    const redirectTo = `${window.location.origin}${window.location.pathname}`
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo },
    })
    if (error) setAuthError(error.message)
  }

  return (
    <div className="app-screen">
      <TopBar />

      <main className="login-shell app-shell">
        <section className="login-hero">
          <p className="eyebrow">Operator workspace</p>
          <h1 className="hero-title">Turn NYC location history into a disciplined case-file review.</h1>
          <p className="hero-copy">
            Search an address, inspect historical incident timelines, and generate a preliminary
            liability screen without switching tools.
          </p>
          <div className="trust-list">
            <div className="trust-item">
              <span className="trust-title">Structured timeline review</span>
              <span className="trust-copy">Bring reported and closed incident events into one sequence.</span>
            </div>
            <div className="trust-item">
              <span className="trust-title">Authenticated access</span>
              <span className="trust-copy">Google sign-in gates lookup and analysis tools behind your workspace.</span>
            </div>
            <div className="trust-item">
              <span className="trust-title">Focused legal screening</span>
              <span className="trust-copy">Use case-strength signals as intake support, not final legal advice.</span>
            </div>
          </div>
        </section>

        <section className="auth-panel">
          <div className="auth-panel-head">
            <p className="eyebrow">Secure sign-in</p>
            <h2>Access the incident review desk</h2>
            <p>Use your firm account to open the authenticated incident search and screening workflow.</p>
          </div>

          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={!hasSupabaseConfig}
            className="button-primary auth-button"
          >
            Continue with Google
          </button>

          <div className="auth-footnote">
            {!hasSupabaseConfig && <p className="status-danger">Missing Supabase environment configuration.</p>}
            {authError && <p className="status-danger">{authError}</p>}
          </div>
        </section>
      </main>
    </div>
  )
}

function SearchPanel({
  address,
  loading,
  onAddressChange,
  onSubmit,
}: {
  address: string
  loading: boolean
  onAddressChange: (value: string) => void
  onSubmit: (event: { preventDefault(): void }) => void
}) {
  return (
    <section className="panel intake-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Address intake</p>
          <h1>Incident review</h1>
        </div>
      </div>

      <form className="intake-form" onSubmit={onSubmit}>
        <label className="field-block">
          <span className="field-label">Property or sidewalk address</span>
          <input
            className="text-input"
            value={address}
            onChange={(event) => onAddressChange(event.target.value)}
            placeholder="Enter an address, intersection, or location note"
            autoFocus
          />
        </label>

        <button type="submit" disabled={loading} className="button-primary intake-button">
          {loading ? 'Searching…' : 'Search records'}
        </button>
      </form>
    </section>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  )
}

function ResultsHeader({
  result,
  searchedAddress,
}: {
  result: AddressIncidentLookupResponse
  searchedAddress: string
}) {
  const longestDurationDays = getLongestIncidentDurationDays(result.incidents)

  return (
    <section className="panel results-header">
      <div className="results-header-top">
        <div className="results-header-copy">
          <div>
            <p className="eyebrow">Search result</p>
            <h2>{result.location.canonical_address}</h2>
          </div>

          <div className="results-meta">
            <span className="badge-muted">{formatBoroughCode(result.location.boro)}</span>
            {result.location.spec_loc && <span className="badge-muted">{result.location.spec_loc}</span>}
            <span className="results-query">Queried as “{searchedAddress}”</span>
          </div>
        </div>

        <div className="results-metrics">
          <MetricCard label="Incidents" value={`${result.incident_count}`} />
          <MetricCard label="Events" value={`${result.event_count}`} />
          <MetricCard
            label="Longest open"
            value={longestDurationDays === null ? 'Unavailable' : formatDurationLabel(longestDurationDays)}
          />
        </div>
      </div>

      <MapPanel mapData={result.map} />
    </section>
  )
}

const MAP_CONTEXT_ZOOM = 14.9
const MAP_BOUNDS_SPAN_THRESHOLD = 0.006
const MAP_MAX_BOUNDS_ZOOM = 15.2

function getMapCenter(mapData: IncidentMapData): [number, number] | null {
  if (mapData.center) return mapData.center
  if (!mapData.bbox) return null

  return [
    (mapData.bbox[0] + mapData.bbox[2]) / 2,
    (mapData.bbox[1] + mapData.bbox[3]) / 2,
  ]
}

function shouldUseBoundsFit(bbox: IncidentMapData['bbox']): bbox is [number, number, number, number] {
  if (!bbox) return false

  const lngSpan = Math.abs(bbox[2] - bbox[0])
  const latSpan = Math.abs(bbox[3] - bbox[1])
  return Math.max(lngSpan, latSpan) >= MAP_BOUNDS_SPAN_THRESHOLD
}

function createMapPinElement(): HTMLDivElement {
  const pin = document.createElement('div')
  pin.className = 'map-pin'
  pin.innerHTML = '<span class="map-pin-core"></span>'
  return pin
}

function MapPanel({ mapData }: { mapData: IncidentMapData | null }) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  const mapInstanceRef = useRef<maplibregl.Map | null>(null)

  useEffect(() => {
    if (!mapData || !mapContainerRef.current || !hasMapStyleConfig) {
      mapInstanceRef.current?.remove()
      mapInstanceRef.current = null
      return
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: mapStyleUrl,
      attributionControl: false,
      interactive: false,
    })

    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')

    map.on('load', () => {
      const center = getMapCenter(mapData)

      map.addSource('incident-location', {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: {
            canonicalAddress: mapData.location.canonical_address,
          },
          geometry: mapData.geometry,
        },
      } as maplibregl.GeoJSONSourceSpecification)

      map.addLayer({
        id: 'incident-location-line',
        type: 'line',
        source: 'incident-location',
        paint: {
          'line-color': '#31506e',
          'line-width': 4,
          'line-opacity': 0.72,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      })

      if (center) {
        new maplibregl.Marker({
          element: createMapPinElement(),
          anchor: 'bottom',
        })
          .setLngLat(center)
          .addTo(map)
      }

      if (shouldUseBoundsFit(mapData.bbox)) {
        map.fitBounds(
          [
            [mapData.bbox[0], mapData.bbox[1]],
            [mapData.bbox[2], mapData.bbox[3]],
          ],
          {
            padding: 72,
            duration: 0,
            maxZoom: MAP_MAX_BOUNDS_ZOOM,
          },
        )
        return
      }

      if (center) {
        map.jumpTo({
          center,
          zoom: MAP_CONTEXT_ZOOM,
        })
      }
    })

    mapInstanceRef.current = map

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [mapData])

  return (
    <div className="results-map-block">
      {mapData && hasMapStyleConfig ? (
        <div ref={mapContainerRef} className="map-canvas" aria-label="Incident location map" />
      ) : (
        <div className="map-empty-state">
          <p className={hasMapStyleConfig ? 'status-muted' : 'status-danger'}>
            {hasMapStyleConfig
              ? 'Map data is unavailable for this location.'
              : 'Map rendering is disabled until VITE_MAPTILER_API_KEY is configured.'}
          </p>
        </div>
      )}
    </div>
  )
}

function TimelineToolbar({
  canApplyClientDate,
  confirmedClientIncidentDate,
  draftClientIncidentDate,
  onApplyClientIncidentDate,
  onClearClientIncidentDate,
  onDraftClientIncidentDateChange,
}: {
  canApplyClientDate: boolean
  confirmedClientIncidentDate: string
  draftClientIncidentDate: string
  onApplyClientIncidentDate: () => void
  onClearClientIncidentDate: () => void
  onDraftClientIncidentDateChange: (value: string) => void
}) {
  return (
    <div className="timeline-toolbar">
      <div>
        <p className="eyebrow">Case comparison</p>
        <h3>Client incident date</h3>
      </div>

      <div className="timeline-toolbar-controls">
        <label className="field-inline">
          <span className="field-label">Date</span>
          <input
            type="date"
            className="text-input date-input"
            value={draftClientIncidentDate}
            onChange={(event) => onDraftClientIncidentDateChange(event.target.value)}
          />
        </label>

        <button
          type="button"
          onClick={onApplyClientIncidentDate}
          disabled={!canApplyClientDate}
          className="button-primary"
        >
          Apply date
        </button>

        <button
          type="button"
          onClick={onClearClientIncidentDate}
          disabled={!draftClientIncidentDate && !confirmedClientIncidentDate}
          className="button-secondary"
        >
          Clear
        </button>
      </div>

      <p className="field-help">
        {confirmedClientIncidentDate
          ? `Client incident is currently pinned to ${formatDate(confirmedClientIncidentDate)}.`
          : 'Apply a date to place the client event directly inside the incident sequence.'}
      </p>
    </div>
  )
}

function IncidentTimeline({
  incidents,
  clientIncidentDate,
}: {
  incidents: Incident[]
  clientIncidentDate: string
}) {
  const timelineEvents = buildTimelineEvents(incidents, clientIncidentDate)

  if (timelineEvents.length === 0) {
    return (
      <div className="timeline-empty">
        <p>No events recorded for this address.</p>
      </div>
    )
  }

  return (
    <ol className="timeline-list">
      {timelineEvents.map((event) => {
        const isClientIncident = event.kind === 'client-incident'
        let durationLabel: string | null = null

        if (
          event.kind === 'backend' &&
          event.incidentDurationDays !== null &&
          getTimelineLabel(event).trim().toLowerCase() === 'closed'
        ) {
          durationLabel = formatDurationLabel(event.incidentDurationDays)
        }

        return (
          <li key={event.key} className="timeline-item">
            <div className="timeline-date-block">
              <p className="timeline-date">{formatDate(event.event_at)}</p>
              <p className="timeline-date-subhead">{isClientIncident ? 'Client marker' : 'Recorded event'}</p>
            </div>

            <div className="timeline-line">
              <span className={`timeline-dot ${getTimelineDotClassName(event)}`} />
            </div>

            <div className={`timeline-card ${isClientIncident ? 'timeline-card-emphasis' : ''}`}>
              <div className="timeline-card-header">
                <div className="timeline-title-row">
                  <p className="timeline-title">{getTimelineLabel(event)}</p>
                  {durationLabel && <span className="badge-muted">{durationLabel}</span>}
                  {isClientIncident && <span className="badge-warning">Comparison point</span>}
                </div>
                <p className="timeline-incident-id">{event.incidentExternalId}</p>
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function TimelineSection({
  analysisLoading,
  confirmedClientIncidentDate,
  draftClientIncidentDate,
  incidents,
  onGenerateAnalysis,
  onApplyClientIncidentDate,
  onClearClientIncidentDate,
  onDraftClientIncidentDateChange,
}: {
  analysisLoading: boolean
  confirmedClientIncidentDate: string
  draftClientIncidentDate: string
  incidents: Incident[]
  onGenerateAnalysis: (event?: MouseEvent<HTMLButtonElement>) => void
  onApplyClientIncidentDate: () => void
  onClearClientIncidentDate: () => void
  onDraftClientIncidentDateChange: (value: string) => void
}) {
  const canApplyClientDate =
    Boolean(draftClientIncidentDate && isValidDate(draftClientIncidentDate)) &&
    draftClientIncidentDate !== confirmedClientIncidentDate

  return (
    <section className="panel timeline-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Evidence timeline</p>
          <h2>Incident sequence</h2>
        </div>
        <p className="section-copy">
          Review reported and closed events in order, then place the client date into the same historical frame.
        </p>
      </div>

      <TimelineToolbar
        canApplyClientDate={canApplyClientDate}
        confirmedClientIncidentDate={confirmedClientIncidentDate}
        draftClientIncidentDate={draftClientIncidentDate}
        onApplyClientIncidentDate={onApplyClientIncidentDate}
        onClearClientIncidentDate={onClearClientIncidentDate}
        onDraftClientIncidentDateChange={onDraftClientIncidentDateChange}
      />

      <IncidentTimeline incidents={incidents} clientIncidentDate={confirmedClientIncidentDate} />

      <div className="timeline-analysis-action">
        <div>
          <p className="eyebrow">Next step</p>
          <h3>Run timeline screening</h3>
          <p className="section-copy">
            Generate the liability review after you confirm the client incident date against the timeline.
          </p>
        </div>

        <button
          type="button"
          onClick={(event) => onGenerateAnalysis(event)}
          disabled={(!canApplyClientDate && !confirmedClientIncidentDate) || analysisLoading}
          className="button-primary timeline-analysis-button"
        >
          {analysisLoading ? 'Generating…' : 'Generate analysis'}
        </button>
      </div>
    </section>
  )
}

function AnalysisPanel({
  analysis,
  analysisError,
  analysisLoading,
  analysisPanelRef,
  confirmedClientIncidentDate,
  onGenerateAnalysis,
}: {
  analysis: LiabilityAnalysisResponse | null
  analysisError: string
  analysisLoading: boolean
  analysisPanelRef: RefObject<HTMLElement | null>
  confirmedClientIncidentDate: string
  onGenerateAnalysis: () => void
}) {
  const hasValidClientDate = Boolean(confirmedClientIncidentDate && isValidDate(confirmedClientIncidentDate))

  return (
    <section ref={analysisPanelRef} className="panel analysis-panel" tabIndex={-1}>
      <div className="section-heading compact analysis-heading">
        <div>
          <p className="eyebrow">AI screening</p>
          <h3>Timeline liability analysis</h3>
        </div>
        <p className="section-copy">
          Generate a short case-screening summary based on whether prior incidents were open by the client date.
        </p>
      </div>

      {!hasValidClientDate && (
        <div className="analysis-state">
          <p className="status-muted">Add and apply a client incident date to enable case screening.</p>
        </div>
      )}

      {hasValidClientDate && !analysisLoading && !analysis && !analysisError && (
        <div className="analysis-state">
          <p className="status-muted">
            Client incident date confirmed for {formatDate(confirmedClientIncidentDate)}. Generate the
            analysis from below the timeline to review the result here.
          </p>
        </div>
      )}

      {analysisLoading && (
        <div className="analysis-loading">
          <div className="skeleton-row short" />
          <div className="skeleton-row" />
          <div className="skeleton-row" />
          <p className="status-muted">Generating timeline analysis…</p>
        </div>
      )}

      {!analysisLoading && analysisError && (
        <div className="analysis-state analysis-error">
          <p className="status-danger">{analysisError}</p>
          <button type="button" onClick={onGenerateAnalysis} className="button-secondary">
            Try again
          </button>
        </div>
      )}

      {!analysisLoading && analysis && (
        <div className="analysis-result">
          <div className="analysis-badges">
            <span className="badge-muted">{formatLiabilitySignal(analysis.liability_signal)}</span>
            <span className={getStrengthClassName(analysis.case_strength)}>
              {formatCaseStrength(analysis.case_strength)}
            </span>
          </div>

          {analysis.best_matching_incident_id && analysis.best_matching_days_open !== null && (
            <div className="analysis-callout">
              Strongest supporting incident: {analysis.best_matching_incident_id} was open for{' '}
              {analysis.best_matching_days_open} day
              {analysis.best_matching_days_open === 1 ? '' : 's'} by the client incident date.
            </div>
          )}

          <p className="analysis-summary">{analysis.analysis_summary}</p>
          <p className="analysis-disclaimer">{analysis.disclaimer}</p>

          <button type="button" onClick={onGenerateAnalysis} className="button-secondary">
            Regenerate
          </button>
        </div>
      )}
    </section>
  )
}

function EmptyWorkspace() {
  return (
    <section className="panel empty-workspace">
      <p className="eyebrow">Ready for review</p>
      <h2>Search a location to open the incident workspace.</h2>
      <p className="section-copy">
        Results will populate with address normalization, incident counts, the full event timeline, and liability screening controls.
      </p>
    </section>
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
  const [draftClientIncidentDate, setDraftClientIncidentDate] = useState('')
  const [confirmedClientIncidentDate, setConfirmedClientIncidentDate] = useState('')
  const [result, setResult] = useState<AddressIncidentLookupResponse | null>(null)
  const [analysis, setAnalysis] = useState<LiabilityAnalysisResponse | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState('')
  const [searchedAddress, setSearchedAddress] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const analysisPanelRef = useRef<HTMLElement | null>(null)

  const userEmail = session.user.email ?? session.user.user_metadata.email ?? 'Unknown user'

  async function handleSearch(event: { preventDefault(): void }) {
    event.preventDefault()
    if (!address.trim()) return
    const nextAddress = address.trim()
    setLoading(true)
    setError('')
    setResult(null)
    setAnalysis(null)
    setAnalysisError('')
    setAnalysisLoading(false)
    setDraftClientIncidentDate('')
    setConfirmedClientIncidentDate('')
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

  useEffect(() => {
    setAnalysis(null)
    setAnalysisError('')
    setAnalysisLoading(false)
  }, [confirmedClientIncidentDate, result, searchedAddress])

  function handleApplyClientIncidentDate() {
    if (!draftClientIncidentDate || !isValidDate(draftClientIncidentDate)) return
    setConfirmedClientIncidentDate(draftClientIncidentDate)
  }

  function handleClearClientIncidentDate() {
    setDraftClientIncidentDate('')
    setConfirmedClientIncidentDate('')
  }

  async function handleGenerateAnalysis(event?: MouseEvent<HTMLButtonElement>) {
    if (
      !result ||
      !searchedAddress ||
      !confirmedClientIncidentDate ||
      !isValidDate(confirmedClientIncidentDate)
    ) {
      setAnalysis(null)
      setAnalysisError('Enter a valid incident date before generating the analysis.')
      setAnalysisLoading(false)
      return
    }

    event?.currentTarget.blur()

    if (analysisPanelRef.current) {
      analysisPanelRef.current.focus({ preventScroll: true })
      const top = analysisPanelRef.current.getBoundingClientRect().top + window.scrollY - 108
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
    }

    setAnalysis(null)
    setAnalysisLoading(true)
    setAnalysisError('')

    try {
      const data = await fetchLiabilityAnalysis(
        searchedAddress,
        confirmedClientIncidentDate,
        session.access_token,
      )
      setAnalysis(data)
    } catch (err) {
      if (err instanceof IncidentLookupError) {
        setAnalysisError(err.message)
        return
      }
      setAnalysisError('Unable to generate the timeline analysis right now.')
    } finally {
      setAnalysisLoading(false)
    }
  }

  return (
    <div className="app-screen">
      <TopBar userEmail={userEmail} onSignOut={onSignOut} />

      <main className="workspace-shell app-shell">
        <section className="workspace-main">
          <SearchPanel
            address={address}
            loading={loading}
            onAddressChange={setAddress}
            onSubmit={handleSearch}
          />

          {error && (
            <div className="panel error-panel">
              <p className="status-danger">{error}</p>
            </div>
          )}

          {!result && !error && !loading && <EmptyWorkspace />}

          {loading && (
            <section className="panel loading-panel">
              <p className="eyebrow">Searching records</p>
              <h2>Looking up location history…</h2>
              <div className="loading-stack">
                <div className="skeleton-row short" />
                <div className="skeleton-row" />
                <div className="skeleton-row" />
              </div>
            </section>
          )}

          {result && (
            <>
              <ResultsHeader result={result} searchedAddress={searchedAddress} />
              <TimelineSection
                analysisLoading={analysisLoading}
                confirmedClientIncidentDate={confirmedClientIncidentDate}
                draftClientIncidentDate={draftClientIncidentDate}
                incidents={result.incidents}
                onGenerateAnalysis={handleGenerateAnalysis}
                onApplyClientIncidentDate={handleApplyClientIncidentDate}
                onClearClientIncidentDate={handleClearClientIncidentDate}
                onDraftClientIncidentDateChange={setDraftClientIncidentDate}
              />
            </>
          )}
        </section>

        <aside className="workspace-rail">
          <AnalysisPanel
            analysis={analysis}
            analysisError={analysisError}
            analysisLoading={analysisLoading}
            analysisPanelRef={analysisPanelRef}
            confirmedClientIncidentDate={confirmedClientIncidentDate}
            onGenerateAnalysis={handleGenerateAnalysis}
          />
        </aside>
      </main>
    </div>
  )
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(!hasSupabaseConfig)

  useEffect(() => {
    if (!supabase) return

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
    if (!supabase) return
    await supabase.auth.signOut()
  }

  if (!ready) {
    return (
      <div className="app-loading-screen">
        <p className="status-muted">Loading session…</p>
      </div>
    )
  }

  if (!session) return <LoginPage />

  return <IncidentLookup session={session} onSignOut={handleSignOut} />
}
