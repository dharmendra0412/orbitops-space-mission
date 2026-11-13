export type PdsProductSummary = {
  lidvid: string
  title?: string
}

export type PdsMemberRecord = {
  id: string
  title?: string
  type?: string
  start_date_time?: string
  stop_date_time?: string
}

export type PdsFileRecord = {
  role: 'label' | 'data'
  fileName?: string
  fileReference?: string
  sizeBytes?: string
  md5?: string
  mimeType?: string
}

export function extractPdsProducts(response: unknown): { hits?: number; products: PdsProductSummary[] } | null {
  if (Array.isArray(response) && response.length === 0) return { hits: 0, products: [] }
  if (!response || typeof response !== 'object' || !('data' in response) || !Array.isArray(response.data)) return null
  const summary = 'summary' in response && response.summary && typeof response.summary === 'object'
    ? response.summary as Record<string, unknown>
    : {}
  const products = response.data.flatMap((item): PdsProductSummary[] => {
    if (!item || typeof item !== 'object' || !('lidvid' in item) || typeof item.lidvid !== 'string') return []
    const row = item as Record<string, unknown>
    return [{
      lidvid: item.lidvid,
      title: typeof row.title === 'string' ? row.title : undefined,
    }]
  })
  return { hits: typeof summary.hits === 'number' ? summary.hits : undefined, products }
}

export function extractPdsMembers(response: unknown): PdsMemberRecord[] | null {
  const rows = Array.isArray(response)
    ? response
    : response && typeof response === 'object' && 'data' in response && Array.isArray(response.data)
      ? response.data
      : null
  if (!rows) return null

  return rows.flatMap((item): PdsMemberRecord[] => {
    if (!item || typeof item !== 'object') return []
    const row = item as Record<string, unknown>
    const id = typeof row.id === 'string' ? row.id : typeof row.lidvid === 'string' ? row.lidvid : null
    if (!id) return []
    return [{
      id,
      title: typeof row.title === 'string' ? row.title : undefined,
      type: typeof row.type === 'string' ? row.type : undefined,
      start_date_time: typeof row.start_date_time === 'string' ? row.start_date_time : undefined,
      stop_date_time: typeof row.stop_date_time === 'string' ? row.stop_date_time : undefined,
    }]
  })
}

export function mergePdsMembers(
  existing: PdsMemberRecord[],
  incoming: PdsMemberRecord[],
): PdsMemberRecord[] {
  const seen = new Set<string>()
  const merged: PdsMemberRecord[] = []
  for (const member of [...existing, ...incoming]) {
    if (seen.has(member.id)) continue
    seen.add(member.id)
    merged.push(member)
  }
  return merged
}

export function extractPdsFileManifest(response: unknown): PdsFileRecord[] {
  if (!response || typeof response !== 'object' || !('meta' in response) || !response.meta || typeof response.meta !== 'object') return []
  const meta = response.meta as Record<string, unknown>
  const result: PdsFileRecord[] = []

  const readFile = (value: unknown, role: 'label' | 'data'): PdsFileRecord | null => {
    if (!value || typeof value !== 'object') return null
    const file = value as Record<string, unknown>
    const get = (key: string) => typeof file[key] === 'string' || typeof file[key] === 'number' ? String(file[key]) : undefined
    return {
      role,
      fileName: get('ops:file_name'),
      fileReference: get('ops:file_ref'),
      sizeBytes: get('ops:file_size'),
      md5: get('ops:md5_checksum'),
      mimeType: get('ops:mime_type'),
    }
  }

  const label = readFile(meta['ops:Label_File_Info'], 'label')
  if (label) result.push(label)

  const dataFiles = meta['ops:Data_Files']
  if (Array.isArray(dataFiles)) {
    for (const item of dataFiles) {
      const file = readFile(item, 'data')
      if (file) result.push(file)
    }
  }
  return result
}
