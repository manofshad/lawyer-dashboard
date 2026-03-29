import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ''
const mapTilerApiKey = import.meta.env.VITE_MAPTILER_API_KEY ?? ''

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const mapStyleUrl =
  import.meta.env.VITE_MAP_STYLE_URL ??
  (mapTilerApiKey
    ? `https://api.maptiler.com/maps/streets-v2/style.json?key=${encodeURIComponent(mapTilerApiKey)}`
    : '')
export const hasMapStyleConfig = Boolean(mapStyleUrl)

export const supabase =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      })
    : null

export const hasSupabaseConfig = Boolean(supabase)
