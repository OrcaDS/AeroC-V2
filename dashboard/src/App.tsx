import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { AqiCategory, Dashboard, DashboardCity, LatestObservation, PollutantTrend } from './api'
import { api, ApiRequestError } from './api'
import 'leaflet/dist/leaflet.css'
import './App.css'

type Screen = { name: 'overview' } | { name: 'city'; cityId: number } | { name: 'cities' } | { name: 'source' }

const markerFallback = '#758195'

const aqiVisuals: Record<string, { foreground: string; surface: string }> = {
  good: { foreground: '#126B3A', surface: '#EAF8EF' },
  moderate: { foreground: '#6B5300', surface: '#FFF7D1' },
  unhealthy_for_sensitive_groups: { foreground: '#914300', surface: '#FFF0E3' },
  unhealthy: { foreground: '#B42318', surface: '#FDECEA' },
  very_unhealthy: { foreground: '#762A7C', surface: '#F5EAF7' },
  hazardous: { foreground: '#68102F', surface: '#F6E8ED' },
  unknown: { foreground: '#52677D', surface: '#EEF3F6' },
}

const aqiLegendItems = [
  { code: 'good', label: 'Good', marker: '#00E400' },
  { code: 'moderate', label: 'Moderate', marker: '#FFFF00' },
  { code: 'unhealthy_for_sensitive_groups', label: 'Unhealthy for sensitive groups', marker: '#FF7E00' },
  { code: 'unhealthy', label: 'Unhealthy', marker: '#FF0000' },
  { code: 'very_unhealthy', label: 'Very unhealthy', marker: '#8F3F97' },
  { code: 'hazardous', label: 'Hazardous', marker: '#7E0023' },
]

function getAqiVisual(category: AqiCategory | null | undefined) {
  return aqiVisuals[category?.code ?? 'unknown'] ?? aqiVisuals.unknown
}

function aqiStyle(category: AqiCategory | null | undefined) {
  const visual = getAqiVisual(category)
  return { '--aqi-foreground': visual.foreground, '--aqi-surface': visual.surface } as CSSProperties
}

function markerStrokeColor(city: DashboardCity) {
  return getAqiVisual(city.latest?.aqi?.category).foreground
}

function parseScreen(): Screen {
  const match = window.location.hash.match(/^#\/cities\/(\d+)/)
  if (match) return { name: 'city', cityId: Number(match[1]) }
  if (window.location.hash === '#/cities') return { name: 'cities' }
  if (window.location.hash === '#/source') return { name: 'source' }
  return { name: 'overview' }
}

function formatTime(value: string | null) {
  if (!value) return 'Unavailable'
  return new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false }).format(new Date(value)) + ' UTC'
}

function formatNumber(value: number | null | undefined) {
  return value === null || value === undefined ? 'N/A' : value.toLocaleString(undefined, { maximumFractionDigits: 1 })
}

function isAbortedRequest(reason: unknown) {
  return reason instanceof DOMException && reason.name === 'AbortError'
}

function markerColor(city: DashboardCity) {
  return city.latest?.aqi?.category?.color ?? markerFallback
}

function MapBounds({ cities }: { cities: DashboardCity[] }) {
  const map = useMap()
  useEffect(() => {
    const points = cities.filter((entry) => entry.latest).map(({ city }) => [city.latitude, city.longitude] as [number, number])
    if (points.length) map.fitBounds(points, { padding: [48, 48], maxZoom: 5 })
  }, [cities, map])
  return null
}

function NavigationIcon({ name }: { name: 'overview' | 'cities' | 'source' }) {
  if (name === 'overview') return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13.5 12 5l8 8.5M6.5 11v8h11v-8M10 19v-5h4v5" /></svg>
  if (name === 'cities') return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="8" r="3" /><circle cx="16" cy="8" r="3" /><path d="M2.5 19c.6-3.1 2.4-4.7 5.5-4.7s4.9 1.6 5.5 4.7M10.5 19c.5-2.5 2-3.8 4.7-3.8 2.8 0 4.6 1.3 5.3 3.8" /></svg>
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4.5h9l3 3V19.5H6zM15 4.5v4h3M9 12h6M9 15.5h6" /></svg>
}

