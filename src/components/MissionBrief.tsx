import { useEffect, useState } from 'react'
import { Download, FileText, Save, Trash2 } from 'lucide-react'
import {
  countCompletedMissionBriefFields,
  createEmptyMissionBrief,
  getMissingRequiredMissionBriefFields,
  missionBriefFields,
  parseMissionBriefDraft,
  serializeMissionBriefDraft,
  type MissionBriefDraft,
} from '../data/missionBrief'

const STORAGE_KEY = 'orbitops.mission-brief.v1'

export function MissionBrief() {
  const [draft, setDraft] = useState<MissionBriefDraft>(createEmptyMissionBrief)
  const [loaded, setLoaded] = useState(false)
  const [saveStatus, setSaveStatus] = useState('Loading this browser’s draft…')

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

  const updateField = (key: keyof MissionBriefDraft, value: string) => {
    setDraft((current) => ({ ...current, [key]: value }))
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
          <div className="mission-brief-status">
            <span className="mission-brief-status-icon"><Save size={14}/></span>
            <div><strong>{completed} / {missionBriefFields.length} sections filled</strong><small>{saveStatus}</small></div>
          </div>
          <div className="mission-brief-actions">
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
                  value={draft[field.key]}
                  placeholder={field.placeholder}
                  onChange={(event) => updateField(field.key, event.target.value)}
                />
              ) : (
                <input
                  id={'mission-brief-' + field.key}
                  type="text"
                  value={draft[field.key]}
                  placeholder={field.placeholder}
                  onChange={(event) => updateField(field.key, event.target.value)}
                />
              )}
              <small>{field.hint}</small>
            </div>
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
