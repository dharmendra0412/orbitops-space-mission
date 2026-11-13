export type LolaProjectionResult = {
  latitudeDegrees: number
  eastLongitudeDegrees: number
  xMapMeters: number
  yMapMeters: number
}

export class LolaProjectionError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'LolaProjectionError'
  }
}

function numericField(
  metadata: Record<string, string>,
  key: string,
  unit?: string,
): number {
  const raw = metadata[key]
  const match = raw?.match(/^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)\s*(?:<([^>]+)>)?\s*$/)
  if (!match || (unit !== undefined && match[2] !== unit)) {
    throw new LolaProjectionError(`PDS label field ${key} is missing or has an unsupported value/unit`)
  }
  const value = Number(match[1])
  if (!Number.isFinite(value)) {
    throw new LolaProjectionError(`PDS label field ${key} must be finite`)
  }
  return value
}

function positiveIntegerField(metadata: Record<string, string>, key: string): number {
  const raw = metadata[key]
  if (!raw || !/^\d+$/.test(raw) || Number(raw) <= 0) {
    throw new LolaProjectionError(`PDS label field ${key} must be a positive integer`)
  }
  return Number(raw)
}

/**
 * Convert zero-based PDS LOLA GDR line/sample indices to planetocentric
 * latitude and east longitude using the source label's DSMAP_POLAR metadata.
 * This locates a grid cell only; it does not read or return its raster value.
 */
export function lolaPixelToLatLon(
  metadata: Record<string, string>,
  lineIndex: number,
  sampleIndex: number,
): LolaProjectionResult {
  const lines = positiveIntegerField(metadata, 'LINES')
  const samples = positiveIntegerField(metadata, 'LINE_SAMPLES')

  if (!Number.isInteger(lineIndex) || !Number.isInteger(sampleIndex)) {
    throw new LolaProjectionError('Pixel indices must be integers')
  }
  if (lineIndex < 0 || lineIndex >= lines || sampleIndex < 0 || sampleIndex >= samples) {
    throw new LolaProjectionError('Pixel index is outside the image bounds')
  }

  if (metadata.MAP_PROJECTION_TYPE !== 'POLAR STEREOGRAPHIC') {
    throw new LolaProjectionError('Unsupported LOLA map projection')
  }
  if (metadata.KEYWORD_LATITUDE_TYPE !== 'PLANETOCENTRIC') {
    throw new LolaProjectionError('LOLA projection requires planetocentric latitude')
  }
  if (metadata.POSITIVE_LONGITUDE_DIRECTION !== 'EAST') {
    throw new LolaProjectionError('LOLA projection requires east-positive longitude')
  }
  if (metadata.COORDINATE_SYSTEM_NAME !== 'MEAN EARTH/POLAR AXIS OF DE421') {
    throw new LolaProjectionError('Unexpected LOLA coordinate reference frame')
  }
  if (numericField(metadata, 'CENTER_LATITUDE', 'deg') !== -90) {
    throw new LolaProjectionError('Selected product is not centered on the lunar south pole')
  }
  if (numericField(metadata, 'CENTER_LONGITUDE', 'deg') !== 0) {
    throw new LolaProjectionError('Unexpected LOLA polar projection center longitude')
  }
  if (numericField(metadata, 'MAP_PROJECTION_ROTATION') !== 0) {
    throw new LolaProjectionError('Rotated LOLA polar projections are not supported')
  }

  const radii = ['A_AXIS_RADIUS', 'B_AXIS_RADIUS', 'C_AXIS_RADIUS']
    .map((key) => numericField(metadata, key, 'km') * 1000)
  if (radii.some((radius) => Math.abs(radius - 1_737_400) > 1e-6)) {
    throw new LolaProjectionError('LOLA projection axes do not match the catalog 1737.4 km sphere')
  }

  const mapScale = numericField(metadata, 'MAP_SCALE', 'm/pix')
  if (mapScale <= 0) {
    throw new LolaProjectionError('LOLA map scale must be positive')
  }
  const lineOffset = numericField(metadata, 'LINE_PROJECTION_OFFSET', 'pix')
  const sampleOffset = numericField(metadata, 'SAMPLE_PROJECTION_OFFSET', 'pix')
  const expectedOffset = lines / 2 - 0.5
  if (Math.abs(lineOffset - expectedOffset) > 1e-9 || Math.abs(sampleOffset - expectedOffset) > 1e-9) {
    throw new LolaProjectionError('Projection offsets do not match the PDS pixel-center convention')
  }

  const xMapMeters = (sampleIndex - sampleOffset) * mapScale
  const yMapMeters = (lineIndex - lineOffset) * mapScale * -1
  const radialDistance = Math.hypot(xMapMeters, yMapMeters)
  const latitudeDegrees = -90 + (2 * Math.atan(0.5 * radialDistance / 1_737_400) * 180 / Math.PI)
  const eastLongitudeDegrees = ((Math.atan2(xMapMeters, yMapMeters) * 180 / Math.PI) + 360) % 360

  return { latitudeDegrees, eastLongitudeDegrees, xMapMeters, yMapMeters }
}