function Sidebar({ active, onOverview, onCities, onSource }: { active: Screen['name']; onOverview: () => void; onCities: () => void; onSource: () => void }) {
  return <aside className="sidebar">
    <button className="brand" type="button" onClick={onOverview} aria-label="Go to monitoring overview"><span className="brand-logo-frame" aria-hidden="true"><img src="/13.png" alt="" /></span></button>
    <nav aria-label="Primary navigation">
      <button className={active === 'overview' ? 'nav-item active' : 'nav-item'} type="button" onClick={onOverview} aria-current={active === 'overview' ? 'page' : undefined}><NavigationIcon name="overview" /><span className="nav-label">Overview</span></button>
      <button className={active === 'city' || active === 'cities' ? 'nav-item active' : 'nav-item'} type="button" onClick={onCities} aria-current={active === 'city' || active === 'cities' ? 'page' : undefined}><NavigationIcon name="cities" /><span className="nav-label">Cities</span></button>
      <button className={active === 'source' ? 'nav-item active' : 'nav-item'} type="button" onClick={onSource} aria-current={active === 'source' ? 'page' : undefined}><NavigationIcon name="source" /><span className="nav-label">Data source</span></button>
    </nav>
    <p className="sidebar-foot">Environmental intelligence<br />from provider snapshots</p>
  </aside>
}

function PageMessage({ eyebrow, title, children }: { eyebrow: string; title: string; children: ReactNode }) {
  return <main className="content-message" role="status">
    <p className="eyebrow">{eyebrow}</p>
    <h1>{title}</h1>
    {children}
  </main>
}

function OverviewLoadingState() {
  return <main className="overview-shell loading-shell" aria-busy="true">
    <header className="page-header"><div><span className="skeleton skeleton-label" /><span className="skeleton skeleton-title" /></div></header>
    <div className="context-line"><span className="skeleton skeleton-line skeleton-line-wide" /></div>
    <section className="signal-grid" aria-hidden="true">{Array.from({ length: 4 }, (_, index) => <article className="signal-card" key={index}><span className="skeleton skeleton-label" /><span className="skeleton skeleton-value" /><span className="skeleton skeleton-line" /></article>)}</section>
    <section className="map-section skeleton-map-section" aria-hidden="true"><div className="map-section-header"><div><span className="skeleton skeleton-label" /><span className="skeleton skeleton-heading" /></div></div><div className="map-workspace skeleton-map"><div className="city-panel"><span className="skeleton skeleton-label" /><span className="skeleton skeleton-title skeleton-title-small" /><span className="skeleton skeleton-value" /><span className="skeleton skeleton-line" /><span className="skeleton skeleton-line" /></div></div><div className="skeleton-legend"><span className="skeleton skeleton-label" /><span className="skeleton skeleton-line" /></div></section>
    <section className="priority-section" aria-hidden="true"><div className="section-heading"><div><span className="skeleton skeleton-label" /><span className="skeleton skeleton-heading" /></div></div><div className="priority-list">{Array.from({ length: 4 }, (_, index) => <div className="priority-row priority-row-skeleton" key={index}><span className="skeleton skeleton-line" /><span className="skeleton skeleton-line" /><span className="skeleton skeleton-line" /></div>)}</div></section>
    <span className="sr-only">Loading current environmental evidence.</span>
  </main>
}

function CityLoadingState() {
  return <main className="city-shell loading-shell" aria-busy="true">
    <div className="breadcrumb-row"><span className="skeleton skeleton-breadcrumb" /></div>
    <header className="city-header"><span className="skeleton skeleton-label" /><span className="skeleton skeleton-title" /></header>
    <section className="city-top" aria-hidden="true"><div className="aqi-hero"><span className="skeleton skeleton-label" /><span className="skeleton skeleton-aqi" /><span className="skeleton skeleton-heading" /></div><div className="observations"><span className="skeleton skeleton-heading" />{Array.from({ length: 4 }, (_, index) => <span className="skeleton skeleton-line" key={index} />)}</div></section>
    <section className="trends-panel" aria-hidden="true"><span className="skeleton skeleton-heading" /><div className="trend-grid">{Array.from({ length: 4 }, (_, index) => <span className="skeleton skeleton-line" key={index} />)}</div></section>
    <span className="sr-only">Loading city intelligence.</span>
  </main>
}

