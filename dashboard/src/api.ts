export type AqiCategory = {
  code: string
  label: string
  color: string
}

export type AqiAssessment = {
  standard: string
  estimated: boolean
  limitations: string[]
  value: number | null
  category: AqiCategory | null
  primary_pollutant: string | null
}

export type PollutantValue = { value: number | null; unit: string }

export type City = {
  id: number
  code: string
  timezone: string
  name: string
  country: string
  latitude: number
  longitude: number
}

export type DashboardCity = {
  city: City
  latest: {
    observed_at: string
    source: string
    pollutants: Record<string, PollutantValue>
    aqi: AqiAssessment | null
  } | null
}

export type Dashboard = {
  summary: {
    cities_monitored: number
    cities_with_current_data: number
    last_observed_at: string | null
  }
  cities: DashboardCity[]
}

export type LatestObservation = {
  city: City
  source: string
  observed_at: string
  collected_at: string
  pollutants: Record<string, PollutantValue>
  aqi: AqiAssessment
}

export type PollutantTrend = {
  pollutant: string
  status: string
  percent_change: number | null
  direction: string | null
  current_observation_count: number
  baseline_observation_count: number
}

export type CityTrends = { trends: Record<string, PollutantTrend> }

const apiRoot = import.meta.env.VITE_API_URL ?? '/api/v1'

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${apiRoot}${path}`)
  if (!response.ok) throw new Error(`AeroC API returned ${response.status}`)
  return response.json() as Promise<T>
}

export const api = {
  dashboard: () => request<Dashboard>('/dashboard'),
  latest: (cityId: number) => request<LatestObservation>(`/cities/${cityId}/latest`),
  trends: (cityId: number) => request<CityTrends>(`/cities/${cityId}/trends?days=1`),
}
