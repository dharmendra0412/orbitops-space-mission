import { useState } from 'react'
import { Database, ExternalLink } from 'lucide-react'

type LaltPixelResponse = {
  source: string
  source_url: string
  label_source_url: string
  retrieved_at: string
  dataset_id: string
  product_id: string
  line_index: number
  sample_index: number
  byte_range_inclusive: { start: number; end: number }
  raw_sample_bytes_hex: string
  elevation_km: number | null
  elevation_m: number | null
  is_dummy: boolean
  planetocentric_latitude_degrees: number
  east_longitude_degrees: number
  coordinate_reference: string
  reference_sphere_radius_km: number
  validation_scope: string
}

export function LaltPixelInspector() {
  const [lineIndex, setLineIndex] = useState('')
  const [sampleIndex, setSampleIndex] = useState('')
  const [result, setResult] = useState<LaltPixelResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const fetchSample = async () => {
    const line = Number(lineIndex)
    const sample = Number(sampleIndex)
    if (!lineIndex.trim() || !sampleIndex.trim() ||
        !Number.isInteger(line) || !Number.isInteger(sample) ||
        line < 0 || line > 1407 || sample < 0 || sample > 11519) {
      setError('Enter integer zero-based indices within 1,408 lines and 11,520 samples.')
      setResult(null)
      return
    }

    setLoading(true)
    setError('')
    setResult(null)
    try {
      const params = new URLSearchParams({ line_index: String(line), sample_index: String(sample) })
      const response = await fetch('/api/v1/pds3/kaguya/lalt/gt-sp/pixel?' + params.toString())
      const payload: unknown = await response.json()
      if (!response.ok) {
        const detail = payload && typeof payload === 'object' && 'detail' in payload
          ? (payload as { detail?: unknown }).detail
          : undefined
        throw new Error(typeof detail === 'string' ? detail : 'JAXA LALT request failed (HTTP ' + response.status + ').')
      }
      if (!payload || typeof payload !== 'object' || !('elevation_km' in payload)) {
        throw new Error('JAXA LALT endpoint returned an unexpected response.')
      }
      setResult(payload as LaltPixelResponse)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to retrieve the JAXA LALT grid sample.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel pds-search-panel lalt-source-panel">
      <div className="pds-search-heading">
        <div><strong>Kaguya SELENE LALT south-polar grid</strong><span>Inspect an actual sample from the JAXA PDS3 interpolated topography product</span></div>
        <span className="resource-kind">LIVE JAXA DATA</span>
      </div>
      <p className="pds-search-note">
        This 11,520 × 1,408 PC_REAL grid is derived from LALT_LGT_TS by spherical interpolation; it is not raw laser-shot data.
        Each request retrieves the source label and exactly four bytes from the fixed DARTS image URL. Values are heights in
        kilometres above the label's 1,737.4 km reference sphere. This product is not independent geodetic ground truth.
      </p>
      <div className="lola-coordinate-fields">
        <label>Line index (0–1407)
          <input type="number" min="0" max="1407" step="1" value={lineIndex} disabled={loading}
            onChange={(event) => { setLineIndex(event.target.value); setResult(null); setError('') }}/>
        </label>
        <label>Sample index (0–11519)
          <input type="number" min="0" max="11519" step="1" value={sampleIndex} disabled={loading}
            onChange={(event) => { setSampleIndex(event.target.value); setResult(null); setError('') }}/>
        </label>
      </div>
      <button className="run-button lola-pixel-button" type="button" onClick={() => void fetchSample()}
        disabled={loading || !lineIndex.trim() || !sampleIndex.trim()}>
        <Database size={15}/>{loading ? 'Reading four source bytes…' : 'Fetch actual Kaguya LALT grid sample'}
      </button>
      {error && <p className="pds-search-error" role="alert">{error}</p>}
      {result && <div className="lola-coordinate-result lola-pixel-result" aria-live="polite">
        <div><span>Grid elevation</span><strong>{result.is_dummy ? 'No data (source dummy)' : result.elevation_km?.toFixed(3) + ' km'}</strong></div>
        <div><span>Elevation converted</span><strong>{result.is_dummy ? 'Unavailable' : result.elevation_m?.toFixed(1) + ' m'}</strong></div>
        <div><span>Planetocentric latitude</span><strong>{result.planetocentric_latitude_degrees.toFixed(8)}°</strong></div>
        <div><span>East longitude</span><strong>{result.east_longitude_degrees.toFixed(8)}°</strong></div>
        <div><span>Original four bytes (hex)</span><strong>{result.raw_sample_bytes_hex}</strong></div>
        <div><span>Source byte range</span><strong>{result.byte_range_inclusive.start}–{result.byte_range_inclusive.end}</strong></div>
        <div className="lola-pixel-provenance">
          <span>Retrieved {new Date(result.retrieved_at).toLocaleString()} · {result.coordinate_reference}</span>
          <a href={result.source_url} target="_blank" rel="noopener noreferrer">Original JAXA DARTS raster <ExternalLink size={11}/></a>
          <small>{result.validation_scope}</small>
        </div>
      </div>}
    </div>
  )
}
