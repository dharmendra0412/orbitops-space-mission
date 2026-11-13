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


  it('includes separate Kaguya altimetry and documents LOLA control limitations', () => {
    const lalt = missionResources.find((resource) => resource.id === 'kaguya-lalt-calibrated')
    const laltDarts = missionResources.find((resource) => resource.id === 'kaguya-lalt-range-darts')
    const lgtTimeseries = missionResources.find((resource) => resource.id === 'kaguya-lalt-lgt-timeseries')
    const southPole = missionResources.find((resource) => resource.id === 'kaguya-lalt-south-pole')
    const usgs = missionResources.find((resource) => resource.id === 'usgs-lroc-south-pole-vv')
    const laltFormat = missionResources.find((resource) => resource.id === 'kaguya-lalt-pds3-format')
    const laltGrid = missionResources.find((resource) => resource.id === 'kaguya-lalt-pds3-dataset')
    const kaguyaSpice = missionResources.find((resource) => resource.id === 'kaguya-spice-kernels')
    expect(lalt?.url).toContain('/LALT/Calibrated_Data.htm')
    expect(lalt?.description).toMatch(/orbit provenance/i)
    expect(lalt?.description).toMatch(/internal spacecraft-clock TI tags/i)
    expect(lalt?.description).toMatch(/do not contain latitude\/longitude/i)
    expect(lalt?.description).toContain('SLN-L-LALT-3-RANGE-V1.0')
    expect(laltDarts?.url).toContain('sln-l-lalt-3-range-v1.0')
    expect(lgtTimeseries?.url).toContain('sln-l-lalt-4-topo-lgt-ts-v2.0')
    expect(lgtTimeseries?.description).toMatch(/NAOJ_RISE_MAIN_ORBIT_SGM100g/)
    expect(lgtTimeseries?.description).toMatch(/only after the orbit kernel and frame provenance are verified/i)
    expect(southPole?.description).toMatch(/LALT_SP/)
    expect(southPole?.description).toMatch(/void cells are encoded as -99/i)
    expect(laltFormat?.description).toMatch(/1\/128° latitude and 1\/32° longitude/)
    expect(laltFormat?.url).toContain('LALT_Format_en_V01.pdf')
    expect(laltGrid?.url).toContain('sln-l-lalt-5-topo-gt-sp-img-v2.0')
    expect(laltGrid?.description).toMatch(/interpolated from LALT global topographic time-series/i)
    expect(kaguyaSpice?.url).toContain('sln-l-spice-6-v1.0')
    expect(kaguyaSpice?.description).toMatch(/Neither is automatically the exact SGM100g orbit/i)
    expect(usgs?.description).toMatch(/not independent absolute geodetic truth/i)
  })
