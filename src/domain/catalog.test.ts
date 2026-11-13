import { describe, expect, it } from 'vitest'
import { instruments, orbitOptions } from './catalog'

describe('research category catalogue', () => {
  it('contains unique identifiers for each selectable category', () => {
    const ids = [...instruments, ...orbitOptions].map((item) => item.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('does not expose unsourced numeric engineering specifications', () => {
    for (const item of instruments) {
      expect(item).not.toHaveProperty('mass')
      expect(item).not.toHaveProperty('power')
      expect(item).not.toHaveProperty('data')
      expect(item).not.toHaveProperty('science')
    }
    for (const item of orbitOptions) {
      expect(item).not.toHaveProperty('altitude')
      expect(item).not.toHaveProperty('comm')
    }
  })
})
