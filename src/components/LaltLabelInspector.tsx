import { useState } from 'react'
import { Database, ExternalLink } from 'lucide-react'

type LaltLabelResponse = {
  source: string
  source_url: string
  retrieved_at: string
  product_file: string
  metadata: {
    dataset_id: string
    product_id: string
    lines: number
    line_samples: number
    sample_type: string
    sample_bits: number
    image_bytes: number
    dummy_value_km: number
    height_unit: string
    reference_sphere_radius_km: number
    coordinate_system: string
    coordinate_system_type: string
    map_projection_type: string
    maximum_latitude_degrees: number
    minimum_latitude_degrees: number
    westernmost_longitude_degrees: number
    easternmost_longitude_degrees: number
    latitude_pixels_per_degree: number
    longitude_pixels_per_degree: number
  }
  validation_scope: string
}

export function LaltLabelInspector() {
  const [result, setResult] = useState<LaltLabelResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const fetchLabel = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const response = await fetch('/api/v1/pds3/kaguya/lalt/gt-sp/label')
      const payload: unknown = await response.json()
      if (!response.ok) {
        const detail = payload && typeof payload === 'object' && 'detail' in payload
          ? (payload as { detail?: unknown }).detail
          : undefined
        throw new Error(typeof detail === 'string' ? detail : 'JAXA LALT label request failed (HTTP ' + response.status + ').')
      }
      if (!payload || typeof payload !== 'object' || !('metadata' in payload)) {
        throw new Error('JAXA LALT endpoint returned an unexpected label response.')
      }
      setResult(payload as LaltLabelResponse)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to retrieve the JAXA LALT PDS3 label.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel pds-search-panel lalt-source-panel">
      <div className="pds-search-heading">
        <div><strong>Kaguya SELENE LALT south-polar grid</strong><span>Inspect the original JAXA PDS3 label and product layout</span></div>
        <span className="resource-kind">LIVE JAXA METADATA</span>
      </div>
      <p className="pds-search-note">
        The 11,520 × 1,408 PC_REAL image is an interpolated topographic grid derived from LALT_LGT_TS, not raw laser-shot data.
        JAXA DARTS did not return HTTP 206 for a bounded four-byte sample request during source validation. ORBITOPS therefore
        does not expose a live pixel lookup or download the full 64.9 MB image for individual clicks.
      </p>
      <button className="run-button lola-pixel-button" type="button" onClick={() => void fetchLabel()} disabled={loading}>
        <Database size={15}/>{loading ? 'Fetching JAXA PDS3 label…' : 'Fetch original Kaguya LALT label'}
      </button>
      {error && <p className="pds-search-error" role="alert">{error}</p>}
      {result && <div className="pds-results">
        <div className="pds-results-meta">
          <span>{result.source} · PDS3</span>
          <span>Retrieved {new Date(result.retrieved_at).toLocaleString()}</span>
        </div>
        <div className="lola-coordinate-result lola-pixel-result" aria-live="polite">
          <div><span>Dataset ID</span><strong>{result.metadata.dataset_id}</strong></div>
          <div><span>Product ID</span><strong>{result.metadata.product_id}</strong></div>
          <div><span>Image dimensions</span><strong>{result.metadata.lines} × {result.metadata.line_samples}</strong></div>
          <div><span>Image size</span><strong>{result.metadata.image_bytes.toLocaleString()} bytes</strong></div>
          <div><span>Sample format</span><strong>{result.metadata.sample_type} · {result.metadata.sample_bits}-bit</strong></div>
          <div><span>Dummy / no-data value</span><strong>{result.metadata.dummy_value_km} km</strong></div>
          <div><span>Reference sphere</span><strong>{result.metadata.reference_sphere_radius_km.toFixed(1)} km</strong></div>
          <div><span>Latitude coverage</span><strong>{result.metadata.maximum_latitude_degrees}° to {result.metadata.minimum_latitude_degrees}°</strong></div>
          <div><span>Grid spacing</span><strong>1/{result.metadata.latitude_pixels_per_degree}° lat · 1/{result.metadata.longitude_pixels_per_degree}° lon</strong></div>
          <div><span>Coordinate frame</span><strong>{result.metadata.coordinate_system}</strong></div>
          <div className="lola-pixel-provenance">
            <a href={result.source_url} target="_blank" rel="noopener noreferrer">Original detached PDS3 label <ExternalLink size={11}/></a>
            <a href="https://darts.isas.jaxa.jp/en/datasets/darts:sln-l-lalt-5-topo-gt-sp-img-v2.0" target="_blank" rel="noopener noreferrer">Official DARTS dataset record <ExternalLink size={11}/></a>
            <a href="https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-lalt-5-topo-gt-sp-img-v2.0/data/LALT_GT_SP_IMG.IMG" target="_blank" rel="noopener noreferrer">Open original 64.9 MB image (manual download) <ExternalLink size={11}/></a>
            <a href="https://www.isas.jaxa.jp/en/researchers/data-policy/" target="_blank" rel="noopener noreferrer">JAXA data-use policy <ExternalLink size={11}/></a>
            <small>{result.validation_scope}</small>
          </div>
        </div>
      </div>}
    </div>
  )
}
