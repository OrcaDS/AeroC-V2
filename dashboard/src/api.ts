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

export type PollutantValue = { value: number | null; unit: string | null }

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
  generated_at: string
  summary: {
    cities_monitored: number
    cities_with_current_data: number
    last_observed_at: string | null
    average_pm2_5: PollutantValue
    average_pm10: PollutantValue
  }
  leaders: {
    highest_pm2_5: { city_id: number; city_name: string; value: number; unit: string | null; observed_at: string } | null
    highest_pm10: { city_id: number; city_name: string; value: number; unit: string | null; observed_at: string } | null
    highest_ozone: { city_id: number; city_name: string; value: number; unit: string | null; observed_at: string } | null
    highest_aqi: { city_id: number; city_name: string; observed_at: string; aqi: AqiAssessment } | null
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

export class ApiRequestError extends Error {
  readonly status: number

  constructor(status: number) {
    super(`AeroC API returned ${status}`)
    this.name = 'ApiRequestError'
    this.status = status
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiRoot}${path}`, { signal })
  if (!response.ok) throw new ApiRequestError(response.status)
  return response.json() as Promise<T>
}

export const api = {
  dashboard: (signal?: AbortSignal) => request<Dashboard>('/dashboard', signal),
  latest: (cityId: number, signal?: AbortSignal) => request<LatestObservation>(`/cities/${cityId}/latest`, signal),
  trends: (cityId: number, signal?: AbortSignal) => request<CityTrends>(`/cities/${cityId}/trends?days=1`, signal),
}
