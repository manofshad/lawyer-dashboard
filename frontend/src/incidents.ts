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

export type AddressIncidentLookupResponse = {
  address: string
  normalized_address: string
  location: IncidentLocation
  incidents: Incident[]
  incident_count: number
  event_count: number
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