function SelectedCity({ entry, onOpen }: { entry: DashboardCity; onOpen: () => void }) {
  const latest = entry.latest
  if (!latest) return <div className="city-panel muted-panel">No current provider snapshot is available for {entry.city.name}.</div>
  const aqi = latest.aqi
  const pm25 = latest.pollutants.pm2_5
  return <aside className="city-panel">
    <p className="eyebrow">Selected city</p>
    <h2>{entry.city.name}</h2>
    <div className="aqi-lockup" style={aqiStyle(aqi?.category)}>
      <span className="aqi-value">{formatNumber(aqi?.value)}</span>
      <div><p className="eyebrow">Estimated AQI</p><strong>{aqi?.category?.label ?? 'Unavailable'}</strong></div>
    </div>
    <dl className="evidence-list">
      <div><dt>Primary pollutant</dt><dd>{aqi?.primary_pollutant?.replace('_', '.').toUpperCase() ?? 'N/A'}</dd></div>
      <div><dt>PM2.5</dt><dd>{formatNumber(pm25?.value)} {pm25?.unit ?? ''}</dd></div>
      <div><dt>Observed</dt><dd>{formatTime(latest.observed_at)}</dd></div>
      <div><dt>Source</dt><dd>{latest.source}</dd></div>
    </dl>
    <button className="text-action" type="button" onClick={onOpen}>Open city intelligence <span aria-hidden="true">→</span></button>
  </aside>
}

function Overview({ data, onOpenCity }: { data: Dashboard; onOpenCity: (cityId: number) => void }) {
  const withData = useMemo(() => data.cities.filter((entry) => entry.latest), [data])
  const priority = useMemo(() => [...withData].sort((a, b) => (b.latest?.aqi?.value ?? -1) - (a.latest?.aqi?.value ?? -1)), [withData])
  const [selectedId, setSelectedId] = useState<number | null>(priority[0]?.city.id ?? null)
  const selected = data.cities.find((entry) => entry.city.id === selectedId) ?? priority[0]

  useEffect(() => { if (!selectedId && priority[0]) setSelectedId(priority[0].city.id) }, [priority, selectedId])

  return <main className="overview-shell">
    <header className="page-header"><div><p className="eyebrow">Regional environmental intelligence</p><h1>Air quality overview</h1></div></header>
    <p className="context-line"><strong>{data.summary.cities_with_current_data} cities with current data</strong><span>•</span>Latest provider-valid hour: {formatTime(data.summary.last_observed_at)}<span>•</span>Open-Meteo / CAMS</p>
    {withData.length === 0 ? <EmptyState /> : <>
      <section className="signal-grid" aria-label="Network snapshot">
        <article className="signal-card network"><span>Network coverage</span><strong>{data.summary.cities_with_current_data}<small> / {data.summary.cities_monitored} cities</small></strong><p>Provider-valid snapshots available now</p></article>
        <article className="signal-card"><span>Average PM2.5</span><strong>{formatNumber(data.summary.average_pm2_5.value)}<small> {data.summary.average_pm2_5.unit}</small></strong><p>Across monitored cities</p></article>
        <article className="signal-card"><span>Average PM10</span><strong>{formatNumber(data.summary.average_pm10.value)}<small> {data.summary.average_pm10.unit}</small></strong><p>Across monitored cities</p></article>
        <article className="signal-card status-card" style={aqiStyle(data.leaders.highest_aqi?.aqi.category)}><span>Highest estimated AQI</span><strong>{formatNumber(data.leaders.highest_aqi?.aqi.value)}</strong><p className="status-context"><span>{data.leaders.highest_aqi?.aqi.category?.label ?? 'Unavailable'}</span><span>{data.leaders.highest_aqi?.city_name ?? 'No city data available'}</span></p></article>
      </section>
      <section className="map-section" aria-labelledby="map-section-title">
        <div className="map-section-header"><div><p className="eyebrow">Geographic view</p><h2 id="map-section-title">Current conditions by city</h2></div><p>Select a marker to review its latest provider snapshot.</p></div>
        <div className="map-workspace" aria-label="Current air quality map">
          <MapContainer className="map" center={[5, 120]} zoom={4} scrollWheelZoom>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <MapBounds cities={withData} />
            {withData.map((entry) => <CircleMarker key={entry.city.id} center={[entry.city.latitude, entry.city.longitude]} radius={18} pathOptions={{ color: selected?.city.id === entry.city.id ? '#18181b' : markerStrokeColor(entry), weight: selected?.city.id === entry.city.id ? 3 : 2, fillColor: markerColor(entry), fillOpacity: 1 }} eventHandlers={{ click: () => setSelectedId(entry.city.id) }}>
              <Tooltip permanent direction="right" offset={[14, 0]}>{formatNumber(entry.latest?.aqi?.value)} <strong>{entry.city.name}</strong></Tooltip>
            </CircleMarker>)}
          </MapContainer>
          {selected && <SelectedCity entry={selected} onOpen={() => onOpenCity(selected.city.id)} />}
        </div>
        <div className="map-legend" aria-label="Estimated AQI category legend"><div><strong>Estimated AQI scale</strong><span>Provider-model snapshot</span></div><ul>{aqiLegendItems.map((item) => <li key={item.code}><i style={{ backgroundColor: item.marker, borderColor: aqiVisuals[item.code].foreground }} aria-hidden="true" /><span>{item.label}</span></li>)}</ul></div>
      </section>
      <section className="priority-section"><div className="section-heading"><div><p className="eyebrow">Where to investigate</p><h2>Priority locations</h2></div><p>Ranked by current estimated AQI</p></div>
        <div className="priority-list"><div className="priority-table-head" aria-hidden="true"><span>Rank</span><span>City</span><span>AQI</span><span>Status</span><span>Observed</span><span /></div>{priority.map((entry, index) => <button className="priority-row" type="button" key={entry.city.id} onClick={() => onOpenCity(entry.city.id)} aria-label={`Open intelligence for ${entry.city.name}`}><span className="rank">{String(index + 1).padStart(2, '0')}</span><strong>{entry.city.name}</strong><span className="aqi-small" style={aqiStyle(entry.latest?.aqi?.category)}>{formatNumber(entry.latest?.aqi?.value)}</span><span>{entry.latest?.aqi?.category?.label ?? 'No AQI'}</span><span>{formatTime(entry.latest?.observed_at ?? null)}</span><span aria-hidden="true">→</span></button>)}</div>
      </section>
      <p className="disclosure">ⓘ Estimated AQI reflects a provider model snapshot. It is not an official EPA AQI.</p>
    </>}
  </main>
}

