export type Instrument = {
  id: string
  name: string
  purpose: string
  mass: number
  power: number
  data: number
  science: number
}

export type OrbitOption = {
  id: string
  name: string
  altitude: string
  coverage: string
  comm: number
}

export type LaunchClass = 'small' | 'medium' | 'large'

export const instruments: Instrument[] = [
  { id: 'camera', name: 'Terrain imaging camera', purpose: 'Context imaging and landing-site reconnaissance', mass: 4.2, power: 18, data: 1.8, science: 18 },
  { id: 'spectrometer', name: 'Near-infrared spectrometer', purpose: 'Surface mineral and volatile signatures', mass: 7.5, power: 32, data: 3.6, science: 28 },
  { id: 'radar', name: 'Subsurface radar sounder', purpose: 'Shallow subsurface structure investigation', mass: 11.8, power: 48, data: 5.2, science: 30 },
  { id: 'thermal', name: 'Thermal radiometer', purpose: 'Surface temperature observations', mass: 5.1, power: 22, data: 1.2, science: 20 },
]

export const orbitOptions: OrbitOption[] = [
  { id: 'low', name: 'Low lunar orbit', altitude: '100 km', coverage: 'High-resolution regional passes', comm: 1 },
  { id: 'elliptical', name: 'Elliptical polar orbit', altitude: '30 × 1,000 km', coverage: 'Long dwell near selected polar regions', comm: 0.82 },
  { id: 'high', name: 'High lunar orbit', altitude: '500 km', coverage: 'Broader coverage, lower spatial detail', comm: 1.18 },
]

const platform = { mass: 42, power: 85, data: 0.35 }
const launchCapacities: Record<LaunchClass, number> = { small: 75, medium: 100, large: 140 }

export type MissionDesignInput = {
  selectedInstrumentIds: string[]
  orbitId: string
  launchClass: LaunchClass
  budgetMillions: number
}

export type MissionDesignResult = {
  chosen: Instrument[]
  mass: number
  power: number
  data: number
  capacity: number
  generation: number
  dailyDataAllowance: number
  massPass: boolean
  powerPass: boolean
  dataPass: boolean
  budgetPass: boolean
  score: number
  link: OrbitOption
  requiredBudgetMillions: number
}

export function calculateMissionDesign(input: MissionDesignInput): MissionDesignResult {
  if (!Number.isFinite(input.budgetMillions) || input.budgetMillions < 0) {
    throw new RangeError('budgetMillions must be a finite, non-negative number')
  }

  const link = orbitOptions.find((option) => option.id === input.orbitId)
  if (!link) throw new RangeError(`Unknown orbit preset: ${input.orbitId}`)
  if (!(input.launchClass in launchCapacities)) {
    throw new RangeError(`Unknown launch class: ${input.launchClass}`)
  }

  const selectedIds = new Set(input.selectedInstrumentIds)
  const chosen = instruments.filter((instrument) => selectedIds.has(instrument.id))
  const unknownIds = [...selectedIds].filter((id) => !instruments.some((instrument) => instrument.id === id))
  if (unknownIds.length > 0) throw new RangeError(`Unknown instrument id(s): ${unknownIds.join(', ')}`)

  const mass = platform.mass + chosen.reduce((sum, item) => sum + item.mass, 0)
  const power = platform.power + chosen.reduce((sum, item) => sum + item.power, 0)
  const data = platform.data + chosen.reduce((sum, item) => sum + item.data, 0)
  const capacity = launchCapacities[input.launchClass]
  const generation = 180
  const dailyDataAllowance = 24
  const requiredBudgetMillions = 120 + chosen.length * 12 + (input.launchClass === 'large' ? 35 : input.launchClass === 'medium' ? 20 : 0)
  const massPass = mass <= capacity
  const powerPass = power <= generation
  const dataPass = data <= dailyDataAllowance * link.comm
  const budgetPass = input.budgetMillions >= requiredBudgetMillions
  const sciencePoints = chosen.reduce((sum, item) => sum + item.science, 0)
  const score = Math.max(0, Math.min(100, Math.round(
    sciencePoints * 0.9 + (massPass ? 12 : 0) + (powerPass ? 10 : 0) +
    (dataPass ? 8 : 0) + (budgetPass ? 8 : 0) + (chosen.length ? 5 : 0),
  )))

  return {
    chosen, mass, power, data, capacity, generation, dailyDataAllowance,
    massPass, powerPass, dataPass, budgetPass, score, link, requiredBudgetMillions,
  }
}
