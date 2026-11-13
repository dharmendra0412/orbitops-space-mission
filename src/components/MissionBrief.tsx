import { type ChangeEvent, useEffect, useRef, useState } from 'react'
import { Download, FileText, Save, Trash2, Upload } from 'lucide-react'
import {
  countCompletedMissionBriefFields,
  createEmptyMissionBrief,
  getMissingRequiredMissionBriefFields,
  missionBriefFields,
  parseMissionBriefDraft,
  serializeMissionBriefDraft,
  type MissionBriefDraft,
  type MissionBriefTextKey,
  type MissionRequirement,
} from '../data/missionBrief'

const STORAGE_KEY = 'orbitops.mission-brief.v1'

export function MissionBrief() {
  const [draft, setDraft] = useState<MissionBriefDraft>(createEmptyMissionBrief)
  const [loaded, setLoaded] = useState(false)
  const [saveStatus, setSaveStatus] = useState('Loading this browser’s draft…')
  const importInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    try {
      setDraft(parseMissionBriefDraft(window.localStorage.getItem(STORAGE_KEY)))
      setSaveStatus('Draft loaded from this browser, if one exists.')
    } catch {
      setSaveStatus('Browser storage is unavailable. Export your draft to keep a copy.')
    } finally {
      setLoaded(true)
    }
  }, [])

  useEffect(() => {
    if (!loaded) return
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        serializeMissionBriefDraft(draft, new Date().toISOString()),
      )
      setSaveStatus('Automatically saved in this browser only.')
    } catch {
      setSaveStatus('Could not save locally. Export your draft to keep a copy.')
    }
  }, [draft, loaded])

  const updateField = (key: MissionBriefTextKey, value: string) => {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  const addRequirement = () => {
    setDraft((current) => {
      const nextNumber = current.requirements.reduce((max, row) => {
        const parsed = Number(row.id.replace(/^REQ-/, ''))
        return Number.isInteger(parsed) ? Math.max(max, parsed) : max
      }, 0) + 1
      const requirement: MissionRequirement = {
        id: 'REQ-' + String(nextNumber).padStart(3, '0'),
        statement: '',
        targetValue: '',
        sourceUrl: '',
        evidenceNote: '',
      }
      return { ...current, requirements: [...current.requirements, requirement] }
    })
  }

  const updateRequirement = (id: string, key: keyof Omit<MissionRequirement, 'id'>, value: string) => {
    setDraft((current) => ({
      ...current,
      requirements: current.requirements.map((row) => row.id === id ? { ...row, [key]: value } : row),
    }))
  }

  const removeRequirement = (id: string) => {
    setDraft((current) => ({
      ...current,
      requirements: current.requirements.filter((row) => row.id !== id),
    }))
  }

  const exportDraft = () => {
    const contents = serializeMissionBriefDraft(draft, new Date().toISOString())
    const blob = new Blob([contents], { type: 'application/json' })
    const objectUrl = URL.createObjectURL(blob)
    const filename = draft.missionName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'mission-brief'
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = filename + '.json'
    anchor.click()
    URL.revokeObjectURL(objectUrl)
  }

  const importDraft = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      if (file.size > 1_000_000) throw new Error('Mission brief JSON must be smaller than 1 MB.')
      const raw = await file.text()
      const parsed: unknown = JSON.parse(raw)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('The selected file is not a mission brief export.')
      }
      const record = parsed as Record<string, unknown>
      if (record.schema_version !== 1 || !record.brief || typeof record.brief !== 'object') {
        throw new Error('Unsupported mission brief export format.')
      }
      setDraft(parseMissionBriefDraft(raw))
      setSaveStatus('Mission brief imported and saved in this browser.')
    } catch (error) {
      setSaveStatus(error instanceof Error ? error.message : 'Unable to import this mission brief.')
    } finally {
      event.target.value = ''
    }
  }

  const clearDraft = () => {
    try {
      window.localStorage.removeItem(STORAGE_KEY)
    } catch {
      // The in-memory draft is still cleared when browser storage is unavailable.
    }
    setDraft(createEmptyMissionBrief())
    setSaveStatus('Draft cleared.')
  }

  const completed = countCompletedMissionBriefFields(draft)
  const missingRequired = getMissingRequiredMissionBriefFields(draft)

  return (
    <section className="section-block mission-brief-section" id="mission-brief">
      <div className="section-heading">
        <div>
          <div className="section-eyebrow">MISSION CONCEPT WORKSPACE</div>
          <h3>Build a traceable mission brief</h3>
          <p>Record your own mission concept and assumptions. No spacecraft data or mission results are pre-filled.</p>
        </div>
        <span className="section-note">USER-AUTHORED · NO SIMULATION</span>
      </div>

      <div className="mission-brief-panel">
        <div className="mission-brief-toolbar">
          <div className="mission-brief-status" role="status" aria-live="polite">
            <span className="mission-brief-status-icon"><Save size={14}/></span>
            <div><strong>{completed} / {missionBriefFields.length} sections filled</strong><small>{saveStatus}</small></div>
          </div>
          <div className="mission-brief-actions">
            <input ref={importInputRef} type="file" accept="application/json,.json" hidden onChange={(event) => void importDraft(event)} />
            <button type="button" onClick={() => importInputRef.current?.click()}><Upload size={14}/> Import JSON</button>
            <button type="button" onClick={exportDraft}><Download size={14}/> Export JSON</button>
            <button type="button" className="mission-brief-clear" onClick={clearDraft}><Trash2 size={14}/> Clear draft</button>
          </div>
        </div>

        <div className="mission-brief-fields">
          {missionBriefFields.map((field) => (
            <div className={field.multiline ? 'mission-brief-field mission-brief-field-wide' : 'mission-brief-field'} key={field.key}>
              <label htmlFor={'mission-brief-' + field.key}>
                {field.label}{field.required ? <span className="mission-required">Required</span> : <span className="mission-optional">Optional</span>}
              </label>
              {field.multiline ? (
                <textarea
                  id={'mission-brief-' + field.key}
                  rows={3}
                  required={field.required}
                  aria-required={field.required}
                  value={draft[field.key]}
                  placeholder={field.placeholder}
                  onChange={(event) => updateField(field.key, event.target.value)}
                />
              ) : (
                <input
                  id={'mission-brief-' + field.key}
                  type="text"
                  required={field.required}
                  aria-required={field.required}
                  value={draft[field.key]}
                  placeholder={field.placeholder}
                  onChange={(event) => updateField(field.key, event.target.value)}
                />
              )}
              <small>{field.hint}</small>
            </div>
          ))}
        </div>


        <div className="mission-requirements">
          <div className="mission-requirements-heading">
            <div><strong>Requirement traceability matrix</strong><small>{draft.requirements.length} user-authored requirements · source links are not independently validated</small></div>
            <button type="button" onClick={addRequirement}>+ Add requirement</button>
          </div>
          {draft.requirements.length === 0
            ? <p className="mission-requirements-empty">No requirements added yet. Add a requirement only when your team has a real objective or constraint to record.</p>
            : draft.requirements.map((row) => (
              <article className="mission-requirement-row" key={row.id}>
                <div className="mission-requirement-topline">
                  <strong>{row.id}</strong>
                  <span className={row.sourceUrl.trim() ? 'mission-source-linked' : 'mission-source-missing'}>
                    {row.sourceUrl.trim() ? 'URL entered · not fetched or validated' : 'No source linked'}
                  </span>
                  <button type="button" onClick={() => removeRequirement(row.id)} aria-label={'Remove ' + row.id}>Remove</button>
                </div>
                <label>Requirement statement
                  <textarea rows={2} value={row.statement} placeholder="Describe the requirement without inventing a threshold." onChange={(event) => updateRequirement(row.id, 'statement', event.target.value)}/>
                </label>
                <label>Target / threshold and units
                  <input type="text" value={row.targetValue} placeholder="Enter a sourced value or mark it TBD" onChange={(event) => updateRequirement(row.id, 'targetValue', event.target.value)}/>
                </label>
                <label>Source URL
                  <input type="url" value={row.sourceUrl} placeholder="https://…" onChange={(event) => updateRequirement(row.id, 'sourceUrl', event.target.value)}/>
                </label>
                <label>Evidence notes
                  <textarea rows={2} value={row.evidenceNote} placeholder="Record product ID, units, uncertainty, assumptions, and validation status." onChange={(event) => updateRequirement(row.id, 'evidenceNote', event.target.value)}/>
                </label>
              </article>
            ))}
        </div>

        <div className="mission-brief-validation">
          <FileText size={15}/>
          <div>
            {missingRequired.length === 0
              ? <strong>Required brief fields are filled. Engineering feasibility has not been assessed.</strong>
              : <strong>Still required: {missingRequired.join(', ')}</strong>}
            <p>All entries remain user-supplied planning notes. ORBITOPS does not validate feasibility, calculate trajectories, or infer missing mass, power, cost, data-volume, or performance values.</p>
          </div>
        </div>
      </div>
    </section>
  )
}
