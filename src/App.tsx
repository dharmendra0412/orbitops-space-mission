import { useState } from 'react'
import {
  Activity, ArrowUpRight, Atom, BatteryCharging, Check,
  ChevronDown, CircleHelp, Compass, Database, Globe2, Layers3,
  Menu, Radio, Rocket, Satellite, Settings2, ShieldCheck,
  SlidersHorizontal, Target, Telescope, Users, X, ExternalLink
} from 'lucide-react'

import { instruments, orbitOptions } from './domain/mission'
import { missionResources } from './data/sources'

function Metric({ label, value, unit, icon: Icon, tone = 'blue', detail }: {
  label: string; value: string; unit?: string; icon: typeof Activity; tone?: string; detail: string
}) {
  return <div className="metric-card">
    <div className="metric-top"><span>{label}</span><span className={`metric-icon ${tone}`}><Icon size={16} /></span></div>
    <div className="metric-value">{value}<small>{unit}</small></div>
    <div className="metric-detail">{detail}</div>
  </div>
}

function App() {
  const [activeNav, setActiveNav] = useState('Mission overview')
  const [selected, setSelected] = useState<string[]>([])
  const [orbit, setOrbit] = useState('low')
  const [showAll, setShowAll] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const toggleInstrument = (id: string) => {
    setSelected(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id])
    setRunState('idle')
  }

  const navItems = ['Mission overview', 'Spacecraft designer', 'Constraint checks', 'NASA data sources', 'Engineering guide']
  const goTo = (item: string) => {
    setActiveNav(item)
    setMobileMenu(false)
    if (item === 'Spacecraft designer') document.getElementById('designer')?.scrollIntoView({ behavior: 'smooth' })
    else if (item === 'Mission overview') window.scrollTo({ top: 0, behavior: 'smooth' })
    else if (item === 'Engineering guide') setShowAll(true)
    else if (item === 'NASA data sources') document.getElementById('data-sources')?.scrollIntoView({ behavior: 'smooth' })
    else document.getElementById('mission-output')?.scrollIntoView({ behavior: 'smooth' })
  }

  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><OrbitMark /></div><div><strong>ORBITOPS</strong><span>MISSION ENGINEERING</span></div><button className="icon-button mobile-close" onClick={() => setMobileMenu(false)} aria-label="Close menu"><X size={18}/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <div className="workspace-switch"><div className="workspace-avatar">LP</div><div><strong>Example workspace</strong><span>Local draft only</span></div><ChevronDown size={15}/></div>
      <div className="nav-label">MISSION</div>
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
        <div className="profile"><div className="profile-avatar">G</div><div><strong>Guest workspace</strong><span>Not signed in</span></div><Settings2 size={16}/></div>
      </div>
    </aside>

    {mobileMenu && <button className="scrim" onClick={() => setMobileMenu(false)} aria-label="Close navigation"/>}
    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs"><button className="mobile-menu-button icon-button" onClick={() => setMobileMenu(true)} aria-label="Open menu"><Menu size={19}/></button><span>MISSIONS</span><span className="crumb-slash">/</span><strong>LUNAR PATHFINDER</strong></div>
        <div className="top-actions"><span className="autosave"><span className="status-dot"/> Local preview · changes not saved</span><button className="team-button" disabled title="Team collaboration will be implemented in a later milestone"><Users size={16}/> Team mode planned</button><div className="top-avatar">G</div></div>
      </header>

      <div className="content">
        <section className="page-heading">
          <div><div className="eyebrow"><span className="eyebrow-line"/> MISSION WORKSPACE <span className="eyebrow-tag">CONCEPT PHASE</span></div><h1>Mission overview<span className="heading-period">.</span></h1><p>Turn a scientific objective into an engineered mission concept.</p></div>
          <button className="primary-button" onClick={() => goTo('Spacecraft designer')}><Rocket size={16}/> Configure spacecraft <ArrowUpRight size={15}/></button>
        </section>

        <section className="mission-hero">
          <div className="hero-copy">
            <div className="hero-kicker"><span className="hero-kicker-dot"/> EXAMPLE WORKSPACE <span className="hero-id">NOT A REAL MISSION</span></div>
            <h2>Lunar <em>Pathfinder</em></h2>
            <p>Investigate lunar polar terrain, characterize surface conditions, and identify regions of scientific interest for future exploration.</p>
            <div className="hero-tags"><span><Target size={13}/> Lunar science</span><span><Compass size={13}/> South polar region</span><span><Atom size={13}/> Orbiter concept</span></div>
            <button className="hero-link" onClick={() => goTo('Spacecraft designer')}>Continue mission design <ArrowUpRight size={15}/></button>
          </div>
          <div className="moon-scene" aria-label="Decorative illustration of the Moon and a spacecraft; not mission data">
            <div className="orbit-ring orbit-one"/><div className="orbit-ring orbit-two"/><div className="moon"><div className="moon-crater crater-one"/><div className="moon-crater crater-two"/><div className="moon-crater crater-three"/><div className="moon-crater crater-four"/></div>
            <div className="satellite-art"><div className="sat-body"/><div className="sat-panel left"/><div className="sat-panel right"/><div className="sat-antenna"/></div>
            <div className="scene-label label-orbit"><span/> CONCEPT ARTWORK</div>
            <div className="scene-coordinates">EXAMPLE TARGET <span>/</span> LUNAR SOUTH POLE</div>
          </div>
          <div className="hero-footer"><span>WORKSPACE <strong>EXAMPLE ONLY</strong></span><span>DATA STATUS <strong>NO PRODUCTS INGESTED</strong></span><span>TEAM MODE <strong>NOT CONNECTED</strong></span></div>
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
            <div className="section-heading designer-heading"><div><div className="section-eyebrow">CONFIGURATION STUDIO</div><h3>Build your spacecraft</h3><p>Select research categories. No hardware specifications are assumed or invented.</p></div><span className="step-pill">STEP 02 <span>/ 05</span></span></div>
            <div className="panel instrument-panel">
              <div className="panel-header"><div className="panel-title-icon"><Telescope size={17}/></div><div><strong>Scientific payload</strong><span>Select instruments for your mission objectives</span></div><span className="selected-count">{selected.length} SELECTED</span></div>
              <div className="instrument-list">{instruments.map(item => {
                const checked = selected.includes(item.id)
                return <button key={item.id} className={`instrument-row ${checked ? 'instrument-selected' : ''}`} onClick={() => toggleInstrument(item.id)} aria-pressed={checked}>
                  <span className={`instrument-check ${checked ? 'checked' : ''}` }>{checked && <Check size={13}/>}</span>
                  <span className="instrument-symbol"><InstrumentSymbol id={item.id}/></span>
                  <span className="instrument-info"><strong>{item.name}</strong><small>{item.purpose}</small></span>
                  
                </button>
              })}</div>
              <div className="panel-footnote"><CircleHelp size={14}/> These are research categories, not a verified flight-hardware catalogue. Mass, power, cost, and performance remain unavailable until sourced.</div>
            </div>

            <div className="panel options-panel">
              <div className="panel-header"><div className="panel-title-icon orbit-icon"><Satellite size={17}/></div><div><strong>Orbit selection</strong><span>Choose an orbit concept for polar observations</span></div></div>
              <div className="orbit-options">{orbitOptions.map(item => <button key={item.id} className={orbit === item.id ? 'orbit-option chosen' : 'orbit-option'} onClick={() => { setOrbit(item.id); setRunState('idle') }}>
                <span className="orbit-radio">{orbit === item.id && <i/>}</span><span className="orbit-option-copy"><strong>{item.name}</strong><small>{item.coverage}</small></span>
              </button>)}</div>
              <div className="panel-footnote"><CircleHelp size={14}/> Architecture labels only. No altitude, ephemeris, trajectory, or contact-window value is provided.</div>
            </div>
          </div>

          <aside className="designer-side">
            <div className="panel verification-panel" id="mission-output">
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
          <div className="resource-grid">
            {missionResources.map((resource) => (
              <article className="resource-card" key={resource.id}>
                <div className="resource-card-top"><span className="resource-kind">{resource.kind}</span><span className="resource-owner">{resource.owner}</span></div>
                <h4>{resource.title}</h4>
                <p>{resource.description}</p>
                <a href={resource.url} target="_blank" rel="noreferrer">
                  Open original source <ExternalLink size={13}/>
                </a>
              </article>
            ))}
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
