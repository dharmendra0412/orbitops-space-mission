import { useEffect, useRef, useState } from 'react'
import {
  Activity, ArrowUpRight, Atom, BatteryCharging, BookOpen, Check, ClipboardList,
  ChevronDown, CircleHelp, Compass, Database, Globe2, Layers3,
  Menu, Radio, Rocket, Satellite, Settings2, ShieldCheck,
  SlidersHorizontal, Target, Telescope, Users, X, ExternalLink
} from 'lucide-react'

import { instruments, orbitOptions } from './domain/catalog'
import { missionResources } from './data/sources'
import { extractPdsFileManifest, extractPdsMembers, extractPdsProducts, mergePdsMembers } from './data/pds'
import { lolaPixelToLatLon } from './data/lolaProjection'
import { apiUrl } from './data/api'
import { MissionBrief } from './components/MissionBrief'
import { LaltLabelInspector } from './components/LaltLabelInspector'

function Metric({ label, value, unit, icon: Icon, tone = 'blue', detail }: {
  label: string; value: string; unit?: string; icon: typeof Activity; tone?: string; detail: string
}) {
  return <div className="metric-card">
    <div className="metric-top"><span>{label}</span><span className={`metric-icon ${tone}`}><Icon size={16} /></span></div>
    <div className="metric-value">{value}<small>{unit}</small></div>
    <div className="metric-detail">{detail}</div>
  </div>
}

type PdsSearchResponse = {
  source: string
  source_url: string
  api_documentation: string
  retrieved_at: string
  query: { keywords: string; limit: number }
  response: unknown
}

type PdsMembersResponse = {
  source: string
  source_url: string
  api_documentation: string
  retrieved_at: string
  identifier: string
  depth: number
  next_search_after?: string | null
  response: unknown
}

type PdsLookupResponse = {
  source: string
  source_url: string
  api_documentation: string
  retrieved_at: string
  identifier: string
  response: unknown
}

type Pds3LabelResponse = {
  source: string
  source_url: string
  retrieved_at: string
  label_format: string
  product_file: string
  metadata: Record<string, string>
  note: string
}

type LolaPixelResponse = {
  source: string
  source_url: string
  label_source_url: string
  retrieved_at: string
  product_file: string
  line_index: number
  sample_index: number
  byte_range_inclusive: { start: number; end: number }
  raw_dn: number
  height_m: number
  planetary_radius_m: number
  planetocentric_latitude_degrees: number
  east_longitude_degrees: number
  units: { raw_dn: string; height: string; planetary_radius: string }
  coordinate_reference: string
  validation_scope: string
}

type LolaProfileResponse = {
  source: string
  source_url: string
  label_source_url: string
  retrieved_at: string
  product_file: string
  line_index: number
  start_sample_index: number
  sample_count: number
  sample_spacing_m: number
  profile_span_m: number
  byte_range_inclusive: { start: number; end: number }
  coordinate_reference: string
  points: Array<{
    sample_index: number
    raw_dn: number
    height_m: number
    planetary_radius_m: number
    planetocentric_latitude_degrees: number
    east_longitude_degrees: number
  }>
  validation_scope: string
}



async function readApiResponse<T>(response: Response, operation: string): Promise<T> {
  const body = await response.text()
  let payload: unknown = null

  if (body.trim()) {
    try {
      payload = JSON.parse(body)
    } catch {
      const format = response.headers.get('content-type') ?? 'unknown content type'
      throw new Error(
        response.ok
          ? operation + ' returned an invalid response (' + format + ').'
          : operation + ' failed (HTTP ' + response.status + '); the server returned a non-JSON response.'
      )
    }
  } else if (response.ok) {
    throw new Error(operation + ' returned an empty response.')
  }

  if (!response.ok) {
    const detail = payload && typeof payload === 'object' && 'detail' in payload
      ? (payload as { detail?: unknown }).detail
      : undefined
    const message = typeof detail === 'string' && detail.trim()
      ? detail
      : operation + ' failed (HTTP ' + response.status + ').'
    throw new Error(message)
  }

  return payload as T
}

