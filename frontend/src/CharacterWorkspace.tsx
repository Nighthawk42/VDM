import { useEffect, useState, type FormEvent } from 'react'
import { api, type Ability, type Character, type CharacterSheet, type Event, type Room, type User } from './api'

const abilities: Ability[] = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
const extraKeys = new Set(['abilities', 'skills', 'notes'])

function extrasFor(sheet: CharacterSheet): string {
  return JSON.stringify(Object.fromEntries(Object.entries(sheet).filter(([key]) => !extraKeys.has(key))), null, 2)
}

function signed(value: number): string { return value >= 0 ? `+${value}` : `${value}` }
function modifier(score: number): number { return Math.floor((score - 10) / 2) }

export function CharacterWorkspace({ room, user, onRoll }: {
  room: Room; user: User; onRoll: (event: Event) => void
}) {
  const [characters, setCharacters] = useState<Character[]>([])
  const [draft, setDraft] = useState<Character | null>(null)
  const [extras, setExtras] = useState('{}')
  const [newName, setNewName] = useState('')
  const [newSkill, setNewSkill] = useState('')
  const [dc, setDc] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const isGM = ['host', 'lead_gm', 'co_gm'].includes(room.role)
  const selected = characters.find(character => character.id === draft?.id)
  const canEdit = !!draft && room.role !== 'spectator' && (draft.owner_id === user.id || isGM)
  const dirty = !!draft && !!selected && (
    draft.name !== selected.name || JSON.stringify(draft.sheet) !== JSON.stringify(selected.sheet) ||
    extras !== extrasFor(selected.sheet)
  )

  useEffect(() => {
    let active = true
    api.characters(room.id).then(items => {
      if (!active) return
      setCharacters(items)
      if (items.length) { setDraft(items[0]); setExtras(extrasFor(items[0].sheet)) }
    }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Could not load characters.') })
    return () => { active = false }
  }, [room.id])

  function choose(character: Character) {
    if (dirty && !window.confirm('Discard unsaved character changes?')) return
    setDraft(character); setExtras(extrasFor(character.sheet)); setError(''); setMessage('')
  }

  function changeSheet(patch: Partial<CharacterSheet>) {
    setDraft(current => current ? { ...current, sheet: { ...current.sheet, ...patch } } : current)
  }

  async function create(event: FormEvent) {
    event.preventDefault()
    if (!newName.trim()) return
    if (dirty && !window.confirm('Discard unsaved character changes?')) return
    setBusy(true); setError(''); setMessage('')
    try {
      const created = await api.createCharacter(room.id, newName.trim())
      setCharacters(existing => [...existing, created])
      setDraft(created); setExtras(extrasFor(created.sheet)); setNewName('')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create character.') }
    finally { setBusy(false) }
  }

  async function save() {
    if (!draft) return
    setBusy(true); setError(''); setMessage('')
    try {
      const parsed: unknown = JSON.parse(extras)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Extra data must be a JSON object.')
      if (Object.keys(parsed).some(key => extraKeys.has(key))) throw new Error('Edit abilities, skills, and notes in their fields above.')
      const sheet = { ...draft.sheet, ...parsed as Record<string, unknown> }
      Object.keys(sheet).forEach(key => { if (!extraKeys.has(key) && !(key in parsed)) delete sheet[key] })
      const saved = await api.updateCharacter(room.id, { ...draft, sheet })
      setCharacters(existing => existing.map(item => item.id === saved.id ? saved : item))
      setDraft(saved); setExtras(extrasFor(saved.sheet)); setMessage('Character saved.')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save character.') }
    finally { setBusy(false) }
  }

  function addSkill(event: FormEvent) {
    event.preventDefault()
    const name = newSkill.trim()
    if (!name || !draft) return
    if (Object.keys(draft.sheet.skills).some(existing => existing.toLowerCase() === name.toLowerCase())) {
      setError('That skill is already on the sheet.'); return
    }
    changeSheet({ skills: { ...draft.sheet.skills, [name]: { ability: 'WIS', ranks: 0, misc: 0 } } })
    setNewSkill(''); setError('')
  }

  async function roll(kind: 'ability' | 'skill', target: string) {
    if (!draft || dirty) return
    setBusy(true); setError(''); setMessage('')
    try {
      const posted = await api.rollCheck(room.id, draft.id, kind, target, isGM && dc !== '' ? Number(dc) : undefined)
      onRoll(posted)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not roll the check.') }
    finally { setBusy(false) }
  }

  return <div className="character-workspace">
    <div className="character-intro"><span className="section-kicker">D&D 3.5E</span><h3>Character sheets</h3><p>Record the basics, then roll from your saved sheet. The GM may set a DC.</p></div>
    {error && <div className="notice error" role="alert">{error}</div>}
    {message && <div className="notice success" role="status">{message}</div>}
    <div className="character-layout">
      <div className="character-roster">
        <span className="section-kicker">THE PARTY</span>
        {characters.map(character => <button key={character.id} className={`character-choice ${draft?.id === character.id ? 'selected' : ''}`} onClick={() => choose(character)}>
          <strong>{character.name}</strong><small>{character.owner_id === user.id ? 'Your character' : 'Party member'}</small>
        </button>)}
        {!characters.length && <p className="muted">No characters yet.</p>}
        {room.role !== 'spectator' && <form className="character-create" onSubmit={create}>
          <label htmlFor="new-character">New character</label><input id="new-character" maxLength={80} value={newName} onChange={event => setNewName(event.target.value)} placeholder="Name" />
          <button className="button secondary" disabled={busy || !newName.trim()}>Create character</button>
        </form>}
      </div>
      {draft ? <div className="character-editor">
        <div className="character-editor-head"><div><span className="section-kicker">CHARACTER</span><h4>{draft.name}</h4></div><span className="muted">{canEdit ? 'Editable' : 'View only'}</span></div>
        <label className="character-name">Name<input maxLength={80} value={draft.name} disabled={!canEdit} onChange={event => setDraft({ ...draft, name: event.target.value })} /></label>
        {isGM && <label className="character-dc">Check DC (optional)<input type="number" min={0} max={100} value={dc} onChange={event => setDc(event.target.value)} placeholder="Set by GM" /></label>}
        <div className="character-section"><h5>Ability scores</h5><div className="ability-grid">{abilities.map(ability => <div className="ability-card" key={ability}>
          <label>{ability}<input type="number" min={1} max={99} value={draft.sheet.abilities[ability]} disabled={!canEdit} onChange={event => changeSheet({ abilities: { ...draft.sheet.abilities, [ability]: Number(event.target.value) } })} /></label>
          <span>{signed(modifier(draft.sheet.abilities[ability]))}</span>
          <button className="text-button" disabled={!canEdit || busy || dirty} onClick={() => roll('ability', ability)}>Roll</button>
        </div>)}</div></div>
        <div className="character-section"><h5>Skills</h5><p className="field-help">Ranks may use half steps. Add equipment, circumstance, or other bonuses under Misc.</p>
          <div className="skill-list">{Object.entries(draft.sheet.skills).map(([name, skill]) => <div className="skill-row" key={name}>
            <strong title={name}>{name}</strong><label>Ability<select value={skill.ability} disabled={!canEdit} onChange={event => changeSheet({ skills: { ...draft.sheet.skills, [name]: { ...skill, ability: event.target.value as Ability } } })}>{abilities.map(value => <option key={value}>{value}</option>)}</select></label>
            <label>Ranks<input type="number" min={0} max={100} step={0.5} value={skill.ranks} disabled={!canEdit} onChange={event => changeSheet({ skills: { ...draft.sheet.skills, [name]: { ...skill, ranks: Number(event.target.value) } } })} /></label>
            <label>Misc<input type="number" min={-100} max={100} value={skill.misc} disabled={!canEdit} onChange={event => changeSheet({ skills: { ...draft.sheet.skills, [name]: { ...skill, misc: Number(event.target.value) } } })} /></label>
            <button className="button secondary" disabled={!canEdit || busy || dirty} onClick={() => roll('skill', name)}>Roll</button>
            {canEdit && <button className="skill-remove" aria-label={`Remove ${name}`} onClick={() => { const skills = { ...draft.sheet.skills }; delete skills[name]; changeSheet({ skills }) }}>×</button>}
          </div>)}</div>
          {canEdit && <form className="skill-add" onSubmit={addSkill}><label className="sr-only" htmlFor="new-skill">Skill name</label><input id="new-skill" maxLength={60} value={newSkill} onChange={event => setNewSkill(event.target.value)} placeholder="Add a skill, e.g. Hide" /><button className="button secondary" disabled={!newSkill.trim()}>Add skill</button></form>}
        </div>
        <div className="character-section"><label className="character-notes">Notes<textarea rows={4} maxLength={4000} value={draft.sheet.notes} disabled={!canEdit} onChange={event => changeSheet({ notes: event.target.value })} /></label></div>
        {canEdit && <details className="character-section extra-fields"><summary>Additional JSON fields</summary><p className="field-help">Optional data beyond the simple fields. This must be a JSON object.</p><textarea rows={6} value={extras} onChange={event => setExtras(event.target.value)} spellCheck={false} /></details>}
        {canEdit && <div className="character-save"><span>{dirty ? 'Save changes before rolling.' : 'Sheet is up to date.'}</span><button className="button primary" onClick={save} disabled={busy || !dirty}>{busy ? 'Working…' : 'Save character'}</button></div>}
      </div> : <div className="character-empty"><span className="ornament">✧</span><h4>Gather the party.</h4><p>Create a character to start keeping track of abilities and skills.</p></div>}
    </div>
  </div>
}
