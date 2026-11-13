import { useState } from 'react'
import {
  Activity, ArrowUpRight, Atom, BatteryCharging, Check,
  ChevronDown, CircleHelp, Compass, Database, Globe2, Layers3,
  Menu, Radio, Rocket, Satellite, Settings2, ShieldCheck,
  SlidersHorizontal, Target, Telescope, Users, X, ExternalLink
} from 'lucide-react'

import { instruments, orbitOptions } from './domain/catalog'
import { missionResources } from './data/sources'
import { extractPdsFileManifest, extractPdsMembers, extractPdsProducts } from './data/pds'

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


function App() {
  const [activeNav, setActiveNav] = useState('Research overview')
  const [selected, setSelected] = useState<string[]>([])
  const [orbit, setOrbit] = useState('low')
  const [showAll, setShowAll] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const [pdsKeywords, setPdsKeywords] = useState('LOLA')
  const [pdsSearchResponse, setPdsSearchResponse] = useState<PdsSearchResponse | null>(null)
  const [pdsSearchError, setPdsSearchError] = useState('')
  const [pdsSearchLoading, setPdsSearchLoading] = useState(false)
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
  const toggleInstrument = (id: string) => {
    setSelected(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id])
  }


  const pdsProducts = pdsSearchResponse ? extractPdsProducts(pdsSearchResponse.response) : null
  const pdsFiles = pdsLookupResponse ? extractPdsFileManifest(pdsLookupResponse.response) : []

  const searchPds = async () => {
    const keywords = pdsKeywords.trim()
    if (keywords.length < 2) {
      setPdsSearchError('Enter at least two characters to search the NASA PDS archive.')
      setPdsSearchResponse(null)
      return
    }

    setPdsSearchLoading(true)
    setPdsSearchError('')
    setPdsSearchResponse(null)
    try {
      const params = new URLSearchParams({ keywords, limit: '10' })
      const response = await fetch('/api/v1/pds/search?' + params.toString())
      const payload = await response.json() as PdsSearchResponse | { detail?: string }
      if (!response.ok) {
        const message = 'detail' in payload && payload.detail ? payload.detail : 'PDS search failed (HTTP ' + response.status + ')'
        throw new Error(message)
      }
      setPdsSearchResponse(payload as PdsSearchResponse)
    } catch (error) {
      setPdsSearchError(error instanceof Error ? error.message : 'Unable to retrieve NASA PDS results.')
    } finally {
      setPdsSearchLoading(false)
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
      const response = await fetch('/api/v1/pds/products/' + encodeURIComponent(identifier))
      const payload = await response.json() as PdsLookupResponse | { detail?: string }
      if (!response.ok) {
        const message = 'detail' in payload && payload.detail ? payload.detail : 'PDS product lookup failed (HTTP ' + response.status + ')'
        throw new Error(message)
      }
      setPdsIdentifier(identifier)
      setPdsLookupResponse(payload as PdsLookupResponse)
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
      const response = await fetch('/api/v1/pds/products/' + encodeURIComponent(identifier) + '/members?' + params.toString())
      const payload = await response.json() as PdsMembersResponse | { detail?: string }
      if (!response.ok) {
        const message = 'detail' in payload && payload.detail ? payload.detail : 'PDS hierarchy request failed (HTTP ' + response.status + ')'
        throw new Error(message)
      }
      const parsedMembers = extractPdsMembers((payload as PdsMembersResponse).response)
      setPdsMembersStructured(parsedMembers !== null)
      if (parsedMembers) {
        setPdsMembersRecords((current) => {
          if (!searchAfter) return parsedMembers
          const known = new Set(current.map((member) => member.id))
          return [...current, ...parsedMembers.filter((member) => !known.has(member.id))]
        })
      } else if (!searchAfter) {
        setPdsMembersRecords([])
      }
      setPdsIdentifier(identifier)
      setPdsMembersResponse(payload as PdsMembersResponse)
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
    try {
      const response = await fetch('/api/v1/pds3/lola/gdr/ldem-85s-40m/label')
      const payload = await response.json() as Pds3LabelResponse | { detail?: string }
      if (!response.ok) {
        const message = 'detail' in payload && payload.detail ? payload.detail : 'LOLA label request failed (HTTP ' + response.status + ')'
        throw new Error(message)
      }
      setPdsLabelResponse(payload as Pds3LabelResponse)
    } catch (error) {
      setPdsLabelError(error instanceof Error ? error.message : 'Unable to retrieve the original LOLA label.')
    } finally {
      setPdsLabelLoading(false)
    }
  }

  const navItems = ['Research overview', 'Research categories', 'Input readiness', 'NASA data sources', 'Engineering guide']
  const goTo = (item: string) => {
    setActiveNav(item)
    setMobileMenu(false)
    if (item === 'Research categories') document.getElementById('designer')?.scrollIntoView({ behavior: 'smooth' })
    else if (item === 'Research overview') window.scrollTo({ top: 0, behavior: 'smooth' })
    else if (item === 'Engineering guide') setShowAll(true)
    else if (item === 'NASA data sources') document.getElementById('data-sources')?.scrollIntoView({ behavior: 'smooth' })
    else document.getElementById('input-readiness')?.scrollIntoView({ behavior: 'smooth' })
  }

  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><OrbitMark /></div><div><strong>ORBITOPS</strong><span>SPACE SCIENCE WORKSPACE</span></div><button className="icon-button mobile-close" onClick={() => setMobileMenu(false)} aria-label="Close menu"><X size={18}/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <div className="workspace-switch"><div className="workspace-avatar">RS</div><div><strong>Research workspace</strong><span>No mission configured</span></div><ChevronDown size={15}/></div>
      <div className="nav-label">RESEARCH</div>
      <nav className="side-nav">{navItems.map((item, index) => {
        const icons = [Globe2, SlidersHorizontal, Activity, Database, Layers3]
        const Icon = icons[index]
        return <button key={item} className={activeNav === item ? 'nav-item active' : 'nav-item'} onClick={() => goTo(item)}><Icon size={17}/><span>{item}</span>{index === 2 && <span className="nav-live">CHECKS</span>}</button>
      })}</nav>
      <div className="nav-label tools-label">TOOLS</div>
      <button className="nav-item" onClick={() => setShowAll(!showAll)}><Layers3 size={17}/><span>Engineering guide</span></button>
      <button className="nav-item" onClick={() => setShowAll(true)}><ShieldCheck size={17}/><span>Model limitations</span></button>
      <div className="sidebar-bottom">
        <div className="help-card"><div className="help-icon"><CircleHelp size={17}/></div><strong>Need a hand?</strong><p>Explore the engineering guide to understand mission trade-offs.</p><button onClick={() => setShowAll(!showAll)}>Open learning guide <ArrowUpRight size={13}/></button></div>
        <div className="profile"><div className="profile-avatar">R</div><div><strong>Research session</strong><span>Local browser only</span></div><Settings2 size={16}/></div>
      </div>
    </aside>

    {mobileMenu && <button className="scrim" onClick={() => setMobileMenu(false)} aria-label="Close navigation"/>}
    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs"><button className="mobile-menu-button icon-button" onClick={() => setMobileMenu(true)} aria-label="Open menu"><Menu size={19}/></button><span>RESEARCH</span><span className="crumb-slash">/</span><strong>LUNAR SCIENCE</strong></div>
        <div className="top-actions"><span className="autosave"><span className="status-dot"/> Local session · not saved</span><button className="team-button" disabled title="Team collaboration will be implemented in a later milestone"><Users size={16}/> Team mode planned</button><div className="top-avatar">G</div></div>
      </header>

      <div className="content">
        <section className="page-heading">
          <div><div className="eyebrow"><span className="eyebrow-line"/> SCIENCE RESEARCH WORKSPACE</div><h1>Research overview<span className="heading-period">.</span></h1><p>Explore authoritative lunar science data and technical documentation.</p></div>
          <button className="primary-button" onClick={() => goTo('Research categories')}><Rocket size={16}/> Explore research areas <ArrowUpRight size={15}/></button>
        </section>

        <section className="mission-hero">
          <div className="hero-copy">
            <div className="hero-kicker"><span className="hero-kicker-dot"/> RESEARCH AREA <span className="hero-id">NO MISSION CONFIGURED</span></div>
            <h2>Lunar <em>science</em></h2>
            <p>Review original lunar polar science products and their documentation. No spacecraft, trajectory, mission scenario, or scientific result is assumed in this workspace.</p>
            <div className="hero-tags"><span><Target size={13}/> Lunar science</span><span><Compass size={13}/> South-polar data</span><span><Database size={13}/> Source-first research</span></div>
            <button className="hero-link" onClick={() => goTo('NASA data sources')}>Browse NASA data sources <ArrowUpRight size={15}/></button>
          </div>
          <div className="hero-footer"><span>WORKSPACE <strong>RESEARCH ONLY</strong></span><span>DATA STATUS <strong>NO PRODUCTS INGESTED</strong></span><span>MISSION CONFIG <strong>NOT CONFIGURED</strong></span></div>
        </section>

        <section className="section-block">
          <div className="section-heading"><div><div className="section-eyebrow">SOURCE-VERIFIED INPUTS</div><h3>Engineering data availability</h3></div><span className="section-note">NO DATA PRODUCTS INGESTED</span></div>
          <div className="metrics-grid">
            <Metric label="Spacecraft mass" value="N/A" icon={Layers3} detail="No verified spacecraft configuration source" tone="blue"/>
            <Metric label="Power budget" value="N/A" icon={Activity} detail="No verified power-system source" tone="amber"/>
            <Metric label="Data volume" value="N/A" icon={Database} detail="No instrument product or telemetry source" tone="violet"/>
            <Metric label="Mission cost" value="N/A" icon={Target} detail="No cost model or approved estimate source" tone="green"/>
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

        <section className="section-block resources-section" id="data-sources">
          <div className="section-heading">
            <div><div className="section-eyebrow">TRACEABLE REFERENCES</div><h3>NASA & science data resources</h3></div>
            <span className="section-note">SOURCE CATALOGUE · NOT INGESTED DATA</span>
          </div>
          <p className="resources-intro">Open the original archives and technical references. ORBITOPS does not fabricate measurements or imply that these external datasets have already been downloaded, processed, or synchronized.</p>
          <div className="panel pds-search-panel">
            <div className="pds-search-heading"><div><strong>Search the NASA PDS archive</strong><span>Live read-only request to the official PDS Search API</span></div><span className="resource-kind">LIVE SOURCE QUERY</span></div>
            <div className="pds-search-controls">
              <label className="pds-search-label" htmlFor="pds-keywords">Product keywords</label>
              <div className="pds-search-input-row">
                <input id="pds-keywords" value={pdsKeywords} onChange={(event) => setPdsKeywords(event.target.value)} placeholder="e.g. LOLA, Diviner, LROC" maxLength={120}/>
                <button className="run-button" type="button" onClick={() => void searchPds()} disabled={pdsSearchLoading || pdsKeywords.trim().length < 2}>
                  <Database size={15}/>{pdsSearchLoading ? 'Searching…' : 'Search PDS'}
                </button>
              </div>
            </div>
            <p className="pds-search-note">Results are returned from NASA PDS at request time. The PDS Search API documentation warns that its servers do not yet contain every PDS dataset; an empty response must be checked against the mission archive index.</p>
            {pdsSearchError && <p className="pds-search-error" role="alert">{pdsSearchError}</p>}
            {pdsSearchResponse && <div className="pds-results">
              <div className="pds-results-meta"><span>{pdsSearchResponse.source}</span><span>Retrieved {new Date(pdsSearchResponse.retrieved_at).toLocaleString()}</span></div>
              <a href={pdsSearchResponse.source_url} target="_blank" rel="noopener noreferrer">Open exact upstream query <ExternalLink size={12}/></a>
              {pdsProducts ? <div className="pds-product-results">
                <div className="pds-results-count">{pdsProducts.hits === undefined ? 'Returned products' : pdsProducts.hits + ' matching products reported by PDS'}</div>
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
            <p className="pds-search-note">This endpoint retrieves the detached label only. It does not download or decode the associated 115 MB image file. Height conversion is deliberately disabled because official LOLA references disagree on whether OFFSET belongs in HEIGHT; no terrain elevations are calculated.</p>
            <button className="run-button" type="button" onClick={() => void fetchLolaSampleLabel()} disabled={pdsLabelLoading}>
              <Database size={15}/>{pdsLabelLoading ? 'Fetching source label…' : 'Fetch original LOLA label metadata'}
            </button>
            {pdsLabelError && <p className="pds-search-error" role="alert">{pdsLabelError}</p>}
            {pdsLabelResponse && <div className="pds-results">
              <div className="pds-results-meta"><span>{pdsLabelResponse.source} · {pdsLabelResponse.label_format}</span><span>Retrieved {new Date(pdsLabelResponse.retrieved_at).toLocaleString()}</span></div>
              <a href={pdsLabelResponse.source_url} target="_blank" rel="noopener noreferrer">Open original detached label <ExternalLink size={12}/></a>
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
              <p className="pds-search-note">{pdsLabelResponse.note} Values and units are source metadata; no unit conversion has been applied.</p>
            </div>}
          </div>
          <p className="resource-disclaimer">NASA does not endorse this independent project. Non-U.S. Government resources remain subject to their own data-use terms; review those terms before reuse.</p>
        </section>

        <section className="section-block readiness-note">
          <div className="section-heading"><div><div className="section-eyebrow">NEXT ENGINEERING GATE</div><h3>Source validation before calculations</h3></div><span className="section-note">REQUIREMENT GATE 01</span></div>
          <p className="resources-intro">The next step is to select specific NASA/PDS products, preserve their original labels and metadata, and verify units and coordinate references. Until then, numerical mission outputs remain unavailable by design.</p>
          <button className="primary-button" onClick={() => goTo('NASA data sources')}><Database size={16}/> Browse authoritative sources <ArrowUpRight size={15}/></button>
        </section>

        <footer className="footer"><div><span className="footer-mark"><OrbitMark/></span><strong>ORBITOPS</strong><span>EDUCATIONAL MISSION PLANNING WORKSPACE</span></div><p>Independent educational project · Not affiliated with or endorsed by NASA.</p><p>Unverified engineering values are intentionally not displayed.</p></footer>
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
