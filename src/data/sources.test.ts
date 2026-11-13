import { describe, expect, it } from 'vitest'
import { missionResources } from './sources'

describe('mission resource catalogue', () => {
  it('uses unique stable identifiers', () => {
    const ids = missionResources.map((resource) => resource.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('links only to explicit HTTPS source pages', () => {
    for (const resource of missionResources) {
      expect(() => new URL(resource.url)).not.toThrow()
      expect(new URL(resource.url).protocol).toBe('https:')
      expect(resource.title.length).toBeGreaterThan(0)
      expect(resource.description.length).toBeGreaterThan(20)
    }
  })

  it('does not describe reference-only tools as integrated data feeds', () => {
    const missionViz = missionResources.find((resource) => resource.id === 'mission-viz')
    const gmat = missionResources.find((resource) => resource.id === 'gmat')
    expect(missionViz?.description).toMatch(/does not claim to embed/i)
    expect(gmat?.description).toMatch(/does not run/i)
  })
})
