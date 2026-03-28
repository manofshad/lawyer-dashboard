import { useState } from 'react'

type Incident = {
  id: string
  date: string
  type: string
  description: string
  address: string
}

const MOCK_INCIDENTS: Incident[] = [
  {
    id: '1',
    date: '2024-11-03',
    type: 'Slip and Fall',
    description: 'Wet pavement near crosswalk caused pedestrian to fall.',
    address: '123 Main St, New York, NY',
  },
  {
    id: '2',
    date: '2024-08-15',
    type: 'Pothole Damage',
    description: 'Large pothole caused vehicle damage and minor injuries.',
    address: '123 Main St, New York, NY',
  },
  {
    id: '3',
    date: '2023-12-22',
    type: 'Sidewalk Defect',
    description: 'Raised sidewalk slab caused trip and fall injury.',
    address: '123 Main St, New York, NY',
  },
]

async function fetchIncidents(_address: string): Promise<Incident[]> {
  // TODO: replace with real API call once backend is ready
  // const response = await fetch(`/api/incidents?address=${encodeURIComponent(address)}`)
  // return response.json()
  await new Promise((r) => setTimeout(r, 600))
  return MOCK_INCIDENTS
}

function LoginPage({ onLogin }: { onLogin: (email: string) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function handleSubmit(event: { preventDefault(): void }) {
    event.preventDefault()
    if (!email.trim() || !password) return
    // TODO: replace with real auth call
    onLogin(email.trim())
  }

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-slate-900">Hello!</h1>
          <p className="text-slate-500 text-sm">Sign in to access the incident lookup.</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              className="w-full rounded-xl border border-slate-300 px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-slate-400"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoFocus
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="w-full rounded-xl border border-slate-300 px-4 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-slate-400"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <button
            className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-base font-medium text-white hover:bg-slate-700 transition-colors"
            type="submit"
          >
            Sign in
          </button>
        </form>
      </div>
    </main>
  )
}

function IncidentLookup({ userEmail }: { userEmail: string }) {
  const [address, setAddress] = useState('')
  const [incidents, setIncidents] = useState<Incident[] | null>(null)
  const [searchedAddress, setSearchedAddress] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSearch(event: { preventDefault(): void }) {
    event.preventDefault()
    if (!address.trim()) return

    setLoading(true)
    setError('')
    setIncidents(null)

    try {
      const data = await fetchIncidents(address.trim())
      setIncidents(data)
      setSearchedAddress(address.trim())
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col items-center px-4">
      <div className="w-full max-w-2xl flex flex-col items-center gap-8 pt-24">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">Incident Lookup</h1>
          <p className="text-slate-500 text-lg">Search an address to see reported incidents</p>
          <p className="text-xs text-slate-400">Signed in as {userEmail}</p>
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

        {incidents && (
          <div className="w-full space-y-4 pb-12">
            <p className="text-sm text-slate-500">
              {incidents.length === 0
                ? `No incidents found for "${searchedAddress}"`
                : `${incidents.length} incident${incidents.length !== 1 ? 's' : ''} found for "${searchedAddress}"`}
            </p>
            {incidents.map((incident) => (
              <div
                key={incident.id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800">{incident.type}</span>
                  <span className="text-sm text-slate-400">{incident.date}</span>
                </div>
                <p className="text-sm text-slate-600">{incident.description}</p>
                <p className="text-xs text-slate-400">{incident.address}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}

export default function App() {
  const [userEmail, setUserEmail] = useState<string | null>(null)

  if (!userEmail) {
    return <LoginPage onLogin={setUserEmail} />
  }

  return <IncidentLookup userEmail={userEmail} />
}