function TrendRow({ label, trend }: { label: string; trend?: PollutantTrend }) {
  if (!trend || trend.status !== 'ok') return <div className="trend-row"><strong>{label}</strong><span>Insufficient data</span><small>{trend ? `${trend.current_observation_count} / ${trend.baseline_observation_count} observations` : 'No observations'}</small></div>
  const direction = trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→'
  const percentChange = trend.percent_change === null ? null : Math.abs(trend.percent_change)
  return <div className="trend-row"><strong>{label}</strong><span className={`trend ${trend.direction}`}>{direction} {trend.direction ?? 'flat'} {formatNumber(percentChange)}{percentChange === null ? '' : '%'}</span><small>24h vs prior 24h · {trend.current_observation_count} observations</small></div>
}

function CityIntelligence({ cityId, onOverview }: { cityId: number; onOverview: () => void }) {
  const [latest, setLatest] = useState<LatestObservation | null>(null)
  const [trends, setTrends] = useState<Record<string, PollutantTrend>>({})
  const [error, setError] = useState<Error | null>(null)
  const [requestVersion, setRequestVersion] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLatest(null)
    setTrends({})
    setError(null)
    Promise.all([api.latest(cityId, controller.signal), api.trends(cityId, controller.signal)])
      .then(([observation, result]) => { setLatest(observation); setTrends(result.trends) })
      .catch((reason: unknown) => { if (!isAbortedRequest(reason)) setError(reason instanceof Error ? reason : new Error('The city data request could not be completed.')) })
    return () => controller.abort()
  }, [cityId, requestVersion])
  if (error instanceof ApiRequestError && error.status === 404) return <PageMessage eyebrow="No current provider snapshot" title="City intelligence is not available yet."><p>AeroC does not infer environmental status when the API has no current snapshot for this city.</p><div className="message-actions"><button className="text-action" type="button" onClick={onOverview}>Back to overview</button></div></PageMessage>
  if (error) return <PageMessage eyebrow="Connection unavailable" title="City data could not be loaded."><p>{error.message}. Check the API connection and try again.</p><div className="message-actions"><button className="primary-action" type="button" onClick={() => setRequestVersion((value) => value + 1)}>Try again</button><button className="text-action" type="button" onClick={onOverview}>Back to overview</button></div></PageMessage>
  if (!latest) return <CityLoadingState />
  const pollutantEntries = Object.entries(latest.pollutants)
  return <main className="city-shell"><div className="breadcrumb-row"><button className="breadcrumb" type="button" onClick={onOverview}>Monitoring overview</button><span className="slash" aria-hidden="true">/</span><span aria-current="page">{latest.city.name}</span></div>
    <header className="city-header"><div><p className="eyebrow">{latest.city.code} · {latest.city.country}</p><h1>{latest.city.name}</h1><p>Latest provider-valid hour: {formatTime(latest.observed_at)}</p></div></header>
    <section className="city-top"><div className="aqi-hero" style={aqiStyle(latest.aqi.category)}><p className="eyebrow">Estimated AQI</p><div>{formatNumber(latest.aqi.value)}</div><strong>{latest.aqi.category?.label ?? 'Unavailable'}</strong><p>Primary pollutant: {latest.aqi.primary_pollutant ? latest.aqi.primary_pollutant.replace('_', '.').toUpperCase() : 'N/A'}</p><small>ⓘ Model snapshot · Not an official EPA AQI</small></div>
      <div className="observations"><div className="section-heading"><div><p className="eyebrow">Evidence</p><h2>Current observations</h2></div><p>Observed {formatTime(latest.observed_at)}<br />Collected {formatTime(latest.collected_at)}</p></div>{pollutantEntries.map(([name, value]) => <div className="observation-row" key={name}><span>{name.replace('_', '.').toUpperCase()}</span><strong>{formatNumber(value.value)} <small>{value.unit}</small></strong></div>)}<p className="source-note">Source: {latest.source}</p></div>
    </section>
    <section className="trends-panel"><div className="section-heading"><div><p className="eyebrow">Server-calculated comparison</p><h2>What changed</h2></div><p>Current 24h vs prior 24h</p></div><div className="trend-grid"><TrendRow label="PM2.5" trend={trends.pm2_5} /><TrendRow label="PM10" trend={trends.pm10} /><TrendRow label="Ozone" trend={trends.ozone} /><TrendRow label="Nitrogen dioxide" trend={trends.nitrogen_dioxide} /></div></section>
    <p className="disclosure">ⓘ Values are provider model snapshots preserved by AeroC at collection time. They are estimates, not regulatory measurements.</p>
  </main>
}

