export type ResearchCategory = {
  id: string
  name: string
  purpose: string
}

export type OrbitArchitectureCategory = {
  id: string
  name: string
  coverage: string
}

// These are user-selectable research categories, not a hardware catalogue.
// No mass, power, data-rate, cost, or performance specifications are asserted.
export const instruments: ResearchCategory[] = [
  { id: 'camera', name: 'Terrain imaging', purpose: 'Research surface context, morphology, and site documentation' },
  { id: 'spectrometer', name: 'Near-infrared spectroscopy', purpose: 'Research mineral and volatile signatures in published observations' },
  { id: 'radar', name: 'Subsurface radar', purpose: 'Research subsurface structure products and instrument principles' },
  { id: 'thermal', name: 'Thermal radiometry', purpose: 'Research surface temperature and thermal-property datasets' },
]

// These are architecture labels only. No altitude or orbital mechanics values are supplied.
export const orbitOptions: OrbitArchitectureCategory[] = [
  { id: 'low', name: 'Low lunar orbit', coverage: 'Architecture category; numerical parameters not set' },
  { id: 'elliptical', name: 'Elliptical polar orbit', coverage: 'Architecture category; numerical parameters not set' },
  { id: 'high', name: 'High lunar orbit', coverage: 'Architecture category; numerical parameters not set' },
]
