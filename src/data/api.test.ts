import { describe, expect, it } from 'vitest'
import { apiUrl } from './api'

describe('API URL configuration', () => {
  it('normalizes API paths to a leading slash', () => {
    expect(apiUrl('api/v1/pds/search')).toBe('/api/v1/pds/search')
    expect(apiUrl('/api/v1/pds/search')).toBe('/api/v1/pds/search')
  })

  it('preserves query strings when building API paths', () => {
    expect(apiUrl('/api/v1/pds/search?keywords=LOLA&limit=10'))
      .toBe('/api/v1/pds/search?keywords=LOLA&limit=10')
  })
})