function CitiesPage({ data, onOpenCity }: { data: Dashboard; onOpenCity: (cityId: number) => void }) {
  const [sort, setSort] = useState<{ key: 'country' | 'aqi'; direction: 'ascending' | 'descending' }>({ key: 'country', direction: 'ascending' })
  const cities = useMemo(() => [...data.cities].sort((a, b) => {
    if (sort.key === 'country') {
      const countryComparison = a.city.country.localeCompare(b.city.country)
      const result = countryComparison || a.city.name.localeCompare(b.city.name)
      return sort.direction === 'ascending' ? result : -result
    }
    const aqiA = a.latest?.aqi?.value
    const aqiB = b.latest?.aqi?.value
    if (aqiA === null || aqiA === undefined) return aqiB === null || aqiB === undefined ? a.city.name.localeCompare(b.city.name) : 1
    if (aqiB === null || aqiB === undefined) return -1
    const result = aqiA - aqiB || a.city.name.localeCompare(b.city.name)
    return sort.direction === 'ascending' ? result : -result
  }), [data.cities, sort])
  const changeSort = (key: 'country' | 'aqi') => setSort((current) => current.key === key ? { key, direction: current.direction === 'ascending' ? 'descending' : 'ascending' } : { key, direction: key === 'aqi' ? 'descending' : 'ascending' })
  const sortArrow = (key: 'country' | 'aqi') => sort.key === key ? (sort.direction === 'ascending' ? '↑' : '↓') : '↕'
  return <main className="directory-page"><header className="directory-header"><p className="eyebrow">Monitoring network</p><h1>Cities</h1><p className="page-intro">Each location represents AeroC's first captured provider snapshot for its latest valid hour.</p></header>
    <div className="city-directory"><div className="directory-table-head"><span>City</span><button type="button" className={sort.key === 'country' ? 'sort-button active' : 'sort-button'} onClick={() => changeSort('country')} aria-pressed={sort.key === 'country'}>Country <span aria-hidden="true">{sortArrow('country')}</span></button><button type="button" className={sort.key === 'aqi' ? 'sort-button active' : 'sort-button'} onClick={() => changeSort('aqi')} aria-pressed={sort.key === 'aqi'}>Estimated AQI <span aria-hidden="true">{sortArrow('aqi')}</span></button><span /></div>{cities.map((entry) => <button className="directory-row" key={entry.city.id} type="button" onClick={() => onOpenCity(entry.city.id)} aria-label={`Open intelligence for ${entry.city.name}`}><div><strong>{entry.city.name}</strong><span><span className="mobile-country">{entry.city.country} · </span>{entry.city.code}</span></div><span className="directory-country">{entry.city.country}</span><div className="directory-aqi" style={aqiStyle(entry.latest?.aqi?.category)}><span>{formatNumber(entry.latest?.aqi?.value)}</span><small>{entry.latest?.aqi?.category?.label ?? 'No estimated AQI'}</small></div><span aria-hidden="true">→</span></button>)}</div>
  </main>
}

