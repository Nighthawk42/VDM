import { useState } from 'react'
import type { Ability, CharacterSheet, Combat, EquipmentEntry, SheetEntry, SpellEntry } from './api'

const abilities: Ability[] = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
const tabs = ['Overview', 'Combat', 'Equipment', 'Skills', 'Spells', 'Notes'] as const
type Tab = typeof tabs[number]
type SaveName = keyof Combat['saves']
const saveAbility: Record<SaveName, Ability> = { fortitude: 'CON', reflex: 'DEX', will: 'WIS' }
const signed = (value: number) => value >= 0 ? `+${value}` : `${value}`
const modifier = (score: number) => Math.floor((score - 10) / 2)

export function Dnd35SheetTabs({ sheet, canEdit, busy, dirty, change, roll }: {
  sheet: CharacterSheet
  canEdit: boolean
  busy: boolean
  dirty: boolean
  change: (patch: Partial<CharacterSheet>) => void
  roll: (kind: 'ability' | 'skill', target: string) => void
}) {
  const [tab, setTab] = useState<Tab>('Overview')
  const [newSkill, setNewSkill] = useState('')
  const [skillError, setSkillError] = useState('')
  const combat = sheet.combat
  const dex = modifier(sheet.abilities.DEX)
  const armorClass = 10 + dex + combat.armor + combat.shield + combat.natural + combat.deflection + combat.ac_misc
  const updateCombat = (patch: Partial<Combat>) => change({ combat: { ...combat, ...patch } })

  function numberField(label: string, value: number, onChange: (value: number) => void, min = -100, max = 1000) {
    return <label className="sheet-field" key={label}>{label}<input type="number" min={min} max={max} value={value} disabled={!canEdit} onChange={event => onChange(Number(event.target.value))} /></label>
  }
  function textField(label: string, value: string, onChange: (value: string) => void, placeholder = '') {
    return <label className="sheet-field" key={label}>{label}<input maxLength={160} value={value} disabled={!canEdit} placeholder={placeholder} onChange={event => onChange(event.target.value)} /></label>
  }
  function updateList<T extends object>(key: 'attacks' | 'equipment' | 'spells', items: T[], index: number, patch: Partial<T>) {
    change({ [key]: items.map((item, position) => position === index ? { ...item, ...patch } : item) })
  }
  function addSkill() {
    const name = newSkill.trim()
    if (!name) return
    if (Object.keys(sheet.skills).some(existing => existing.toLowerCase() === name.toLowerCase())) {
      setSkillError('That skill is already on the sheet.'); return
    }
    change({ skills: { ...sheet.skills, [name]: { ability: 'WIS', ranks: 0, misc: 0 } } })
    setNewSkill(''); setSkillError('')
  }

  return <>
    <div className="sheet-tabs" role="tablist" aria-label="Character sheet sections">
      {tabs.map(item => <button key={item} type="button" role="tab" aria-selected={tab === item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}
    </div>
    <div role="tabpanel" className="sheet-panel">
      {tab === 'Overview' && <>
        <div className="sheet-section"><h5>Identity</h5><div className="sheet-grid">
          {textField('Race', sheet.race, value => change({ race: value }), 'Elf')}
          {textField('Class', sheet.class_name, value => change({ class_name: value }), 'Rogue')}
          {textField('Alignment', sheet.alignment, value => change({ alignment: value }))}
          {numberField('Level', sheet.level, value => change({ level: value }), 1, 99)}
          {numberField('Experience', sheet.experience, value => change({ experience: value }), 0, 10000000)}
        </div></div>
        <div className="sheet-section"><h5>Ability scores</h5><div className="ability-grid">{abilities.map(ability => <div className="ability-card" key={ability}>
          <label>{ability}<input type="number" min={1} max={99} value={sheet.abilities[ability]} disabled={!canEdit} onChange={event => change({ abilities: { ...sheet.abilities, [ability]: Number(event.target.value) } })} /></label>
          <span>{signed(modifier(sheet.abilities[ability]))}</span>
          <button className="text-button" disabled={!canEdit || busy || dirty} onClick={() => roll('ability', ability)}>Roll</button>
        </div>)}</div></div>
        <div className="sheet-section"><h5>At a glance</h5><div className="sheet-totals">
          <div><span>Hit points</span><strong>{combat.hp_current} / {combat.hp_max}</strong></div>
          <div><span>Armor class</span><strong>{armorClass}</strong></div>
          <div><span>Initiative</span><strong>{signed(dex + combat.initiative_misc)}</strong></div>
          <div><span>Base attack</span><strong>{signed(combat.base_attack)}</strong></div>
        </div></div>
      </>}
      {tab === 'Combat' && <>
        <div className="sheet-section"><h5>Health and movement</h5><div className="sheet-grid">
          {numberField('Current HP', combat.hp_current, value => updateCombat({ hp_current: value }))}
          {numberField('Maximum HP', combat.hp_max, value => updateCombat({ hp_max: value }), 0)}
          {numberField('Nonlethal damage', combat.nonlethal, value => updateCombat({ nonlethal: value }), 0)}
          {numberField('Speed (ft.)', combat.speed, value => updateCombat({ speed: value }), 0)}
          {numberField('Initiative misc', combat.initiative_misc, value => updateCombat({ initiative_misc: value }))}
          {numberField('Base attack bonus', combat.base_attack, value => updateCombat({ base_attack: value }))}
        </div></div>
        <div className="sheet-section"><h5>Armor class</h5><div className="sheet-totals">
          <div><span>Normal</span><strong>{armorClass}</strong></div>
          <div><span>Touch</span><strong>{10 + dex + combat.deflection + combat.ac_misc}</strong></div>
          <div><span>Flat-footed</span><strong>{armorClass - Math.max(0, dex)}</strong></div>
        </div><p className="field-help">Totals use the entered values. Apply conditions and situational modifiers at the table.</p><div className="sheet-grid">
          {(['armor', 'shield', 'natural', 'deflection', 'ac_misc'] as const).map(key => numberField(key === 'ac_misc' ? 'Misc AC' : key[0].toUpperCase() + key.slice(1), combat[key], value => updateCombat({ [key]: value })))}
        </div></div>
        <div className="sheet-section"><h5>Saving throws</h5><div className="sheet-list">
          {(Object.keys(saveAbility) as SaveName[]).map(name => { const entry = combat.saves[name]; const total = entry.base + modifier(sheet.abilities[saveAbility[name]]) + entry.misc; return <div className="sheet-row save-row" key={name}>
            <strong>{name[0].toUpperCase() + name.slice(1)} <span className="sheet-derived">{signed(total)}</span></strong>
            {numberField('Base', entry.base, value => updateCombat({ saves: { ...combat.saves, [name]: { ...entry, base: value } } }))}
            <span className="sheet-derived">{saveAbility[name]} {signed(modifier(sheet.abilities[saveAbility[name]]))}</span>
            {numberField('Misc', entry.misc, value => updateCombat({ saves: { ...combat.saves, [name]: { ...entry, misc: value } } }))}
          </div> })}
        </div></div>
        <div className="sheet-section"><div className="sheet-section-head"><h5>Weapons and attacks</h5>{canEdit && <button className="button secondary" onClick={() => change({ attacks: [...sheet.attacks, { name: '', bonus: '', damage: '' }] })}>Add attack</button>}</div>
          <div className="sheet-list">{sheet.attacks.map((entry: SheetEntry, index) => <div className="sheet-row entry-row" key={index}>
            {textField('Name', entry.name, value => updateList('attacks', sheet.attacks, index, { name: value }))}
            {textField('Attack bonus', entry.bonus, value => updateList('attacks', sheet.attacks, index, { bonus: value }), 'e.g. +5/+0')}
            {textField('Damage', entry.damage, value => updateList('attacks', sheet.attacks, index, { damage: value }), 'e.g. 1d8+2')}
            {canEdit && <button className="sheet-remove" aria-label={`Remove attack ${index + 1}`} onClick={() => change({ attacks: sheet.attacks.filter((_, position) => position !== index) })}>×</button>}
          </div>)}</div>{!sheet.attacks.length && <p className="field-help">No attacks recorded.</p>}
        </div>
      </>}
      {tab === 'Equipment' && <>
        <div className="sheet-section"><div className="sheet-section-head"><h5>Equipment</h5>{canEdit && <button className="button secondary" onClick={() => change({ equipment: [...sheet.equipment, { name: '', quantity: '1', notes: '' }] })}>Add item</button>}</div>
          <div className="sheet-list">{sheet.equipment.map((entry: EquipmentEntry, index) => <div className="sheet-row entry-row" key={index}>
            {textField('Item', entry.name, value => updateList('equipment', sheet.equipment, index, { name: value }))}
            {textField('Qty', entry.quantity, value => updateList('equipment', sheet.equipment, index, { quantity: value }))}
            {textField('Notes', entry.notes, value => updateList('equipment', sheet.equipment, index, { notes: value }))}
            {canEdit && <button className="sheet-remove" aria-label={`Remove item ${index + 1}`} onClick={() => change({ equipment: sheet.equipment.filter((_, position) => position !== index) })}>×</button>}
          </div>)}</div>{!sheet.equipment.length && <p className="field-help">No equipment recorded.</p>}
        </div>
        <div className="sheet-section"><div className="sheet-section-head"><h5>Feats and special abilities</h5>{canEdit && <button className="button secondary" onClick={() => change({ feats: [...sheet.feats, ''] })}>Add feat</button>}</div>
          <div className="sheet-list">{sheet.feats.map((feat, index) => <div className="sheet-row feat-row" key={index}>
            {textField(`Feat ${index + 1}`, feat, value => change({ feats: sheet.feats.map((item, position) => position === index ? value : item) }))}
            {canEdit && <button className="sheet-remove" aria-label={`Remove feat ${index + 1}`} onClick={() => change({ feats: sheet.feats.filter((_, position) => position !== index) })}>×</button>}
          </div>)}</div>{!sheet.feats.length && <p className="field-help">No feats recorded.</p>}
        </div>
      </>}
      {tab === 'Skills' && <div className="sheet-section"><h5>Skills</h5><p className="field-help">Ranks may use half steps. Add equipment, circumstance, or other bonuses under Misc.</p>
        <div className="skill-list">{Object.entries(sheet.skills).map(([name, skill]) => <div className="skill-row" key={name}>
          <strong title={name}>{name} <span className="sheet-derived">{signed(skill.ranks + modifier(sheet.abilities[skill.ability]) + skill.misc)}</span></strong>
          <label>Ability<select value={skill.ability} disabled={!canEdit} onChange={event => change({ skills: { ...sheet.skills, [name]: { ...skill, ability: event.target.value as Ability } } })}>{abilities.map(value => <option key={value}>{value}</option>)}</select></label>
          <label>Ranks<input type="number" min={0} max={100} step={0.5} value={skill.ranks} disabled={!canEdit} onChange={event => change({ skills: { ...sheet.skills, [name]: { ...skill, ranks: Number(event.target.value) } } })} /></label>
          <label>Misc<input type="number" min={-100} max={100} value={skill.misc} disabled={!canEdit} onChange={event => change({ skills: { ...sheet.skills, [name]: { ...skill, misc: Number(event.target.value) } } })} /></label>
          <button className="button secondary" disabled={!canEdit || busy || dirty} onClick={() => roll('skill', name)}>Roll</button>
          {canEdit && <button className="skill-remove" aria-label={`Remove ${name}`} onClick={() => { const skills = { ...sheet.skills }; delete skills[name]; change({ skills }) }}>×</button>}
        </div>)}</div>
        {canEdit && <form className="skill-add" onSubmit={event => { event.preventDefault(); addSkill() }}><label className="sr-only" htmlFor="new-skill">Skill name</label><input id="new-skill" maxLength={60} value={newSkill} onChange={event => setNewSkill(event.target.value)} placeholder="Add a skill, e.g. Hide" /><button className="button secondary" disabled={!newSkill.trim()}>Add skill</button></form>}
        {skillError && <p className="notice error" role="alert">{skillError}</p>}
      </div>}
      {tab === 'Spells' && <div className="sheet-section"><div className="sheet-section-head"><h5>Spells</h5>{canEdit && <button className="button secondary" onClick={() => change({ spells: [...sheet.spells, { name: '', level: '', notes: '' }] })}>Add spell</button>}</div>
        <p className="field-help">Record spells here; spell slots and casting rules are tracked by the group.</p><div className="sheet-list">{sheet.spells.map((entry: SpellEntry, index) => <div className="sheet-row entry-row" key={index}>
          {textField('Spell', entry.name, value => updateList('spells', sheet.spells, index, { name: value }))}
          {textField('Level', entry.level, value => updateList('spells', sheet.spells, index, { level: value }))}
          {textField('Notes', entry.notes, value => updateList('spells', sheet.spells, index, { notes: value }))}
          {canEdit && <button className="sheet-remove" aria-label={`Remove spell ${index + 1}`} onClick={() => change({ spells: sheet.spells.filter((_, position) => position !== index) })}>×</button>}
        </div>)}</div>{!sheet.spells.length && <p className="field-help">No spells recorded.</p>}
      </div>}
      {tab === 'Notes' && <div className="sheet-section"><label className="character-notes">Character notes<textarea rows={12} maxLength={4000} value={sheet.notes} disabled={!canEdit} onChange={event => change({ notes: event.target.value })} /></label></div>}
    </div>
  </>
}
