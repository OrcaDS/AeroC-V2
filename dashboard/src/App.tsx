import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { Dashboard, DashboardCity, LatestObservation, PollutantTrend } from './api'
import { api } from './api'
import 'leaflet/dist/leaflet.css'
import './App.css'

type Screen = { name: 'overview' } | { name: 'city'; cityId: number }

const categoryFallback = '#758195'

function parseScreen(): Screen {
  const match = window.location.hash.match(/^#\/cities\/(\d+)/)
  return match ? { name: 'city', cityId: Number(match[1]) } : { name: 'overview' }
}

function formatTime(value: string | null) {
  if (!value) return 'Unavailable'
  return new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false }).format(new Date(value)) + ' UTC'
}

function formatNumber(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : value.toLocaleString(undefined, { maximumFractionDigits: 1 })
}

function markerColor(city: DashboardCity) {
  return city.latest?.aqi?.category?.color ?? categoryFallback
}

function MapBounds({ cities }: { cities: DashboardCity[] }) {
  const map = useMap()
  useEffect(() => {
    const points = cities.filter((entry) => entry.latest).map(({ city }) => [city.latitude, city.longitude] as [number, number])
    if (points.length) map.fitBounds(points, { padding: [48, 48], maxZoom: 5 })
  }, [cities, map])
  return null
}

function Sidebar({ active, onOverview }: { active: 'overview' | 'city'; onOverview: () => void }) {
  return <aside className="sidebar">
    <button className="brand" onClick={onOverview} aria-label="Go to monitoring overview"><span className="brand-mark">◒</span>AeroC</button>
    <nav>
      <button className={active === 'overview' ? 'nav-item active' : 'nav-item'} onClick={onOverview}><span>◎</span>Overview</button>
      <span className={active === 'city' ? 'nav-item active' : 'nav-item'}><span>⌖</span>Cities</span>
      <span className="nav-item"><span>▣</span>Data source</span>
    </nav>
    <p className="sidebar-foot">Environmental intelligence<br />from provider snapshots</p>
  </aside>
}

function SelectedCity({ entry, onOpen }: { entry: DashboardCity; onOpen: () => void }) {
  const latest = entry.latest
  if (!latest) return <div className="city-panel muted-panel">No current provider snapshot is available for {entry.city.name}.</div>
  const aqi = latest.aqi
  const pm25 = latest.pollutants.pm2_5
  return <aside className="city-panel">
    <p className="eyebrow">Selected city</p>
    <h2>{entry.city.name}</h2>
    <div className="aqi-lockup" style={{ '--severity': aqi?.category?.color ?? categoryFallback } as CSSProperties}>
      <span className="aqi-value">{formatNumber(aqi?.value)}</span>
      <div><p className="eyebrow">Estimated AQI</p><strong>{aqi?.category?.label ?? 'Unavailable'}</strong></div>
    </div>
    <dl className="evidence-list">
      <div><dt>Primary pollutant</dt><dd>{aqi?.primary_pollutant?.replace('_', '.').toUpperCase() ?? '—'}</dd></div>
      <div><dt>PM2.5</dt><dd>{formatNumber(pm25?.value)} {pm25?.unit ?? ''}</dd></div>
      <div><dt>Observed</dt><dd>{formatTime(latest.observed_at)}</dd></div>
      <div><dt>Source</dt><dd>{latest.source}</dd></div>
    </dl>
    <button className="text-action" onClick={onOpen}>Open city intelligence <span>→</span></button>
  </aside>
}

