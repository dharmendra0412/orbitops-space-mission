import { describe, expect, it } from 'vitest'
import {
  countCompletedMissionBriefFields,
  createEmptyMissionBrief,
  getMissingRequiredMissionBriefFields,
  missionBriefFields,
  parseMissionBriefDraft,
  serializeMissionBriefDraft,
} from './missionBrief'

describe('user-authored mission brief', () => {
  it('starts empty and does not invent mission assumptions', () => {
    const draft = createEmptyMissionBrief()
    expect(Object.values(draft).every((value) => value === '')).toBe(true)
    expect(countCompletedMissionBriefFields(draft)).toBe(0)
    expect(getMissingRequiredMissionBriefFields(draft)).toEqual([
      'Mission name',
      'Mission objective',
      'Target body / region',
    ])
  })

  it('counts only non-empty user-entered sections', () => {
    const draft = createEmptyMissionBrief()
    draft.missionName = 'Polar Survey'
    draft.objective = 'Map selected terrain using source-backed measurements.'
    draft.missionDuration = 'TBD'
    expect(countCompletedMissionBriefFields(draft)).toBe(3)
    expect(getMissingRequiredMissionBriefFields(draft)).toEqual(['Target body / region'])
  })

  it('serializes a clearly labelled user draft without claiming verification', () => {
    const draft = createEmptyMissionBrief()
    draft.missionName = 'Polar Survey'
    const parsed = JSON.parse(serializeMissionBriefDraft(draft, '2026-11-13T00:00:00Z'))
    expect(parsed.schema_version).toBe(1)
    expect(parsed.provenance).toMatch(/User-entered draft/)
    expect(parsed.brief.missionName).toBe('Polar Survey')
  })

  it('loads only known string fields and ignores malformed stored content', () => {
    const loaded = parseMissionBriefDraft(JSON.stringify({
      schema_version: 1,
      brief: { missionName: 'Saved draft', objective: 42, unknown: 'ignore me' },
    }))
    expect(loaded.missionName).toBe('Saved draft')
    expect(loaded.objective).toBe('')
    expect(Object.keys(loaded)).toHaveLength(9)
    expect(parseMissionBriefDraft('{invalid json')).toEqual(createEmptyMissionBrief())
  })

  it('defines unique field keys and requires explicit objective and target', () => {
    const keys = missionBriefFields.map((field) => field.key)
    expect(new Set(keys).size).toBe(keys.length)
    expect(missionBriefFields.filter((field) => field.required).map((field) => field.key))
      .toEqual(['missionName', 'objective', 'targetRegion'])
  })
})
