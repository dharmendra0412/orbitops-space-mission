import { describe, expect, it } from 'vitest'
import { lolaPixelToLatLon, LolaProjectionError } from './lolaProjection'

const metadata: Record<string, string> = {
  LINES: '7584',
  LINE_SAMPLES: '7584',
  MAP_PROJECTION_TYPE: 'POLAR STEREOGRAPHIC',
  KEYWORD_LATITUDE_TYPE: 'PLANETOCENTRIC',
  POSITIVE_LONGITUDE_DIRECTION: 'EAST',
  COORDINATE_SYSTEM_NAME: 'MEAN EARTH/POLAR AXIS OF DE421',
  CENTER_LATITUDE: '-90 <deg>',
  CENTER_LONGITUDE: '0 <deg>',
  MAP_PROJECTION_ROTATION: '0.0',
  A_AXIS_RADIUS: '1737.4 <km>',
  B_AXIS_RADIUS: '1737.4 <km>',
  C_AXIS_RADIUS: '1737.4 <km>',
  MAP_SCALE: '40 <m/pix>',
  LINE_PROJECTION_OFFSET: '3791.5 <pix>',
  SAMPLE_PROJECTION_OFFSET: '3791.5 <pix>',
}

describe('LOLA source-label pixel geolocation', () => {
  it.each([
    [3791, 3791, 315],
    [3791, 3792, 45],
    [3792, 3792, 135],
    [3792, 3791, 225],
  ])('matches the PDS south-polar quadrant at line %i, sample %i', (line, sample, longitude) => {
    const result = lolaPixelToLatLon(metadata, line, sample)
    expect(result.latitudeDegrees).toBeCloseTo(-89.9990672445, 9)
    expect(result.eastLongitudeDegrees).toBe(longitude)
  })

  it('uses source pixel-center offsets and map scale for projected coordinates', () => {
    const result = lolaPixelToLatLon(metadata, 3791, 3791)
    expect(result.xMapMeters).toBe(-20)
    expect(result.yMapMeters).toBe(20)
  })

  it('rejects fractional pixel indices', () => {
    expect(() => lolaPixelToLatLon(metadata, 3791.5, 3791))
      .toThrow(LolaProjectionError)
  })

  it('rejects out-of-bounds indices', () => {
    expect(() => lolaPixelToLatLon(metadata, 7584, 0))
      .toThrow(/outside the image bounds/)
  })

  it('rejects non-positive map scale', () => {
    expect(() => lolaPixelToLatLon({ ...metadata, MAP_SCALE: '0 <m/pix>' }, 3791, 3791))
      .toThrow(/map scale must be positive/)
  })

  it('rejects non-finite projection metadata', () => {
    expect(() => lolaPixelToLatLon({ ...metadata, MAP_SCALE: '1e999 <m/pix>' }, 3791, 3791))
      .toThrow(/must be finite/)
  })

  it('rejects an unexpected reference frame', () => {
    expect(() => lolaPixelToLatLon({ ...metadata, COORDINATE_SYSTEM_NAME: 'UNKNOWN' }, 3791, 3791))
      .toThrow(/coordinate reference frame/)
  })
})