function Overview({ data, onOpenCity }: { data: Dashboard; onOpenCity: (cityId: number) => void }) {
  const withData = useMemo(() => data.cities.filter((entry) => entry.latest), [data])
  const priority = useMemo(() => [...withData].sort((a, b) => (b.latest?.aqi?.value ?? -1) - (a.latest?.aqi?.value ?? -1)), [withData])
  const [selectedId, setSelectedId] = useState<number | null>(priority[0]?.city.id ?? null)
  const selected = data.cities.find((entry) => entry.city.id === selectedId) ?? priority[0]

  useEffect(() => { if (!selectedId && priority[0]) setSelectedId(priority[0].city.id) }, [priority, selectedId])

  return <main className="overview-shell">
    <header className="page-header"><div><p className="eyebrow">Environmental intelligence</p><h1>Monitoring overview</h1></div></header>
    <p className="context-line"><strong>{data.summary.cities_with_current_data} cities with current data</strong><span>•</span>Latest provider-valid hour: {formatTime(data.summary.last_observed_at)}<span>•</span>Open-Meteo / CAMS</p>
    {withData.length === 0 ? <EmptyState /> : <>
      <section className="map-workspace" aria-label="Current air quality map">
        <MapContainer className="map" center={[5, 120]} zoom={4} scrollWheelZoom>
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <MapBounds cities={withData} />
          {withData.map((entry) => <CircleMarker key={entry.city.id} center={[entry.city.latitude, entry.city.longitude]} radius={18} pathOptions={{ color: selected?.city.id === entry.city.id ? '#12365a' : '#fff', weight: selected?.city.id === entry.city.id ? 3 : 2, fillColor: markerColor(entry), fillOpacity: 1 }} eventHandlers={{ click: () => setSelectedId(entry.city.id) }}>
            <Tooltip permanent direction="right" offset={[14, 0]}>{formatNumber(entry.latest?.aqi?.value)} <strong>{entry.city.name}</strong></Tooltip>
          </CircleMarker>)}
        </MapContainer>
        {selected && <SelectedCity entry={selected} onOpen={() => onOpenCity(selected.city.id)} />}
        <div className="map-legend"><strong>Estimated AQI</strong><span>Model snapshot</span><div><i className="good" />Good <i className="moderate" />Moderate <i className="sensitive" />Sensitive groups</div></div>
      </section>
      <section className="priority-section"><div className="section-heading"><div><p className="eyebrow">Where to investigate</p><h2>Priority locations</h2></div><p>Ranked by current estimated AQI</p></div>
        <div className="priority-list">{priority.map((entry, index) => <button className="priority-row" key={entry.city.id} onClick={() => onOpenCity(entry.city.id)}><span className="rank">{String(index + 1).padStart(2, '0')}</span><strong>{entry.city.name}</strong><span className="aqi-small" style={{ color: markerColor(entry) }}>{formatNumber(entry.latest?.aqi?.value)}</span><span>{entry.latest?.aqi?.category?.label ?? 'No AQI'}</span><span>{formatTime(entry.latest?.observed_at ?? null)}</span><span aria-hidden="true">→</span></button>)}</div>
      </section>
      <p className="disclosure">ⓘ Estimated AQI reflects a provider model snapshot. It is not an official EPA AQI.</p>
    </>}
  </main>
}

function TrendRow({ label, trend }: { label: string; trend?: PollutantTrend }) {
  if (!trend || trend.status !== 'ok') return <div className="trend-row"><strong>{label}</strong><span>Insufficient data</span><small>{trend ? `${trend.current_observation_count} / ${trend.baseline_observation_count} observations` : 'No observations'}</small></div>
  const direction = trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→'
  return <div className="trend-row"><strong>{label}</strong><span className={`trend ${trend.direction}`}>{direction} {trend.direction ?? 'flat'} {formatNumber(Math.abs(trend.percent_change ?? 0))}%</span><small>24h vs prior 24h · {trend.current_observation_count} observations</small></div>
}