function SourcePage() {
  return <main className="directory-page source-page"><header className="directory-header"><p className="eyebrow">Data provenance</p><h1>Data source</h1><p className="page-intro">AeroC interprets provider data without presenting it as regulatory measurement.</p></header>
    <section><h2>Open-Meteo</h2><p>Current air-quality snapshots are collected from Open-Meteo and represented in AeroC as the first successfully captured snapshot for each city, provider-valid hour, and source.</p></section>
    <section><h2>How to read this product</h2><dl><div><dt>Estimated AQI</dt><dd>An EPA-style PM2.5/PM10 estimate, not an official EPA AQI.</dd></div><div><dt>Observed time</dt><dd>The provider-valid hour for the environmental model snapshot.</dd></div><div><dt>Collected time</dt><dd>When AeroC first stored that snapshot.</dd></div></dl></section>
  </main>
}

function EmptyState() { return <section className="content-message"><p className="eyebrow">No current provider snapshots</p><h1>The monitoring map will appear after collection.</h1><p>AeroC will show locations only once the API has current city data. No environmental status is inferred while evidence is unavailable.</p></section> }

function App() {
  const [screen, setScreen] = useState<Screen>(parseScreen)
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [requestVersion, setRequestVersion] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setDashboard(null)
    setError(null)
    api.dashboard(controller.signal)
      .then(setDashboard)
      .catch((reason: unknown) => { if (!isAbortedRequest(reason)) setError(reason instanceof Error ? reason : new Error('The dashboard request could not be completed.')) })
    return () => controller.abort()
  }, [requestVersion])
  useEffect(() => { const sync = () => setScreen(parseScreen()); window.addEventListener('hashchange', sync); return () => window.removeEventListener('hashchange', sync) }, [])
  useEffect(() => {
    const pageTitles: Record<Screen['name'], string> = { overview: 'Monitoring overview', city: 'City intelligence', cities: 'Cities', source: 'Data source' }
    document.title = `AeroC | ${pageTitles[screen.name]}`
  }, [screen.name])
  const openOverview = () => { window.location.hash = '#/' }
  const openCity = (cityId: number) => { window.location.hash = `#/cities/${cityId}` }
  const openCities = () => { window.location.hash = '#/cities' }
  const openSource = () => { window.location.hash = '#/source' }
  return <div className="app-shell"><Sidebar active={screen.name} onOverview={openOverview} onCities={openCities} onSource={openSource} />{error ? <PageMessage eyebrow="Connection unavailable" title="AeroC data could not be loaded."><p>{error.message}. Confirm the API is running and set <code>VITE_API_URL</code> if it is not at the local default.</p><div className="message-actions"><button className="primary-action" type="button" onClick={() => setRequestVersion((value) => value + 1)}>Try again</button></div></PageMessage> : !dashboard ? <OverviewLoadingState /> : screen.name === 'city' ? <CityIntelligence cityId={screen.cityId} onOverview={openOverview} /> : screen.name === 'cities' ? <CitiesPage data={dashboard} onOpenCity={openCity} /> : screen.name === 'source' ? <SourcePage /> : <Overview data={dashboard} onOpenCity={openCity} />}</div>
}

export default App
