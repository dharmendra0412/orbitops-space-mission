import { useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import {
  Activity, ArrowDownRight, ArrowUpRight, Atom, BatteryCharging, Check,
  ChevronDown, CircleHelp, Compass, Database, Gauge, Globe2, Layers3,
  Menu, Radio, Rocket, Satellite, Settings2, ShieldCheck,
  SlidersHorizontal, Sparkles, Target, Telescope, Users, X, Zap
} from 'lucide-react'

type Instrument = {
  id: string
  name: string
  purpose: string
  mass: number
  power: number
  data: number
  science: number
}

const instruments: Instrument[] = [
  { id: 'camera', name: 'Terrain imaging camera', purpose: 'Context imaging and landing-site reconnaissance', mass: 4.2, power: 18, data: 1.8, science: 18 },
  { id: 'spectrometer', name: 'Near-infrared spectrometer', purpose: 'Surface mineral and volatile signatures', mass: 7.5, power: 32, data: 3.6, science: 28 },
  { id: 'radar', name: 'Subsurface radar sounder', purpose: 'Shallow subsurface structure investigation', mass: 11.8, power: 48, data: 5.2, science: 30 },
  { id: 'thermal', name: 'Thermal radiometer', purpose: 'Surface temperature observations', mass: 5.1, power: 22, data: 1.2, science: 20 },
]

const platform = { mass: 42, power: 85, data: 0.35, budget: 48 }
const orbitOptions = [
  { id: 'low', name: 'Low lunar orbit', altitude: '100 km', coverage: 'High-resolution regional passes', multiplier: 1, comm: 1 },
  { id: 'elliptical', name: 'Elliptical polar orbit', altitude: '30 × 1,000 km', coverage: 'Long dwell near selected polar regions', multiplier: 1.12, comm: 0.82 },
  { id: 'high', name: 'High lunar orbit', altitude: '500 km', coverage: 'Broader coverage, lower spatial detail', multiplier: 0.92, comm: 1.18 },
]

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
  const [selected, setSelected] = useState<string[]>(['camera', 'spectrometer', 'thermal'])
  const [orbit, setOrbit] = useState('low')
  const [launch, setLaunch] = useState('medium')
  const [budget, setBudget] = useState(180)
  const [showAll, setShowAll] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const [runState, setRunState] = useState<'idle' | 'complete'>('idle')

  const design = useMemo(() => {
    const chosen = instruments.filter(item => selected.includes(item.id))
    const mass = platform.mass + chosen.reduce((sum, item) => sum + item.mass, 0)
    const power = platform.power + chosen.reduce((sum, item) => sum + item.power, 0)
    const data = platform.data + chosen.reduce((sum, item) => sum + item.data, 0)
    const capacity = launch === 'small' ? 75 : launch === 'medium' ? 100 : 140
    const generation = 180
    const dailyDataAllowance = 24
    const link = orbitOptions.find(item => item.id === orbit)!
    const massPass = mass <= capacity
    const powerPass = power <= generation
    const dataPass = data <= dailyDataAllowance * link.comm
    const budgetPass = budget >= 120 + chosen.length * 12 + (launch === 'large' ? 35 : launch === 'medium' ? 20 : 0)
    const score = Math.max(0, Math.min(100, Math.round(
      chosen.reduce((sum, item) => sum + item.science, 0) * 0.9 +
      (massPass ? 12 : 0) + (powerPass ? 10 : 0) + (dataPass ? 8 : 0) +
      (budgetPass ? 8 : 0) + (chosen.length ? 5 : 0)
    )))
    return { chosen, mass, power, data, capacity, generation, dailyDataAllowance, massPass, powerPass, dataPass, budgetPass, score, link }
  }, [selected, orbit, launch, budget])

  const toggleInstrument = (id: string) => {
    setSelected(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id])
    setRunState('idle')
  }

  const navItems = ['Mission overview', 'Mission designer', 'Mission control', 'Mission report']
  const goTo = (item: string) => {
    setActiveNav(item)
    setMobileMenu(false)
    if (item === 'Mission designer') document.getElementById('designer')?.scrollIntoView({ behavior: 'smooth' })
    else if (item === 'Mission overview') window.scrollTo({ top: 0, behavior: 'smooth' })
    else document.getElementById('mission-output')?.scrollIntoView({ behavior: 'smooth' })
  }

  const checks = [
    { label: 'Launch mass capacity', ok: design.massPass, value: `${design.mass.toFixed(1)} / ${design.capacity} kg` },
    { label: 'Peak power budget', ok: design.powerPass, value: `${design.power} / ${design.generation} W` },
    { label: 'Daily data allowance', ok: design.dataPass, value: `${design.data.toFixed(1)} / ${(design.dailyDataAllowance * design.link.comm).toFixed(1)} GB/day` },
    { label: 'Development budget', ok: design.budgetPass, value: `$ ${budget}M allocated` },
  ]

  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><OrbitMark /></div><div><strong>ORBITOPS</strong><span>MISSION ENGINEERING</span></div><button className="icon-button mobile-close" onClick={() => setMobileMenu(false)} aria-label="Close menu"><X size={18}/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <div className="workspace-switch"><div className="workspace-avatar">LP</div><div><strong>Lunar Pathfinder</strong><span>Mission workspace</span></div><ChevronDown size={15}/></div>
      <div className="nav-label">MISSION</div>
      <nav className="side-nav">{navItems.map((item, index) => {
        const icons = [Globe2, SlidersHorizontal, Activity, Database]
        const Icon = icons[index]
        return <button key={item} className={activeNav === item ? 'nav-item active' : 'nav-item'} onClick={() => goTo(item)}><Icon size={17}/><span>{item}</span>{index === 2 && <span className="nav-live">LIVE</span>}</button>
      })}</nav>
      <div className="nav-label tools-label">TOOLS</div>
      <button className="nav-item" onClick={() => setShowAll(!showAll)}><Layers3 size={17}/><span>Component library</span><span className="nav-count">04</span></button>
      <button className="nav-item" onClick={() => goTo('Mission report')}><ShieldCheck size={17}/><span>Verification log</span></button>
      <div className="sidebar-bottom">
        <div className="help-card"><div className="help-icon"><CircleHelp size={17}/></div><strong>Need a hand?</strong><p>Explore the engineering guide to understand mission trade-offs.</p><button onClick={() => setShowAll(!showAll)}>Open learning guide <ArrowUpRight size={13}/></button></div>
        <div className="profile"><div className="profile-avatar">DK</div><div><strong>Mission designer</strong><span>Individual workspace</span></div><Settings2 size={16}/></div>
      </div>
    </aside>

    {mobileMenu && <button className="scrim" onClick={() => setMobileMenu(false)} aria-label="Close navigation"/>}
    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs"><button className="mobile-menu-button icon-button" onClick={() => setMobileMenu(true)} aria-label="Open menu"><Menu size={19}/></button><span>MISSIONS</span><span className="crumb-slash">/</span><strong>LUNAR PATHFINDER</strong></div>
        <div className="top-actions"><span className="autosave"><span className="status-dot"/> All changes saved</span><button className="team-button"><Users size={16}/> Invite team <span className="team-count">1/4</span></button><div className="top-avatar">DK</div></div>
      </header>

      <div className="content">
        <section className="page-heading">
          <div><div className="eyebrow"><span className="eyebrow-line"/> MISSION WORKSPACE <span className="eyebrow-tag">CONCEPT PHASE</span></div><h1>Mission overview<span className="heading-period">.</span></h1><p>Turn a scientific objective into an engineered mission concept.</p></div>
          <button className="primary-button" onClick={() => goTo('Mission designer')}><Rocket size={16}/> Configure spacecraft <ArrowUpRight size={15}/></button>
        </section>

        <section className="mission-hero">
          <div className="hero-copy">
            <div className="hero-kicker"><span className="hero-kicker-dot"/> ACTIVE MISSION CONCEPT <span className="hero-id">OP-LP-001</span></div>
            <h2>Lunar <em>Pathfinder</em></h2>
            <p>Investigate lunar polar terrain, characterize surface conditions, and identify regions of scientific interest for future exploration.</p>
            <div className="hero-tags"><span><Target size={13}/> Lunar science</span><span><Compass size={13}/> South polar region</span><span><Atom size={13}/> Orbiter concept</span></div>
            <button className="hero-link" onClick={() => goTo('Mission designer')}>Continue mission design <ArrowUpRight size={15}/></button>
          </div>
          <div className="moon-scene" aria-label="Illustration of the Moon and a spacecraft in orbit">
            <div className="orbit-ring orbit-one"/><div className="orbit-ring orbit-two"/><div className="moon"><div className="moon-crater crater-one"/><div className="moon-crater crater-two"/><div className="moon-crater crater-three"/><div className="moon-crater crater-four"/></div>
            <div className="satellite-art"><div className="sat-body"/><div className="sat-panel left"/><div className="sat-panel right"/><div className="sat-antenna"/></div>
            <div className="scene-label label-orbit"><span/> POLAR ORBIT</div><div className="scene-label label-altitude">100 KM <small>REFERENCE ALTITUDE</small></div>
            <div className="scene-coordinates">89.0° S <span>/</span> 0.0° E</div>
          </div>
          <div className="hero-footer"><span>MISSION STATUS <strong><i/> DESIGN IN PROGRESS</strong></span><span>LAST UPDATED <strong>JUST NOW</strong></span><span>TEAM SIZE <strong>01 / 04</strong></span></div>
        </section>

        <section className="section-block">
          <div className="section-heading"><div><div className="section-eyebrow">ENGINEERING SNAPSHOT</div><h3>Mission resources</h3></div><span className="section-note"><span className="status-dot"/> LIVE DESIGN ESTIMATE</span></div>
          <div className="metrics-grid">
            <Metric label="Spacecraft mass" value={design.mass.toFixed(1)} unit="kg" icon={Layers3} detail={`${Math.max(0, design.capacity - design.mass).toFixed(1)} kg capacity margin`} tone="blue"/>
            <Metric label="Peak power demand" value={String(design.power)} unit="W" icon={Zap} detail={`${design.generation - design.power} W generation margin`} tone="amber"/>
            <Metric label="Daily data load" value={design.data.toFixed(1)} unit="GB/day" icon={Database} detail={`${Math.max(0, design.dailyDataAllowance * design.link.comm - design.data).toFixed(1)} GB/day allowance remaining`} tone="violet"/>
            <Metric label="Science potential" value={String(design.chosen.reduce((sum, item) => sum + item.science, 0))} unit="pts" icon={Sparkles} detail="Relative concept-level index" tone="green"/>
          </div>
        </section>

        <section className="designer-layout" id="designer">
          <div className="designer-main">
            <div className="section-heading designer-heading"><div><div className="section-eyebrow">CONFIGURATION STUDIO</div><h3>Build your spacecraft</h3><p>Every payload choice changes the engineering budget.</p></div><span className="step-pill">STEP 02 <span>/ 05</span></span></div>
            <div className="panel instrument-panel">
              <div className="panel-header"><div className="panel-title-icon"><Telescope size={17}/></div><div><strong>Scientific payload</strong><span>Select instruments for your mission objectives</span></div><span className="selected-count">{selected.length} SELECTED</span></div>
              <div className="instrument-list">{instruments.map(item => {
                const checked = selected.includes(item.id)
                return <button key={item.id} className={`instrument-row ${checked ? 'instrument-selected' : ''}`} onClick={() => toggleInstrument(item.id)} aria-pressed={checked}>
                  <span className={`instrument-check ${checked ? 'checked' : ''}">{checked && <Check size={13}/>}</span>
                  <span className="instrument-symbol"><InstrumentSymbol id={item.id}/></span>
                  <span className="instrument-info"><strong>{item.name}</strong><small>{item.purpose}</small></span>
                  <span className="instrument-specs"><b>{item.mass} kg</b><small>{item.power} W</small></span>
                  <span className="instrument-science">+{item.science}<small>SCI</small></span>
                </button>
              })}</div>
              <div className="panel-footnote"><CircleHelp size={14}/> Payload characteristics are illustrative planning assumptions, not verified specifications of flight hardware.</div>
            </div>

            <div className="panel options-panel">
              <div className="panel-header"><div className="panel-title-icon orbit-icon"><Satellite size={17}/></div><div><strong>Orbit selection</strong><span>Choose an orbit concept for polar observations</span></div></div>
              <div className="orbit-options">{orbitOptions.map(item => <button key={item.id} className={orbit === item.id ? 'orbit-option chosen' : 'orbit-option'} onClick={() => { setOrbit(item.id); setRunState('idle') }}>
                <span className="orbit-radio">{orbit === item.id && <i/>}</span><span className="orbit-option-copy"><strong>{item.name}</strong><small>{item.coverage}</small></span><span className="orbit-altitude">{item.altitude}</span>
              </button>)}</div>
              <div className="panel-footnote"><CircleHelp size={14}/> Orbit options are conceptual presets. No trajectory propagation or contact-window computation is performed in this preview.</div>
            </div>
          </div>

          <aside className="designer-side">
            <div className="panel launch-panel">
              <div className="panel-header compact"><div className="panel-title-icon launch-icon"><Rocket size={16}/></div><div><strong>Launch vehicle class</strong><span>Conceptual payload capacity</span></div></div>
              <div className="launch-select-wrap"><select value={launch} onChange={event => { setLaunch(event.target.value); setRunState('idle') }} aria-label="Launch vehicle class"><option value="small">Small · 75 kg to reference orbit</option><option value="medium">Medium · 100 kg to reference orbit</option><option value="large">Heavy · 140 kg to reference orbit</option></select><ChevronDown size={15}/></div>
              <div className="launch-note">Capacity values are game-design assumptions, not specifications for a named launch vehicle.</div>
            </div>

            <div className="panel budget-panel">
              <div className="panel-header compact"><div className="panel-title-icon budget-icon"><Gauge size={16}/></div><div><strong>Mission budget</strong><span>Development allocation</span></div></div>
              <div className="budget-number"><strong>$ {budget}M</strong><span>USD · CONCEPT ESTIMATE</span></div>
              <input className="budget-slider" type="range" min="100" max="300" step="5" value={budget} onChange={event => { setBudget(Number(event.target.value)); setRunState('idle') }} aria-label="Mission budget in millions of dollars"/>
              <div className="slider-labels"><span>$100M</span><span>$300M</span></div>
              <div className="budget-warning"><Activity size={14}/> Budget feasibility uses a simplified planning rule.</div>
            </div>

            <div className="panel verification-panel" id="mission-output">
              <div className="verify-heading"><div><div className="section-eyebrow">DESIGN VALIDATION</div><strong>Constraint checks</strong></div><span className={checks.every(item => item.ok) ? 'pass-label' : 'warn-label'}>{checks.filter(item => item.ok).length}/{checks.length} PASS</span></div>
              <div className="check-list">{checks.map(item => <div className="check-row" key={item.label}><span className={item.ok ? 'check-status ok' : 'check-status fail'}>{item.ok ? <Check size={11}/> : <X size={11}/>}</span><span>{item.label}</span><b>{item.value}</b></div>)}</div>
              <div className="validation-divider"/>
              <div className="readiness"><span>DESIGN READINESS</span><strong>{checks.every(item => item.ok) ? 'Within preview limits' : 'Needs attention'}</strong></div>
              <button className="run-button" onClick={() => { setRunState('complete'); setActiveNav('Mission report') }}><Activity size={16}/> Run design assessment <ArrowUpRight size={15}/></button>
              {runState === 'complete' && <div className="run-result"><Check size={14}/> Assessment completed using the visible concept rules. This is not a flight-readiness review.</div>}
            </div>
          </aside>
        </section>

        <section className="bottom-grid">
          <div className="panel score-panel"><div className="bottom-panel-heading"><div><div className="section-eyebrow">MISSION PERFORMANCE</div><h3>Concept score</h3></div><span className="score-tag">PREVIEW MODEL</span></div><div className="score-content"><div className="score-ring" style={{ '--score': `${design.score * 3.6}deg` } as CSSProperties}><div><strong>{design.score}</strong><small>/ 100</small></div></div><div className="score-copy"><strong>{design.score >= 75 ? 'Promising configuration' : design.score >= 50 ? 'Room to optimize' : 'Needs redesign'}</strong><p>A relative learning score based on selected payload science points and the four visible constraint checks.</p><span><ArrowDownRight size={13}/> Not a NASA mission rating</span></div></div></div>
          <div className="panel next-panel"><div className="bottom-panel-heading"><div><div className="section-eyebrow">UP NEXT</div><h3>Mission milestones</h3></div><span className="milestone-count">02 / 05</span></div><div className="milestone-list"><div className="milestone done"><span><Check size={12}/></span><div><strong>Define science objectives</strong><small>Mission concept established</small></div><b>DONE</b></div><div className="milestone current"><span>02</span><div><strong>Configure spacecraft</strong><small>Payload and resource trade-offs</small></div><b>IN PROGRESS</b></div><div className="milestone"><span>03</span><div><strong>Verify mission architecture</strong><small>Requirements and interfaces</small></div><b>LOCKED</b></div></div></div>
        </section>

        <footer className="footer"><div><span className="footer-mark"><OrbitMark/></span><strong>ORBITOPS</strong><span>EDUCATIONAL MISSION DESIGN ENVIRONMENT</span></div><p>Independent educational project · Not affiliated with or endorsed by NASA.</p><p>Concept values shown are illustrative and are not flight-qualified engineering data.</p></footer>
      </div>
    </main>
    {showAll && <div className="guide-popover"><button className="guide-close" onClick={() => setShowAll(false)} aria-label="Close guide"><X size={16}/></button><div className="section-eyebrow">ENGINEERING NOTES</div><h3>How to read this workspace</h3><p><strong>Mass</strong> compares the platform and selected payload against the chosen illustrative launch-class capacity.</p><p><strong>Power</strong> compares a simple peak-load estimate with an assumed generation value. It is not an orbital eclipse or battery simulation.</p><p><strong>Data</strong> compares daily instrument output assumptions against a simplified daily downlink allowance adjusted by a conceptual orbit preset.</p><p><strong>Science points</strong> are relative game-design weights, not scientific measurement units.</p><p className="guide-source">This first website slice intentionally exposes its assumptions. NASA dataset ingestion, validated orbital propagation and detailed subsystem models are future engineering work.</p></div>}
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
