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

  it('includes the authoritative LOLA GDR conversion and projection references', () => {
    const sis = missionResources.find((resource) => resource.id === 'lola-rdr-sis')
    const projection = missionResources.find((resource) => resource.id === 'lola-polar-projection')
    const jp2 = missionResources.find((resource) => resource.id === 'lola-jp2-format')
    expect(sis?.url).toContain('/document/rdrsis.htm')
    expect(projection?.url).toContain('/catalog/dsmap_polar.cat')
    expect(jp2?.url).toContain('/document/jp2info.txt')
  })

  it('does not describe reference-only tools as integrated data feeds', () => {
    const missionViz = missionResources.find((resource) => resource.id === 'mission-viz')
    const gmat = missionResources.find((resource) => resource.id === 'gmat')
    expect(missionViz?.description).toMatch(/does not claim to embed/i)
    expect(gmat?.description).toMatch(/does not run/i)
  })
})
