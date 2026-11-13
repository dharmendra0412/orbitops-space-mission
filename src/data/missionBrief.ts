export type MissionBriefDraft = {
  missionName: string
  objective: string
  targetRegion: string
  missionDuration: string
  orbitConcept: string
  payloadRequirements: string
  spacecraftConstraints: string
  operationsConcept: string
  evidenceAndAssumptions: string
}

export type MissionBriefField = {
  key: keyof MissionBriefDraft
  label: string
  hint: string
  placeholder: string
  required?: boolean
  multiline?: boolean
}

export const missionBriefFields: MissionBriefField[] = [
  {
    key: 'missionName',
    label: 'Mission name',
    hint: 'A working title supplied by your team.',
    placeholder: 'Enter a mission name',
    required: true,
  },
  {
    key: 'objective',
    label: 'Mission objective',
    hint: 'Describe the scientific or exploration objective in your own words.',
    placeholder: 'What should the mission investigate or achieve?',
    required: true,
    multiline: true,
  },
  {
    key: 'targetRegion',
    label: 'Target body / region',
    hint: 'Specify the target and region. Do not assume coordinates that have not been sourced.',
    placeholder: 'e.g. Lunar south-polar region; exact site TBD',
    required: true,
  },
  {
    key: 'missionDuration',
    label: 'Mission duration',
    hint: 'User-supplied planning value only. Include units and whether it is an assumption.',
    placeholder: 'Not specified',
  },
  {
    key: 'orbitConcept',
    label: 'Orbit / trajectory concept',
    hint: 'Describe the intended concept; ORBITOPS does not propagate or simulate it.',
    placeholder: 'Describe the concept or leave as TBD',
    multiline: true,
  },
  {
    key: 'payloadRequirements',
    label: 'Payload / instrument requirements',
    hint: 'List desired measurements and link each to an authoritative instrument source where possible.',
    placeholder: 'Describe measurement needs; do not invent instrument performance.',
    multiline: true,
  },
  {
    key: 'spacecraftConstraints',
    label: 'Spacecraft constraints',
    hint: 'Enter only known or explicitly assumed values. Keep unknown mass, power, cost, and data volume blank.',
    placeholder: 'Record verified constraints or state what remains unknown.',
    multiline: true,
  },
  {
    key: 'operationsConcept',
    label: 'Operations concept',
    hint: 'Describe the intended operational sequence without claiming simulated timelines or contact windows.',
    placeholder: 'Describe mission phases and operations assumptions.',
    multiline: true,
  },
  {
    key: 'evidenceAndAssumptions',
    label: 'Evidence, source URLs, and assumptions',
    hint: 'Record source URLs, product identifiers, units, uncertainties, and all user-supplied assumptions.',
    placeholder: 'Paste source links and explain which inputs are verified versus assumed.',
    multiline: true,
  },
]

export function createEmptyMissionBrief(): MissionBriefDraft {
  return {
    missionName: '',
    objective: '',
    targetRegion: '',
    missionDuration: '',
    orbitConcept: '',
    payloadRequirements: '',
    spacecraftConstraints: '',
    operationsConcept: '',
    evidenceAndAssumptions: '',
  }
}

export function countCompletedMissionBriefFields(draft: MissionBriefDraft): number {
  return Object.values(draft).filter((value) => value.trim().length > 0).length
}

export function getMissingRequiredMissionBriefFields(draft: MissionBriefDraft): string[] {
  return missionBriefFields
    .filter((field) => field.required && !draft[field.key].trim())
    .map((field) => field.label)
}

export function parseMissionBriefDraft(raw: string | null): MissionBriefDraft {
  if (!raw) return createEmptyMissionBrief()
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return createEmptyMissionBrief()
    }
    const record = parsed as Record<string, unknown>
    const source = record.brief && typeof record.brief === 'object' && !Array.isArray(record.brief)
      ? record.brief as Record<string, unknown>
      : record
    const empty = createEmptyMissionBrief()
    return Object.fromEntries(
      Object.keys(empty).map((key) => [
        key,
        typeof source[key] === 'string' ? source[key] : '',
      ]),
    ) as MissionBriefDraft
  } catch {
    return createEmptyMissionBrief()
  }
}

export function serializeMissionBriefDraft(draft: MissionBriefDraft, savedAt: string): string {
  return JSON.stringify({
    schema_version: 1,
    saved_at: savedAt,
    provenance: 'User-entered draft; not verified engineering data.',
    brief: draft,
  }, null, 2)
}