function CityIntelligence({ cityId, onOverview }: { cityId: number; onOverview: () => void }) {
  const [latest, setLatest] = useState<LatestObservation | null>(null)
  const [trends, setTrends] = useState<Record<string, PollutantTrend>>({})
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { Promise.all([api.latest(cityId), api.trends(cityId)]).then(([observation, result]) => { setLatest(observation); setTrends(result.trends) }).catch((reason: Error) => setError(reason.message)) }, [cityId])
  if (error) return <main className="content-message"><h1>City data unavailable</h1><p>{error}. Return to the overview and try again.</p><button className="text-action" onClick={onOverview}>Back to overview</button></main>
  if (!latest) return <main className="content-message"><p className="eyebrow">Loading city intelligence</p><h1>Preparing evidence…</h1></main>
  const pollutantEntries = Object.entries(latest.pollutants)
  return <main className="city-shell"><button className="breadcrumb" onClick={onOverview}>Monitoring overview</button><span className="slash">/</span><span>{latest.city.name}</span>
    <header className="city-header"><div><p className="eyebrow">{latest.city.code} · {latest.city.country}</p><h1>{latest.city.name}</h1><p>Latest provider-valid hour: {formatTime(latest.observed_at)}</p></div></header>
    <section className="city-top"><div className="aqi-hero" style={{ '--severity': latest.aqi.category?.color ?? categoryFallback } as CSSProperties}><p className="eyebrow">Estimated AQI</p><div>{formatNumber(latest.aqi.value)}</div><strong>{latest.aqi.category?.label}</strong><p>Primary pollutant: {latest.aqi.primary_pollutant?.replace('_', '.').toUpperCase()}</p><small>ⓘ Model snapshot · Not an official EPA AQI</small></div>
      <div className="observations"><div className="section-heading"><div><p className="eyebrow">Evidence</p><h2>Current observations</h2></div><p>Observed {formatTime(latest.observed_at)}<br />Collected {formatTime(latest.collected_at)}</p></div>{pollutantEntries.map(([name, value]) => <div className="observation-row" key={name}><span>{name.replace('_', '.').toUpperCase()}</span><strong>{formatNumber(value.value)} <small>{value.unit}</small></strong></div>)}<p className="source-note">Source: {latest.source}</p></div>
    </section>
    <section className="trends-panel"><div className="section-heading"><div><p className="eyebrow">Server-calculated comparison</p><h2>What changed</h2></div><p>Current 24h vs prior 24h</p></div><div className="trend-grid"><TrendRow label="PM2.5" trend={trends.pm2_5} /><TrendRow label="PM10" trend={trends.pm10} /><TrendRow label="Ozone" trend={trends.ozone} /><TrendRow label="Nitrogen dioxide" trend={trends.nitrogen_dioxide} /></div></section>
    <p className="disclosure">ⓘ Values are provider model snapshots preserved by AeroC at collection time. They are estimates, not regulatory measurements.</p>
  </main>
}

function EmptyState() { return <section className="content-message"><p className="eyebrow">No current provider snapshots</p><h1>The monitoring map will appear after collection.</h1><p>AeroC will show locations only once the API has current city data. No environmental status is inferred while evidence is unavailable.</p></section> }

function App() {
  const [screen, setScreen] = useState<Screen>(parseScreen)
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api.dashboard().then(setDashboard).catch((reason: Error) => setError(reason.message)) }, [])
  useEffect(() => { const sync = () => setScreen(parseScreen()); window.addEventListener('hashchange', sync); return () => window.removeEventListener('hashchange', sync) }, [])
  const openOverview = () => { window.location.hash = '#/' }
  const openCity = (cityId: number) => { window.location.hash = `#/cities/${cityId}` }
  return <div className="app-shell"><Sidebar active={screen.name === 'overview' ? 'overview' : 'city'} onOverview={openOverview} />{error ? <main className="content-message"><p className="eyebrow">Connection unavailable</p><h1>AeroC data could not be loaded.</h1><p>{error}. Confirm the API is running and set <code>VITE_API_URL</code> if it is not at the local default.</p></main> : !dashboard ? <main className="content-message"><p className="eyebrow">Loading AeroC</p><h1>Retrieving current environmental evidence…</h1></main> : screen.name === 'city' ? <CityIntelligence cityId={screen.cityId} onOverview={openOverview} /> : <Overview data={dashboard} onOpenCity={openCity} />}</div>
}

export default App
