import { apiBaseUrl } from './lib'

export type IncidentEvent = {
  id: number
  event_type: string
  event_at: string
  event_label: string | null
  metadata: Record<string, unknown>
}

export type Incident = {
  id: number
  external_id: string
  dataset_name: string
  source: string | null
  initiated_by: string | null
  reported_at: string
  closed_at: string | null
  status: string
  raw_payload: Record<string, unknown>
  events: IncidentEvent[]
}

export type IncidentLocation = {
  id: number
  canonical_address: string
  boro: string
  house_num: string | null
  street_name: string
  from_street: string | null
  to_street: string | null
  spec_loc: string | null
  location_key: string
}

export type GeoJsonLineString = {
  type: 'LineString'
  coordinates: [number, number][]
}

export type GeoJsonMultiLineString = {
  type: 'MultiLineString'
  coordinates: [number, number][][]
}

export type IncidentMapData = {
  normalized_address: string
  location: IncidentLocation
  geometry: GeoJsonLineString | GeoJsonMultiLineString
  bbox: [number, number, number, number] | null
  center: [number, number] | null
}

export type AddressIncidentLookupResponse = {
  address: string
  normalized_address: string
  location: IncidentLocation
  map: IncidentMapData | null
  incidents: Incident[]
  incident_count: number
  event_count: number
}

export type LiabilitySignal = 'likely_liable' | 'likely_not_liable'
export type CaseStrength = 'strong' | 'maybe' | 'weak'

export type LiabilityAnalysisResponse = {
  address: string
  client_incident_date: string
  liability_signal: LiabilitySignal
  case_strength: CaseStrength
  best_matching_incident_id: string | null
  best_matching_days_open: number | null
  analysis_summary: string
  disclaimer: string
}

export class IncidentLookupError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'IncidentLookupError'
    this.status = status
  }
}

export async function fetchIncidentsByAddress(
  address: string,
  accessToken: string,
): Promise<AddressIncidentLookupResponse> {
  const response = await fetch(`${apiBaseUrl}/api/incidents/by-address`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ address }),
  })

  if (!response.ok) {
    let detail = 'Something went wrong. Please try again.'

    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Ignore non-JSON error bodies and fall back to generic messaging.
    }

    throw new IncidentLookupError(detail, response.status)
  }

  return (await response.json()) as AddressIncidentLookupResponse
}

export async function fetchLiabilityAnalysis(
  address: string,
  clientIncidentDate: string,
  accessToken: string,
): Promise<LiabilityAnalysisResponse> {
  const response = await fetch(`${apiBaseUrl}/api/incidents/liability-analysis`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      address,
      client_incident_date: clientIncidentDate,
    }),
  })

  if (!response.ok) {
    let detail = 'Something went wrong. Please try again.'

    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        detail = payload.detail
      }
    } catch {
      // Ignore non-JSON error bodies and fall back to generic messaging.
    }

    throw new IncidentLookupError(detail, response.status)
  }

  return (await response.json()) as LiabilityAnalysisResponse
}