function App() {
  const [activeNav, setActiveNav] = useState('Research overview')
  const [selected, setSelected] = useState<string[]>([])
  const [orbit, setOrbit] = useState('low')
  const [showAll, setShowAll] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const mobileMenuTriggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!mobileMenu) return
    document.getElementById('mobile-menu-close')?.focus()
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileMenu(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      window.removeEventListener('keydown', closeOnEscape)
      mobileMenuTriggerRef.current?.focus()
    }
  }, [mobileMenu])
  const [pdsKeywords, setPdsKeywords] = useState('LOLA')
  const [pdsSearchResponse, setPdsSearchResponse] = useState<PdsSearchResponse | null>(null)
  const [pdsSearchError, setPdsSearchError] = useState('')
  const [pdsSearchLoading, setPdsSearchLoading] = useState(false)
  const pdsSearchControllerRef = useRef<AbortController | null>(null)

  useEffect(() => () => pdsSearchControllerRef.current?.abort(), [])
  const [pdsIdentifier, setPdsIdentifier] = useState('')
  const [pdsLookupResponse, setPdsLookupResponse] = useState<PdsLookupResponse | null>(null)
  const [pdsLookupError, setPdsLookupError] = useState('')
  const [pdsLookupLoading, setPdsLookupLoading] = useState(false)
  const [pdsMembersResponse, setPdsMembersResponse] = useState<PdsMembersResponse | null>(null)
  const [pdsMembersError, setPdsMembersError] = useState('')
  const [pdsMembersLoading, setPdsMembersLoading] = useState(false)
  const [pdsMembersRecords, setPdsMembersRecords] = useState<import('./data/pds').PdsMemberRecord[]>([])
  const [pdsMembersStructured, setPdsMembersStructured] = useState(true)
  const [pdsLabelResponse, setPdsLabelResponse] = useState<Pds3LabelResponse | null>(null)
  const [pdsLabelError, setPdsLabelError] = useState('')
  const [pdsLabelLoading, setPdsLabelLoading] = useState(false)
  const [lolaLineIndex, setLolaLineIndex] = useState('3791')
  const [lolaSampleIndex, setLolaSampleIndex] = useState('3791')
  const [lolaPixelResponse, setLolaPixelResponse] = useState<LolaPixelResponse | null>(null)
  const [lolaPixelError, setLolaPixelError] = useState('')
  const [lolaPixelLoading, setLolaPixelLoading] = useState(false)
  const [lolaProfileCount, setLolaProfileCount] = useState('128')
  const [lolaProfileResponse, setLolaProfileResponse] = useState<LolaProfileResponse | null>(null)
  const [lolaProfileError, setLolaProfileError] = useState('')
  const [lolaProfileLoading, setLolaProfileLoading] = useState(false)

  useEffect(() => {
    const sections = [
      { id: 'research-overview', label: 'Research overview' },
      { id: 'designer', label: 'Research categories' },
      { id: 'input-readiness', label: 'Input readiness' },
      { id: 'mission-brief', label: 'Mission brief' },
      { id: 'data-sources', label: 'NASA data sources' },
    ]
    let frame = 0
    const updateActiveSection = () => {
      if (frame) return
      frame = window.requestAnimationFrame(() => {
        frame = 0
        let current = sections[0].label
        for (const section of sections) {
          const element = document.getElementById(section.id)
          if (element && element.getBoundingClientRect().top <= 180) current = section.label
        }
        setActiveNav(current)
      })
    }
    updateActiveSection()
    window.addEventListener('scroll', updateActiveSection, { passive: true })
    window.addEventListener('resize', updateActiveSection)
    return () => {
      window.removeEventListener('scroll', updateActiveSection)
      window.removeEventListener('resize', updateActiveSection)
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [])
  const toggleInstrument = (id: string) => {
    setSelected(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id])
  }


  const pdsProducts = pdsSearchResponse ? extractPdsProducts(pdsSearchResponse.response) : null
  const pdsFiles = pdsLookupResponse ? extractPdsFileManifest(pdsLookupResponse.response) : []
  const profilePoints = lolaProfileResponse?.points ?? []
  const profileHeights = profilePoints.map((point) => point.height_m)
  const profileMinHeight = profileHeights.length ? Math.min(...profileHeights) : 0
  const profileMaxHeight = profileHeights.length ? Math.max(...profileHeights) : 0
  const profileHeightRange = Math.max(profileMaxHeight - profileMinHeight, 1e-9)
  const profilePolyline = profilePoints.map((point, index) => {
    const x = 12 + (index / Math.max(profilePoints.length - 1, 1)) * 776
    const y = 190 - ((point.height_m - profileMinHeight) / profileHeightRange) * 160
    return x.toFixed(2) + ',' + y.toFixed(2)
  }).join(' ')
  let lolaPixelLocation: ReturnType<typeof lolaPixelToLatLon> | null = null
  let lolaPixelLocationError = ''
  if (pdsLabelResponse) {
    try {
      lolaPixelLocation = lolaPixelToLatLon(
        pdsLabelResponse.metadata,
        lolaLineIndex.trim() ? Number(lolaLineIndex) : Number.NaN,
        lolaSampleIndex.trim() ? Number(lolaSampleIndex) : Number.NaN,
      )
    } catch (error) {
      lolaPixelLocationError = error instanceof Error ? error.message : 'Unable to calculate the source-grid coordinate.'
    }
  }

  const searchPds = async () => {
    const keywords = pdsKeywords.trim()
    if (keywords.length < 2) {
      setPdsSearchError('Enter at least two characters to search the NASA PDS archive.')
      setPdsSearchResponse(null)
      return
    }

    pdsSearchControllerRef.current?.abort()
    const controller = new AbortController()
    pdsSearchControllerRef.current = controller
    setPdsSearchLoading(true)
    setPdsSearchError('')
    setPdsSearchResponse(null)
    try {
      const params = new URLSearchParams({ keywords, limit: '10' })
      const response = await fetch(apiUrl('/api/v1/pds/search?' + params.toString()), { signal: controller.signal })
      const payload = await readApiResponse<PdsSearchResponse>(response, 'PDS search')
      if (pdsSearchControllerRef.current === controller) setPdsSearchResponse(payload)
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') return
      if (pdsSearchControllerRef.current === controller) {
        setPdsSearchError(error instanceof Error ? error.message : 'Unable to retrieve NASA PDS results.')
      }
    } finally {
      if (pdsSearchControllerRef.current === controller) {
        pdsSearchControllerRef.current = null
        setPdsSearchLoading(false)
      }
    }
  }


  const resolvePdsProduct = async (identifierValue?: string) => {
    const identifier = (identifierValue ?? pdsIdentifier).trim()
    if (identifier.length < 5) {
      setPdsLookupError('Enter a PDS product LID or LIDVID.')
      setPdsLookupResponse(null)
      return
    }

    setPdsLookupLoading(true)
    setPdsLookupError('')
    setPdsLookupResponse(null)
    try {
      const response = await fetch(apiUrl('/api/v1/pds/products/' + encodeURIComponent(identifier)))
      const payload = await readApiResponse<PdsLookupResponse>(response, 'PDS product lookup')
      setPdsIdentifier(identifier)
      setPdsLookupResponse(payload)
    } catch (error) {
      setPdsLookupError(error instanceof Error ? error.message : 'Unable to resolve the PDS product identifier.')
    } finally {
      setPdsLookupLoading(false)
    }
  }


  const pdsMembers = pdsMembersResponse ? (pdsMembersStructured ? pdsMembersRecords : null) : null

  const browsePdsMembers = async (identifierValue?: string, depth = 1, searchAfter?: string) => {
    const identifier = (identifierValue ?? pdsIdentifier).trim()
    if (identifier.length < 5) {
      setPdsMembersError('Resolve or enter a PDS collection/bundle identifier first.')
      setPdsMembersResponse(null)
      return
    }

    setPdsMembersLoading(true)
    setPdsMembersError('')
    if (!searchAfter) {
      setPdsMembersResponse(null)
      setPdsMembersRecords([])
      setPdsMembersStructured(true)
    }
    try {
      const params = new URLSearchParams({ depth: String(depth), limit: '100' })
      if (searchAfter) params.set('search_after', searchAfter)
      const response = await fetch(apiUrl('/api/v1/pds/products/' + encodeURIComponent(identifier) + '/members?' + params.toString()))
      const payload = await readApiResponse<PdsMembersResponse>(response, 'PDS hierarchy request')
      const parsedMembers = extractPdsMembers(payload.response)
      setPdsMembersStructured(parsedMembers !== null)
      if (parsedMembers) {
        setPdsMembersRecords((current) => searchAfter
          ? mergePdsMembers(current, parsedMembers)
          : mergePdsMembers([], parsedMembers))
      } else if (!searchAfter) {
        setPdsMembersRecords([])
      }
      setPdsIdentifier(identifier)
      setPdsMembersResponse(payload)
    } catch (error) {
      setPdsMembersError(error instanceof Error ? error.message : 'Unable to retrieve PDS child products.')
    } finally {
      setPdsMembersLoading(false)
    }
  }

  const fetchLolaSampleLabel = async () => {
    setPdsLabelLoading(true)
    setPdsLabelError('')
    setPdsLabelResponse(null)
    setLolaPixelResponse(null)
    setLolaPixelError('')
    setLolaProfileResponse(null)
    setLolaProfileError('')
    try {
      const response = await fetch(apiUrl('/api/v1/pds3/lola/gdr/ldem-85s-40m/label'))
      const payload = await readApiResponse<Pds3LabelResponse>(response, 'LOLA label request')
      setPdsLabelResponse(payload)
    } catch (error) {
      setPdsLabelError(error instanceof Error ? error.message : 'Unable to retrieve the original LOLA label.')
    } finally {
      setPdsLabelLoading(false)
    }
  }

  const fetchLolaPixel = async () => {
    if (!lolaPixelLocation || !pdsLabelResponse) {
      setLolaPixelError(lolaPixelLocationError || 'Enter valid line and sample indices first.')
      setLolaPixelResponse(null)
      return
    }
    setLolaPixelLoading(true)
    setLolaPixelError('')
    setLolaPixelResponse(null)
    try {
      const params = new URLSearchParams({ line_index: lolaLineIndex, sample_index: lolaSampleIndex })
      const response = await fetch(apiUrl('/api/v1/pds3/lola/gdr/ldem-85s-40m/pixel?' + params.toString()))
      const payload = await readApiResponse<LolaPixelResponse>(response, 'LOLA source pixel request')
      setLolaPixelResponse(payload)
    } catch (error) {
      setLolaPixelError(error instanceof Error ? error.message : 'Unable to retrieve this LOLA source pixel.')
    } finally {
      setLolaPixelLoading(false)
    }
  }

  const fetchLolaProfile = async () => {
    const line = Number(lolaLineIndex)
    const startSample = Number(lolaSampleIndex)
    const count = Number(lolaProfileCount)
    if (!pdsLabelResponse || !lolaPixelLocation) {
      setLolaProfileError(lolaPixelLocationError || 'Enter valid line and starting sample indices first.')
      setLolaProfileResponse(null)
      return
    }
    if (!Number.isInteger(count) || count < 1 || count > 512) {
      setLolaProfileError('Choose between 1 and 512 source samples for one row profile.')
      setLolaProfileResponse(null)
      return
    }
    if (startSample + count > Number(pdsLabelResponse.metadata.LINE_SAMPLES)) {
      setLolaProfileError('The requested profile would extend beyond the source image row.')
      setLolaProfileResponse(null)
      return
    }
    setLolaProfileLoading(true)
    setLolaProfileError('')
    setLolaProfileResponse(null)
    try {
      const params = new URLSearchParams({
        line_index: String(line),
        start_sample_index: String(startSample),
        sample_count: String(count),
      })
      const response = await fetch(apiUrl('/api/v1/pds3/lola/gdr/ldem-85s-40m/profile?' + params.toString()))
      const payload = await readApiResponse<LolaProfileResponse>(response, 'LOLA source profile request')
      setLolaProfileResponse(payload)
    } catch (error) {
      setLolaProfileError(error instanceof Error ? error.message : 'Unable to retrieve the LOLA source profile.')
    } finally {
      setLolaProfileLoading(false)
    }
  }

  const navItems = ['Research overview', 'Research categories', 'Input readiness', 'Mission brief', 'NASA data sources']
  const goTo = (item: string) => {
    setActiveNav(item)
    setMobileMenu(false)
    if (item === 'Research categories') document.getElementById('designer')?.scrollIntoView({ behavior: 'smooth' })
    else if (item === 'Research overview') window.scrollTo({ top: 0, behavior: 'smooth' })
    else if (item === 'Engineering guide') setShowAll(true)
    else if (item === 'Mission brief') document.getElementById('mission-brief')?.scrollIntoView({ behavior: 'smooth' })
    else if (item === 'NASA data sources') document.getElementById('data-sources')?.scrollIntoView({ behavior: 'smooth' })
    else document.getElementById('input-readiness')?.scrollIntoView({ behavior: 'smooth' })
  }

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><OrbitMark /></div><div><strong>ORBITOPS</strong><span>SPACE SCIENCE WORKSPACE</span></div><button id="mobile-menu-close" type="button" className="icon-button mobile-close" onClick={() => setMobileMenu(false)} aria-label="Close navigation menu"><X size={18}/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <div className="workspace-switch"><div className="workspace-avatar">RS</div><div><strong>Research workspace</strong><span>No mission configured</span></div><ChevronDown size={15}/></div>
      <div className="nav-label">RESEARCH</div>
      <nav id="research-navigation" className="side-nav" aria-label="Research sections">{navItems.map((item, index) => {
        const icons = [Globe2, SlidersHorizontal, Activity, Database, Layers3]
        const Icon = icons[index]
        return <button key={item} type="button" className={activeNav === item ? 'nav-item active' : 'nav-item'} onClick={() => goTo(item)} aria-current={activeNav === item ? 'page' : undefined}><Icon size={17}/><span>{item}</span>{index === 2 && <span className="nav-live">CHECKS</span>}</button>
      })}</nav>
      <div className="nav-label tools-label">TOOLS</div>
      <button type="button" className={`nav-item ${showAll ? 'active' : ''}`} onClick={() => setShowAll(!showAll)} aria-expanded={showAll}><Layers3 size={17}/><span>Engineering guide</span></button>
      <button type="button" className="nav-item" onClick={() => setShowAll(true)} aria-expanded={showAll}><ShieldCheck size={17}/><span>Model limitations</span></button>
      <div className="sidebar-bottom">
        <div className="help-card"><div className="help-icon"><CircleHelp size={17}/></div><strong>Need a hand?</strong><p>Explore the engineering guide to understand source and engineering trade-offs.</p><button onClick={() => setShowAll(!showAll)}>Open learning guide <ArrowUpRight size={13}/></button></div>
        <div className="profile"><div className="profile-avatar">R</div><div><strong>Research session</strong><span>Local browser only</span></div><Settings2 size={16}/></div>
      </div>
    </aside>

    {mobileMenu && <button type="button" className="scrim" onClick={() => setMobileMenu(false)} aria-label="Close navigation"/>}
    <main className="main-area" id="main-content" tabIndex={-1}>
      <header className="topbar">
        <a className="top-brand" href="#research-overview" aria-label="ORBITOPS lunar research control home">
          <span className="top-brand-mark"><OrbitMark /></span>
          <span className="top-brand-copy"><strong>ORBITOPS</strong><small>LUNAR RESEARCH CONTROL</small></span>
        </a>
        <nav className="top-nav" aria-label="Workspace navigation">
          {navItems.map((item) => <button key={item} type="button" className={activeNav === item ? 'top-nav-button active' : 'top-nav-button'} onClick={() => goTo(item)}>{item}</button>)}
          <button type="button" className={showAll ? 'top-nav-button active' : 'top-nav-button'} onClick={() => setShowAll(!showAll)} aria-expanded={showAll}>Engineering guide</button>
        </nav>
        <div className="top-actions">
          <span className="autosave"><span className="status-dot"/>SOURCE ACCESS · ON DEMAND</span>
          <span className="top-session-label">EDUCATIONAL WORKSPACE</span>
        </div>
      </header>

      <div className="content">
        <section className="page-heading" id="research-overview">
          <div><div className="eyebrow"><span className="eyebrow-line"/> ORBITOPS · SPACE SCIENCE RESEARCH</div><h1>Mission control<span className="heading-period">.</span></h1><p>Explore real lunar data, inspect source measurements, and prepare traceable mission concepts.</p></div>
          <button className="primary-button" onClick={() => goTo('Research categories')}><Rocket size={16}/> Explore research areas <ArrowUpRight size={15}/></button>
        </section>

        <div className="mission-overview-grid">
          <section className="mission-hero">
            <img
              className="hero-lunar-image"
              src="https://assets.science.nasa.gov/dynamicimage/assets/science/psd/photojournal/pia/pia13/pia13523/PIA13523.jpg?crop=1&h=1400&w=1600"
              alt="Lunar Reconnaissance Orbiter Wide Angle Camera mosaic of the Moon's south polar region"
              loading="eager"
              decoding="async"
            />
            <div className="hero-image-shade" aria-hidden="true"/>
            <div className="hero-copy">
              <div className="hero-kicker"><span className="hero-kicker-dot"/> FEATURED SCIENCE DATASET <span className="hero-id">PIA13523 · LROC WAC</span></div>
              <h2>Lunar <em>south pole</em></h2>
              <p>A 600 km-wide view of the lunar south-polar region captured by the Lunar Reconnaissance Orbiter Camera. Use this source-backed context to begin an investigation—then inspect the underlying archive records and product metadata.</p>
              <div className="hero-tags"><span><Target size={13}/> South-polar region</span><span><Compass size={13}/> LROC wide-angle mosaic</span><span><Database size={13}/> NASA Photojournal</span></div>
              <button className="hero-link" onClick={() => goTo('NASA data sources')}>Explore source records <ArrowUpRight size={15}/></button>
            </div>
            <a className="hero-image-credit" href="https://science.nasa.gov/photojournal/the-lunar-south-pole/" target="_blank" rel="noopener noreferrer">
              IMAGE PIA13523 · NASA / GSFC / ARIZONA STATE UNIVERSITY <ExternalLink size={11}/>
            </a>
            <div className="hero-footer"><span>MISSION <strong>LUNAR RECONNAISSANCE ORBITER</strong></span><span>INSTRUMENT <strong>WIDE ANGLE CAMERA</strong></span><span>WORKSPACE <strong>RESEARCH ONLY</strong></span></div>
          </section>

          <aside className="mission-architect" aria-label="Mission research configuration">
            <div className="architect-kicker"><span className="architect-kicker-dot"/> RESEARCH CONFIGURATION</div>
            <h2>Mission research architect</h2>
            <p>Shape an investigation using documented science topics. Selections here organize your research; they do not configure flight hardware or run a mission simulation.</p>
            <div className="architect-stats">
              <div><span>RESEARCH AREAS</span><strong>{String(selected.length).padStart(2, '0')} <small>/ {String(instruments.length).padStart(2, '0')}</small></strong></div>
              <div><span>ORBIT TOPIC</span><strong className="architect-orbit-value">{orbitOptions.find((item) => item.id === orbit)?.name ?? 'Not selected'}</strong></div>
            </div>
            <div className="architect-selected">
              <span className="architect-field-label">SELECTED INVESTIGATION AREAS</span>
              {selected.length > 0
                ? <div className="architect-chips">{selected.map((id) => <span key={id}>{instruments.find((item) => item.id === id)?.name ?? id}</span>)}</div>
                : <p className="architect-empty">No research areas selected. Start by choosing the topics relevant to your question.</p>}
            </div>
            <div className="architect-readiness">
              <span className="readiness-mark"><ShieldCheck size={15}/></span>
              <div><strong>Engineering inputs not yet supplied</strong><small>Mass, power, cost, and performance remain unavailable until source-backed values are added.</small></div>
            </div>
            <div className="architect-actions">
              <button type="button" className="architect-primary" onClick={() => goTo('Research categories')}>Configure research areas <ArrowUpRight size={14}/></button>
              <button type="button" className="architect-secondary" onClick={() => goTo('Mission brief')}>Open mission brief <ClipboardList size={14}/></button>
            </div>
            <div className="architect-footnote">NO FLIGHT SIMULATION · NO SYNTHETIC TELEMETRY · SOURCE-FIRST WORKFLOW</div>
          </aside>
        </div>

        <section className="quick-access" aria-labelledby="quick-access-title">
          <div className="quick-access-heading">
            <div><div className="section-eyebrow">EXPLORE THE WORKSPACE</div><h3 id="quick-access-title">Where would you like to start?</h3></div>
            <span>THREE WORKING RESEARCH PATHS</span>
          </div>
          <div className="quick-access-grid">
            <button type="button" className="quick-access-card" onClick={() => goTo('Research categories')}>
              <span className="quick-access-icon"><BookOpen size={18}/></span>
              <span className="quick-access-copy"><strong>Explore lunar research</strong><small>Choose science topics and orbit research areas.</small></span>
              <ArrowUpRight size={16}/>
            </button>
            <button type="button" className="quick-access-card" onClick={() => goTo('Mission brief')}>
              <span className="quick-access-icon"><ClipboardList size={18}/></span>
              <span className="quick-access-copy"><strong>Create a mission brief</strong><small>Record a mission concept and traceable requirements.</small></span>
              <ArrowUpRight size={16}/>
            </button>
            <button type="button" className="quick-access-card" onClick={() => goTo('NASA data sources')}>
              <span className="quick-access-icon"><Database size={18}/></span>
              <span className="quick-access-copy"><strong>Search NASA data</strong><small>Discover source records and inspect available products.</small></span>
              <ArrowUpRight size={16}/>
            </button>
          </div>
        </section>

        <section className="section-block">
          <div className="section-heading"><div><div className="section-eyebrow">SOURCE-VERIFIED INPUTS</div><h3>Engineering data availability</h3></div><span className="section-note">NO DATA PRODUCTS INGESTED</span></div>
          <div className="metrics-grid">
            <Metric label="Research categories" value="04" icon={Telescope} detail="Imaging, spectroscopy, radar, and thermal science" tone="blue"/>
            <Metric label="Orbit research topics" value="03" icon={Compass} detail="Architecture labels only; no orbit calculations" tone="amber"/>
            <Metric label="LOLA profile limit" value="512" unit="samples" icon={Activity} detail="Maximum contiguous samples per row request" tone="violet"/>
            <Metric label="NASA PDS search" value="On demand" icon={Database} detail="Official archive API · read-only requests" tone="green"/>
          </div>
        </section>

        <section className="designer-layout" id="designer">
          <div className="designer-main">
            <div className="section-heading designer-heading"><div><div className="section-eyebrow">RESEARCH CATEGORIES</div><h3>Choose research categories</h3><p>Select research categories. No hardware specifications are assumed or invented.</p></div><span className="section-note">SOURCE-BASED TOPICS</span></div>
            <div className="panel instrument-panel">
              <div className="panel-header"><div className="panel-title-icon"><Telescope size={17}/></div><div><strong>Science investigation areas</strong><span>Select topics to research in the source archives</span></div><span className="selected-count">{selected.length} SELECTED</span></div>
              <div className="instrument-list">{instruments.map(item => {
                const checked = selected.includes(item.id)
                return <button key={item.id} className={`instrument-row ${checked ? 'instrument-selected' : ''}`} onClick={() => toggleInstrument(item.id)} aria-pressed={checked}>
                  <span className={`instrument-check ${checked ? 'checked' : ''}` }>{checked && <Check size={13}/>}</span>
                  <span className="instrument-symbol"><InstrumentSymbol id={item.id}/></span>
                  <span className="instrument-info"><strong>{item.name}</strong><small>{item.purpose}</small></span>
                  
                </button>
              })}</div>
              <div className="panel-footnote"><CircleHelp size={14}/> These are research topics, not a verified flight-hardware catalogue. Mass, power, cost, and performance remain unavailable until sourced.</div>
            </div>

            <div className="panel options-panel">
              <div className="panel-header"><div className="panel-title-icon orbit-icon"><Satellite size={17}/></div><div><strong>Orbit research topics</strong><span>Choose a topic for research; no orbital parameters are assumed</span></div></div>
              <div className="orbit-options">{orbitOptions.map(item => <button key={item.id} className={orbit === item.id ? 'orbit-option chosen' : 'orbit-option'} onClick={() => setOrbit(item.id)}>
                <span className="orbit-radio">{orbit === item.id && <i/>}</span><span className="orbit-option-copy"><strong>{item.name}</strong><small>{item.coverage}</small></span>
              </button>)}</div>
              <div className="panel-footnote"><CircleHelp size={14}/> Architecture labels only. No altitude, ephemeris, trajectory, or contact-window value is provided.</div>
            </div>
          </div>

          <aside className="designer-side">
            <div className="panel verification-panel" id="input-readiness">
              <div className="verify-heading"><div><div className="section-eyebrow">ENGINEERING VERIFICATION</div><strong>Input readiness</strong></div><span className="warn-label">NOT READY</span></div>
              <div className="check-list">
                <div className="check-row"><span className="check-status fail"><X size={11}/></span><span>Mass properties</span><b>Not sourced</b></div>
                <div className="check-row"><span className="check-status fail"><X size={11}/></span><span>Power-system budget</span><b>Not sourced</b></div>
                <div className="check-row"><span className="check-status fail"><X size={11}/></span><span>Instrument data volume</span><b>Not sourced</b></div>
                <div className="check-row"><span className="check-status fail"><X size={11}/></span><span>Mission cost basis</span><b>Not sourced</b></div>
              </div>
              <div className="validation-divider"/>
              <div className="readiness"><span>ASSESSMENT STATUS</span><strong>Blocked pending traceable inputs</strong></div>
              <p className="resources-intro">ORBITOPS will not calculate a pass/fail result until the required source data, units, and applicable constraints are available.</p>
              <button className="run-button" onClick={() => goTo('NASA data sources')}><Database size={16}/> Review source catalogue <ArrowUpRight size={15}/></button>
            </div>
          </aside>
        </section>

        <MissionBrief />

        <section className="section-block resources-section" id="data-sources">
          <div className="section-heading">
            <div><div className="section-eyebrow">TRACEABLE REFERENCES</div><h3>NASA & science data resources</h3></div>
            <span className="section-note">SOURCE CATALOGUE · NOT INGESTED DATA</span>
          </div>
          <p className="resources-intro">Open the original archives and technical references. ORBITOPS does not fabricate measurements or imply that these external datasets have already been downloaded, processed, or synchronized.</p>
          <div className="panel pds-search-panel" aria-busy={pdsSearchLoading}>
            <div className="pds-search-heading"><div><strong>Search the NASA PDS archive</strong><span>Live read-only request to the official PDS Search API</span></div><span className="resource-kind">LIVE SOURCE QUERY</span></div>
            <form className="pds-search-controls" role="search" aria-label="Search NASA Planetary Data System" onSubmit={(event) => { event.preventDefault(); void searchPds() }}>
              <label className="pds-search-label" htmlFor="pds-keywords">Product keywords</label>
              <div className="pds-search-input-row">
                <input id="pds-keywords" name="keywords" type="search" value={pdsKeywords} onChange={(event) => setPdsKeywords(event.target.value)} placeholder="e.g. LOLA, Diviner, LROC" maxLength={120} minLength={2} autoComplete="off" aria-describedby="pds-search-help"/>
                <button className="run-button" type="submit" disabled={pdsSearchLoading || pdsKeywords.trim().length < 2}>
                  <Database size={15}/>{pdsSearchLoading ? 'Searching…' : 'Search PDS'}
                </button>
              </div>
            </form>
            <p className="pds-search-note" id="pds-search-help">Results are returned from NASA PDS at request time. The PDS Search API documentation warns that its servers do not yet contain every PDS dataset; an empty response must be checked against the mission archive index.</p>
            {pdsSearchLoading && <p className="pds-search-note" role="status">Contacting the NASA PDS Search API…</p>}
            {pdsSearchError && <p className="pds-search-error" role="alert">{pdsSearchError}</p>}
            {pdsSearchResponse && <div className="pds-results" aria-live="polite">
              <div className="pds-results-meta"><span>{pdsSearchResponse.source}</span><span>Retrieved {new Date(pdsSearchResponse.retrieved_at).toLocaleString()}</span></div>
              <a href={pdsSearchResponse.source_url} target="_blank" rel="noopener noreferrer">Open exact upstream query <ExternalLink size={12}/></a>
              {pdsProducts ? <div className="pds-product-results">
                <div className="pds-results-count">{'Returned ' + pdsProducts.products.length + ' product records'}{pdsProducts.hits === undefined ? '' : ' · PDS reports ' + pdsProducts.hits + ' total matches'}{pdsSearchResponse.query.limit ? ' · page limit ' + pdsSearchResponse.query.limit : ''}</div>
                {pdsProducts.products.length === 0
                  ? <p className="pds-empty">The PDS API returned no product records for this query. Check the mission-specific archive index; the Search API may not contain every holding.</p>
                  : pdsProducts.products.map((product) => <article className="pds-product-card" key={product.lidvid}>
                      <strong>{product.title ?? 'Title not supplied by source'}</strong>
                      <span>NASA PDS product identifier</span>
                      <code>{product.lidvid}</code>
                      <button type="button" onClick={() => void resolvePdsProduct(product.lidvid)}>Resolve source metadata <ArrowUpRight size={12}/></button>
                    </article>)}
              </div> : <pre>{JSON.stringify(pdsSearchResponse.response, null, 2)}</pre>}
            </div>}
          </div>
          <div className="resource-grid">
            {missionResources.map((resource) => (
              <article className="resource-card" key={resource.id}>
                <div className="resource-card-top"><span className="resource-kind">{resource.kind}</span><span className="resource-owner">{resource.owner}</span></div>
                <h4>{resource.title}</h4>
                <p>{resource.description}</p>
                <a href={resource.url} target="_blank" rel="noopener noreferrer">
                  Open original source <ExternalLink size={13}/>
                </a>
              </article>
            ))}
          </div>
          <div className="panel pds-search-panel">
            <div className="pds-search-heading"><div><strong>Resolve a PDS product identifier</strong><span>Retrieve metadata for a known product LID or LIDVID</span></div><span className="resource-kind">PRODUCT LOOKUP</span></div>
            <div className="pds-search-controls">
              <label className="pds-search-label" htmlFor="pds-identifier">PDS product identifier</label>
              <div className="pds-search-input-row">
                <input id="pds-identifier" value={pdsIdentifier} onChange={(event) => setPdsIdentifier(event.target.value)} placeholder="urn:nasa:pds:lro_lola_rdr:data_gridded::1.0" maxLength={512}/>
                <button className="run-button" type="button" onClick={() => void resolvePdsProduct()} disabled={pdsLookupLoading || pdsIdentifier.trim().length < 5}>
                  <Database size={15}/>{pdsLookupLoading ? 'Resolving…' : 'Resolve product'}
                </button>
              </div>
            </div>
            {pdsLookupError && <p className="pds-search-error" role="alert">{pdsLookupError}</p>}
            {pdsLookupResponse && <div className="pds-results">
              <div className="pds-results-meta"><span>{pdsLookupResponse.source}</span><span>Retrieved {new Date(pdsLookupResponse.retrieved_at).toLocaleString()}</span></div>
              <a href={pdsLookupResponse.source_url} target="_blank" rel="noopener noreferrer">Open exact upstream product metadata <ExternalLink size={12}/></a>
              <div className="pds-file-manifest">
                <div className="pds-results-count">Source file inventory · supplied by NASA PDS metadata</div>
                {pdsFiles.length === 0
                  ? <p className="pds-empty">This response contains no file inventory fields. No download location or checksum is inferred.</p>
                  : pdsFiles.map((file) => <article className="pds-file-row" key={file.role + ':' + file.fileName + ':' + file.fileReference}>
                      <div><strong>{file.fileName || 'Filename not supplied'}</strong><span>{file.role === 'label' ? 'PDS label file' : 'Data file'}{file.mimeType ? ' · ' + file.mimeType : ''}</span></div>
                      {file.fileReference && <code>{file.fileReference}</code>}
                      <small>{file.sizeBytes ? file.sizeBytes + ' bytes' : 'Size not supplied'}{file.md5 ? ' · MD5 ' + file.md5 : ''}</small>
                    </article>)}
              </div>
              <div className="pds-hierarchy-actions">
                <button type="button" onClick={() => void browsePdsMembers(pdsLookupResponse.identifier, 1)} disabled={pdsMembersLoading}>
                  {pdsMembersLoading ? 'Loading archive…' : 'Browse direct children'} <ArrowUpRight size={12}/>
                </button>
                <button type="button" onClick={() => void browsePdsMembers(pdsLookupResponse.identifier, 2)} disabled={pdsMembersLoading}>
                  Browse two hierarchy levels <ArrowUpRight size={12}/>
                </button>
              </div>
              <pre>{JSON.stringify(pdsLookupResponse.response, null, 2)}</pre>
            </div>}
          </div>

          <div className="panel pds-search-panel">
            <div className="pds-search-heading"><div><strong>Archive hierarchy results</strong><span>Child products returned by NASA PDS for the selected identifier</span></div><span className="resource-kind">LIVE ARCHIVE BROWSE</span></div>
            {pdsMembersError && <p className="pds-search-error" role="alert">{pdsMembersError}</p>}
            {pdsMembersResponse && <div className="pds-results">
              <div className="pds-results-meta"><span>Depth {pdsMembersResponse.depth} · {pdsMembersResponse.source}</span><span>Retrieved {new Date(pdsMembersResponse.retrieved_at).toLocaleString()}</span></div>
              <a href={pdsMembersResponse.source_url} target="_blank" rel="noopener noreferrer">Open exact upstream hierarchy query <ExternalLink size={12}/></a>
              {pdsMembers === null
                ? <pre>{JSON.stringify(pdsMembersResponse.response, null, 2)}</pre>
                : pdsMembers.length === 0
                  ? <p className="pds-empty">NASA PDS returned no child records for this identifier and hierarchy depth. Check the archive node's direct holdings.</p>
                  : <div className="pds-product-results">
                      <div className="pds-results-count">{pdsMembers.length} unique child records loaded across archive pages</div>
                      {pdsMembers.map((member) => <article className="pds-product-card" key={member.id}>
                        <strong>{member.title ?? 'Title not supplied by source'}</strong>
                        <span>{member.type ?? 'Product type not supplied'}</span>
                        <code>{member.id}</code>
                        {(member.start_date_time || member.stop_date_time) && <small>{member.start_date_time ?? 'Start time not supplied'} — {member.stop_date_time ?? 'Stop time not supplied'}</small>}
                        <button type="button" onClick={() => void resolvePdsProduct(member.id)}>Resolve product metadata <ArrowUpRight size={12}/></button>
                      </article>)}
                    </div>}
              {pdsMembersResponse.next_search_after && <button className="pds-load-more" type="button" disabled={pdsMembersLoading} onClick={() => void browsePdsMembers(pdsMembersResponse.identifier, pdsMembersResponse.depth, pdsMembersResponse.next_search_after ?? undefined)}>
                {pdsMembersLoading ? 'Loading next page…' : 'Load next 100 source records'} <ArrowUpRight size={12}/>
              </button>}
            </div>}
          </div>
          <div className="panel pds-search-panel">
            <div className="pds-search-heading"><div><strong>Verified LOLA south-polar label</strong><span>Fetch source metadata for one documented PDS3 GDR product</span></div><span className="resource-kind">LIVE LABEL LOOKUP</span></div>
            <p className="pds-search-note">The original 115 MB image has been downloaded and validated in the source-validation workflow. The live app retrieves individual pixels and bounded one-row profiles from the original archive using HTTP Range requests; it does not download the full raster on each interaction. The LOLA GDR SIS defines HEIGHT = DN × SCALING_FACTOR and PLANETARY_RADIUS = DN × SCALING_FACTOR + OFFSET.</p>
            <button className="run-button" type="button" onClick={() => void fetchLolaSampleLabel()} disabled={pdsLabelLoading}>
              <Database size={15}/>{pdsLabelLoading ? 'Fetching source label…' : 'Fetch original LOLA label metadata'}
            </button>
            {pdsLabelError && <p className="pds-search-error" role="alert">{pdsLabelError}</p>}
            {pdsLabelResponse && <div className="pds-results">
              <div className="pds-results-meta"><span>{pdsLabelResponse.source} · {pdsLabelResponse.label_format}</span><span>Retrieved {new Date(pdsLabelResponse.retrieved_at).toLocaleString()}</span></div>
              <a href={pdsLabelResponse.source_url} target="_blank" rel="noopener noreferrer">Open original detached label <ExternalLink size={12}/></a>
              <div className="pds-search-note"><a href="https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/document/rdrsis.htm" target="_blank" rel="noopener noreferrer">LOLA RDR/GDR Software Interface Specification <ExternalLink size={12}/></a> · <a href="https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/catalog/dsmap_polar.cat" target="_blank" rel="noopener noreferrer">Official polar projection equations <ExternalLink size={12}/></a></div>
              <div className="pds-file-manifest">
                <div className="pds-results-count">{pdsLabelResponse.product_file} · metadata exactly as returned from the source label</div>
                {([
                  ['Data set', 'DATA_SET_ID'],
                  ['Product version', 'PRODUCT_VERSION_ID'],
                  ['Target', 'TARGET_NAME'],
                  ['Projection', 'MAP_PROJECTION_TYPE'],
                  ['Latitude range', 'MINIMUM_LATITUDE'],
                  ['Maximum latitude', 'MAXIMUM_LATITUDE'],
                  ['Grid scale', 'MAP_SCALE'],
                  ['Image dimensions', 'LINES'],
                  ['Samples per line', 'LINE_SAMPLES'],
                  ['Image records', 'FILE_RECORDS'],
                  ['Bytes per record', 'RECORD_BYTES'],
                  ['Image data field', 'NAME'],
                  ['Reference sphere', 'A_AXIS_RADIUS'],
                  ['Line projection offset', 'LINE_PROJECTION_OFFSET'],
                  ['Sample projection offset', 'SAMPLE_PROJECTION_OFFSET'],
                  ['Projection rotation', 'MAP_PROJECTION_ROTATION'],
                  ['Sample type', 'SAMPLE_TYPE'],
                  ['Sample bits', 'SAMPLE_BITS'],
                  ['Unit', 'UNIT'],
                  ['Scaling factor', 'SCALING_FACTOR'],
                  ['Offset', 'OFFSET'],
                  ['Coordinate reference', 'COORDINATE_SYSTEM_NAME'],
                ] as const).map(([label, key]) => pdsLabelResponse.metadata[key] ? <article className="pds-file-row" key={key}>
                  <div><strong>{label}</strong><span>{pdsLabelResponse.metadata[key]}</span></div>
                </article> : null)}
              </div>
              <div className="lola-coordinate-tool">
                <div className="pds-results-count">PDS polar-grid coordinate lookup · zero-based pixel indices</div>
                <div className="lola-coordinate-fields">
                  <label>Line index
                    <input type="number" min="0" max={Number(pdsLabelResponse.metadata.LINES) - 1} step="1" disabled={lolaPixelLoading || lolaProfileLoading} value={lolaLineIndex} onChange={(event) => { setLolaLineIndex(event.target.value); setLolaPixelResponse(null); setLolaPixelError(''); setLolaProfileResponse(null); setLolaProfileError('') }} />
                  </label>
                  <label>Sample index
                    <input type="number" min="0" max={Number(pdsLabelResponse.metadata.LINE_SAMPLES) - 1} step="1" disabled={lolaPixelLoading || lolaProfileLoading} value={lolaSampleIndex} onChange={(event) => { setLolaSampleIndex(event.target.value); setLolaPixelResponse(null); setLolaPixelError(''); setLolaProfileResponse(null); setLolaProfileError('') }} />
                  </label>
                </div>
                {lolaPixelLocation ? <div className="lola-coordinate-result" aria-live="polite">
                  <div><span>Planetocentric latitude</span><strong>{lolaPixelLocation.latitudeDegrees.toFixed(8)}°</strong></div>
                  <div><span>East longitude</span><strong>{lolaPixelLocation.eastLongitudeDegrees.toFixed(8)}°</strong></div>
                  <div><span>Projected X / Y</span><strong>{lolaPixelLocation.xMapMeters.toFixed(2)} m / {lolaPixelLocation.yMapMeters.toFixed(2)} m</strong></div>
                </div> : <p className="pds-search-error" role="alert">{lolaPixelLocationError}</p>}
                <button className="run-button lola-pixel-button" type="button" onClick={() => void fetchLolaPixel()} disabled={!lolaPixelLocation || lolaPixelLoading || lolaProfileLoading}>
                  <Database size={15}/>{lolaPixelLoading ? 'Reading two source bytes…' : 'Fetch actual NASA LOLA pixel'}
                </button>
                {lolaPixelError && <p className="pds-search-error" role="alert">{lolaPixelError}</p>}
                {lolaPixelResponse && <div className="lola-coordinate-result lola-pixel-result" aria-live="polite">
                  <div><span>Original signed DN</span><strong>{lolaPixelResponse.raw_dn}</strong></div>
                  <div><span>LOLA GDR height</span><strong>{lolaPixelResponse.height_m.toFixed(2)} m</strong></div>
                  <div><span>Planetary radius</span><strong>{lolaPixelResponse.planetary_radius_m.toFixed(2)} m</strong></div>
                  <div><span>Source byte range</span><strong>{lolaPixelResponse.byte_range_inclusive.start}–{lolaPixelResponse.byte_range_inclusive.end}</strong></div>
                  <div className="lola-pixel-provenance"><span>Retrieved {new Date(lolaPixelResponse.retrieved_at).toLocaleString()}</span><a href={lolaPixelResponse.source_url} target="_blank" rel="noopener noreferrer">Original PDS raster source <ExternalLink size={11}/></a><small>{lolaPixelResponse.validation_scope}</small></div>
                </div>}
                <div className="lola-profile-controls">
                  <label>Profile samples
                    <input type="number" min="1" max="512" step="1" disabled={lolaPixelLoading || lolaProfileLoading} value={lolaProfileCount} onChange={(event) => { setLolaProfileCount(event.target.value); setLolaProfileResponse(null); setLolaProfileError('') }} />
                  </label>
                  <button className="run-button" type="button" onClick={() => void fetchLolaProfile()} disabled={!lolaPixelLocation || lolaProfileLoading || lolaPixelLoading}>
                    <Activity size={15}/>{lolaProfileLoading ? 'Reading source row segment…' : 'Fetch real elevation profile'}
                  </button>
                </div>
                {lolaProfileError && <p className="pds-search-error" role="alert">{lolaProfileError}</p>}
                {lolaProfileResponse && <div className="lola-profile-panel">
                  <div className="lola-profile-heading"><strong>LOLA source elevation profile</strong><span>{lolaProfileResponse.sample_count} original samples · line {lolaProfileResponse.line_index} · {lolaProfileResponse.sample_spacing_m} m/pixel</span></div>
                  <svg className="lola-profile-chart" viewBox="0 0 800 220" role="img" aria-label={`Source-derived LOLA elevation profile in metres, sampled every ${lolaProfileResponse.sample_spacing_m} metres, with no interpolation`}>
                    <line x1="12" y1="190" x2="788" y2="190" stroke="#344b62" strokeWidth="1"/>
                    <line x1="12" y1="30" x2="12" y2="190" stroke="#344b62" strokeWidth="1"/>
                    <polyline points={profilePolyline} fill="none" stroke="#8bd5ef" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round"/>
                  </svg>
                  <div className="lola-profile-range"><span>Min {profileMinHeight.toFixed(2)} m</span><span>Max {profileMaxHeight.toFixed(2)} m</span><span>Span {lolaProfileResponse.profile_span_m.toFixed(2)} m</span></div>
                  <div className="lola-profile-heading"><span>Samples {lolaProfileResponse.start_sample_index}–{lolaProfileResponse.start_sample_index + lolaProfileResponse.sample_count - 1}</span><a href={lolaProfileResponse.source_url} target="_blank" rel="noopener noreferrer">Original PDS raster <ExternalLink size={11}/></a></div>
                  <p className="pds-search-note">{lolaProfileResponse.validation_scope} No smoothing or interpolation is applied to this plotted series.</p>
                </div>}
                <p className="pds-search-note">Coordinates are calculated from the retrieved PDS label and DSMAP_POLAR equations. The pixel action requests exactly two bytes and the profile action requests one bounded contiguous row segment from the fixed PDS archive URL using HTTP Range; both refuse servers that return the full raster instead.</p>
              </div>
              <p className="pds-search-note">{pdsLabelResponse.note} Label fields retain their original source units; derived pixel and profile values are shown separately using the documented GDR conversions.</p>
            </div>}
          </div>
          <LaltLabelInspector />
          <p className="resource-disclaimer">NASA does not endorse this independent project. Non-U.S. Government resources remain subject to their own data-use terms; review those terms before reuse.</p>
        </section>

        <section className="section-block readiness-note">
          <div className="section-heading"><div><div className="section-eyebrow">NEXT ENGINEERING GATE</div><h3>Source validation before calculations</h3></div><span className="section-note">REQUIREMENT GATE 01</span></div>
          <p className="resources-intro">The next step is to select specific NASA/PDS products, preserve their original labels and metadata, and verify units and coordinate references. Until then, numerical mission outputs remain unavailable by design.</p>
          <button className="primary-button" onClick={() => goTo('NASA data sources')}><Database size={16}/> Browse authoritative sources <ArrowUpRight size={15}/></button>
        </section>

        <footer className="footer"><div><span className="footer-mark"><OrbitMark/></span><strong>ORBITOPS</strong><span>EDUCATIONAL SPACE SCIENCE RESEARCH WORKSPACE</span></div><p>Independent educational project · Not affiliated with or endorsed by NASA.</p><p>Unverified engineering values are intentionally not displayed.</p></footer>
      </div>
    </main>
    {showAll && <div className="guide-popover"><button className="guide-close" onClick={() => setShowAll(false)} aria-label="Close guide"><X size={16}/></button><div className="section-eyebrow">ENGINEERING NOTES</div><h3>How to read this workspace</h3><p><strong>Source catalogue</strong> links to original NASA/PDS/JPL and partner reference pages. A link does not mean the dataset has been downloaded or processed.</p><p><strong>Engineering values</strong> remain unavailable until a specific source product and its metadata are ingested and validated.</p><p><strong>Architecture choices</strong> are labels only. ORBITOPS does not calculate or simulate trajectories, spacecraft performance, illumination, or communications.</p><p className="guide-source">The project will show missing data as unavailable instead of filling gaps with invented assumptions. See the data provenance plan for the ingestion requirements.</p></div>}
  </div>
}

function OrbitMark() {
  return <svg viewBox="0 0 36 36" fill="none" aria-hidden="true"><circle cx="18" cy="18" r="5" fill="#9FE6FF"/><ellipse cx="18" cy="18" rx="15" ry="7" stroke="#55BCEB" strokeWidth="1.5" transform="rotate(-35 18 18)"/><circle cx="30" cy="10" r="2.2" fill="#D8F5FF"/></svg>
}

function InstrumentSymbol({ id }: { id: string }) {
  if (id === 'camera') return <Globe2 size={19}/>
  if (id === 'spectrometer') return <Atom size={19}/>
  if (id === 'radar') return <Radio size={19}/>
  return <BatteryCharging size={19}/>
}

export default App
