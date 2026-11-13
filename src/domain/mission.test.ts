import { describe, expect, it } from 'vitest'
import { calculateMissionDesign } from './mission'

const base = {
  selectedInstrumentIds: [] as string[],
  orbitId: 'low',
  launchClass: 'medium' as const,
  budgetMillions: 180,
}

describe('calculateMissionDesign', () => {
  it('returns platform-only resources when no payload is selected', () => {
    const result = calculateMissionDesign(base)
    expect(result.mass).toBe(42)
    expect(result.power).toBe(85)
    expect(result.data).toBe(0.35)
    expect(result.chosen).toHaveLength(0)
  })

  it('adds selected payload resources exactly once', () => {
    const result = calculateMissionDesign({
      ...base,
      selectedInstrumentIds: ['camera', 'thermal'],
    })
    expect(result.mass).toBeCloseTo(51.3)
    expect(result.power).toBe(125)
    expect(result.data).toBeCloseTo(3.35)
    expect(result.chosen).toHaveLength(2)
  })

  it('evaluates mass capacity against the selected launch class', () => {
    const small = calculateMissionDesign({
      ...base,
      selectedInstrumentIds: ['camera', 'spectrometer', 'radar', 'thermal'],
      launchClass: 'small',
    })
    expect(small.mass).toBeCloseTo(70.6)
    expect(small.capacity).toBe(75)
    expect(small.massPass).toBe(true)
  })

  it('uses the orbit preset data allowance factor', () => {
    const result = calculateMissionDesign({
      ...base,
      selectedInstrumentIds: ['camera'],
      orbitId: 'elliptical',
    })
    expect(result.dataPass).toBe(true)
    expect(result.dailyDataAllowance * result.link.comm).toBeCloseTo(19.68)
  })

  it('fails the budget check below the documented planning threshold', () => {
    const result = calculateMissionDesign({
      ...base,
      selectedInstrumentIds: ['camera', 'thermal'],
      budgetMillions: 143,
    })
    expect(result.requiredBudgetMillions).toBe(164)
    expect(result.budgetPass).toBe(false)
  })

  it('rejects unknown instrument, orbit, and invalid budget inputs', () => {
    expect(() => calculateMissionDesign({ ...base, selectedInstrumentIds: ['made-up'] })).toThrow(/Unknown instrument/)
    expect(() => calculateMissionDesign({ ...base, orbitId: 'mars' })).toThrow(/Unknown orbit/)
    expect(() => calculateMissionDesign({ ...base, budgetMillions: Number.NaN })).toThrow(/budgetMillions/)
  })

  it('keeps the relative score within its declared 0–100 range', () => {
    const result = calculateMissionDesign({
      ...base,
      selectedInstrumentIds: ['camera', 'spectrometer', 'radar', 'thermal'],
    })
    expect(result.score).toBeGreaterThanOrEqual(0)
    expect(result.score).toBeLessThanOrEqual(100)
  })
})
