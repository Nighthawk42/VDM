import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Event, type Room, type User } from './api'

const flavors = ['mocha', 'macchiato', 'frappe', 'latte'] as const
type Flavor = typeof flavors[number]

const rulesets = [
  { id: 'freeform', name: 'Freeform storytelling', detail: 'Follow the fiction. Roll when it helps.' },
  { id: 'dnd5e', name: 'Dungeons & Dragons 5e', detail: 'A home for structured 5e adventures.' },
  { id: 'dnd35e', name: 'Dungeons & Dragons 3.5e', detail: 'Classic d20 campaigns.' },
  { id: 'starwars_rev', name: 'Star Wars Revised', detail: 'Stories from a galaxy far, far away.' },
]

function mergeEvents(existing: Event[], incoming: Event[]): Event[] {
  const byId = new Map(existing.map(event => [event.id, event]))
  incoming.forEach(event => byId.set(event.id, event))
  return Array.from(byId.values())
}

function ThemePicker({ theme, onChange }: { theme: Flavor; onChange: (theme: Flavor) => void }) {
  return <label className="theme-picker">
    <span>Theme</span>
    <select value={theme} onChange={event => onChange(event.target.value as Flavor)}>
      {flavors.map(flavor => <option key={flavor} value={flavor}>{flavor[0].toUpperCase() + flavor.slice(1)}</option>)}
    </select>
  </label>
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (user: User) => void }) {
  const [registering, setRegistering] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (registering) await api.register(username.trim(), password)
      onAuthenticated(await api.login(username.trim(), password))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  return <main className="auth-layout">
    <section className="auth-intro">
      <div className="eyebrow"><span className="sparkle">✦</span> A shared world awaits</div>
      <h1>Make a story<br /><em>together.</em></h1>
      <p>Gather your party, shape a world, and let every voice change what happens next.</p>
      <div className="story-quote"><span className="quote-mark">“</span><span>The door is open. What do you do?</span></div>
      <div className="intro-foot">Virtual Dungeon Master <span>·</span> Development build</div>
    </section>
    <section className="auth-panel">
      <div className="panel-kicker">Your adventure starts here</div>
      <h2>{registering ? 'Create your account' : 'Welcome back'}</h2>
      <p className="muted">{registering ? 'Pick a name your party will recognize.' : 'Sign in to return to your rooms.'}</p>
      <form onSubmit={submit} className="stack-form">
        <label>Username
          <input autoComplete="username" minLength={3} maxLength={20} required value={username} onChange={event => setUsername(event.target.value)} placeholder="Your adventurer name" />
        </label>
        <label>Password
          <input type="password" autoComplete={registering ? 'new-password' : 'current-password'} minLength={12} required value={password} onChange={event => setPassword(event.target.value)} placeholder="At least 12 characters" />
        </label>
        {error && <div className="notice error" role="alert">{error}</div>}
        <button className="button primary wide" type="submit" disabled={busy}>{busy ? 'One moment…' : registering ? 'Create account' : 'Sign in'} <span aria-hidden="true">→</span></button>
      </form>
      <p className="auth-switch">{registering ? 'Already have an account?' : 'New to VDM?'} <button className="text-button" onClick={() => { setRegistering(!registering); setError('') }}>{registering ? 'Sign in' : 'Create one'}</button></p>
    </section>
  </main>
}

function Lobby({ user, onEnter }: { user: User; onEnter: (room: Room) => void }) {
  const [rooms, setRooms] = useState<Room[]>([])
  const [name, setName] = useState('')
  const [ruleset, setRuleset] = useState('freeform')
  const [invite, setInvite] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.rooms().then(setRooms).catch(cause => setError(String(cause))) }, [])

  async function create(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setError('')
    try { onEnter(await api.createRoom(name.trim(), ruleset)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create room.') }
    finally { setBusy(false) }
  }

  async function join(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const value = invite.trim()
      const id = value.includes('?room=') ? new URL(value).searchParams.get('room') ?? value : value
      onEnter(await api.joinRoom(id))
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not join room.') }
    finally { setBusy(false) }
  }

  return <main className="lobby page-width">
    <div className="lobby-hero">
      <div className="eyebrow">YOUR TABLE, YOUR STORY</div>
      <h1>Where shall we go,<br /><em>{user.username}?</em></h1>
      <p>Return to an old tale or open a door to somewhere new.</p>
    </div>
    {error && <div className="notice error" role="alert">{error}</div>}
    <div className="lobby-grid">
      <section className="card rooms-card">
        <div className="section-heading"><div><span className="section-kicker">CONTINUE</span><h2>Your rooms</h2></div><span className="count">{rooms.length}</span></div>
        {rooms.length ? <div className="room-list">{rooms.map(room => <button key={room.id} className="room-row" onClick={() => onEnter(room)}>
          <span className="room-glyph">✦</span><span className="room-row-text"><strong>{room.name}</strong><small>{rulesets.find(item => item.id === room.ruleset_id)?.name ?? room.ruleset_id} · {room.role.replace('_', ' ')}</small></span><span className="row-arrow">→</span>
        </button>)}</div> : <div className="empty-rooms"><span className="empty-symbol">✧</span><strong>Your shelf is empty</strong><p>Create a room or join your party with a link.</p></div>}
      </section>
      <div className="lobby-actions">
        <section className="card action-card">
          <span className="section-kicker">BEGIN</span><h2>Start a new room</h2>
          <form onSubmit={create} className="stack-form compact">
            <label>Room name<input required maxLength={80} value={name} onChange={event => setName(event.target.value)} placeholder="The Lantern & the Lost City" /></label>
            <label>Ruleset<select value={ruleset} onChange={event => setRuleset(event.target.value)}>{rulesets.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
            <p className="field-help">{rulesets.find(item => item.id === ruleset)?.detail}</p>
            <button className="button primary" disabled={busy}>Create room <span aria-hidden="true">→</span></button>
          </form>
        </section>
        <section className="card action-card join-card">
          <span className="section-kicker">GATHER</span><h2>Join your party</h2>
          <form onSubmit={join} className="join-form"><label className="sr-only" htmlFor="invite">Room code or link</label><input id="invite" required value={invite} onChange={event => setInvite(event.target.value)} placeholder="Paste a room code or link" /><button className="button secondary" disabled={busy}>Join</button></form>
        </section>
      </div>
    </div>
  </main>
}

function RoomView({ room, user, onBack }: { room: Room; user: User; onBack: () => void }) {
  const [events, setEvents] = useState<Event[]>([])
  const [connected, setConnected] = useState(false)
  const [kind, setKind] = useState<Event['kind']>('action')
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const canWrite = room.role !== 'spectator'
  const canNarrate = ['host', 'lead_gm', 'co_gm'].includes(room.role)

  useEffect(() => {
    let disposed = false
    let socket: WebSocket | undefined
    let retry: ReturnType<typeof setTimeout> | undefined
    setEvents([])
    api.events(room.id).then(history => { if (!disposed) setEvents(history) }).catch(() => {})
    function connect() {
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      socket = new WebSocket(`${protocol}//${location.host}/api/rooms/${encodeURIComponent(room.id)}/ws`)
      socket.onopen = () => { if (!disposed) setConnected(true) }
      socket.onmessage = message => {
        if (disposed) return
        const frame = JSON.parse(message.data)
        if (frame.type === 'history') setEvents(existing => mergeEvents(existing, frame.events))
        if (frame.type === 'event') setEvents(existing => mergeEvents(existing, [frame.event]))
        if (frame.type === 'error') setError(frame.detail)
      }
      socket.onclose = event => {
        setConnected(false)
        if (!disposed && event.code !== 4401 && event.code !== 4403) retry = setTimeout(connect, 2500)
      }
    }
    connect()
    return () => { disposed = true; if (retry) clearTimeout(retry); socket?.close() }
  }, [room.id])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [events.length])

  async function send(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim() || sending) return
    setSending(true); setError('')
    try {
      const posted = await api.post(room.id, kind, draft.trim())
      setEvents(existing => mergeEvents(existing, [posted]))
      setDraft('')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not send message.') }
    finally { setSending(false) }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(`${location.origin}/?room=${encodeURIComponent(room.id)}`)
      setError('Room link copied to clipboard.')
    } catch { setError(`Room code: ${room.id}`) }
  }

  return <main className="table-layout">
    <aside className="table-sidebar">
      <button className="back-link" onClick={onBack}>← All rooms</button>
      <div className="table-identity"><span className="table-emblem">✦</span><span className="section-kicker">ADVENTURE ROOM</span><h1>{room.name}</h1><p>{rulesets.find(item => item.id === room.ruleset_id)?.name ?? room.ruleset_id}</p></div>
      <div className="sidebar-block"><span className="section-kicker">YOUR PLACE AT THE TABLE</span><div className="member-line"><span className="avatar">{user.username[0].toUpperCase()}</span><span><strong>{user.username}</strong><small>{room.role.replace('_', ' ')}</small></span></div></div>
      <div className="sidebar-block sidebar-tip"><span className="section-kicker">STORY NOTE</span><p>Every action becomes part of this room's chronicle. The narrator tools and AI turns are still in development.</p></div>
      <button className="button secondary share-button" onClick={copyLink}>↗ Share room link</button>
    </aside>
    <section className="chronicle">
      <header className="chronicle-header"><div><span className="section-kicker">THE CHRONICLE</span><h2>{room.name}</h2></div><span className={`connection ${connected ? 'online' : ''}`}><span className="connection-dot" />{connected ? 'Live' : 'Reconnecting'}</span></header>
      <div className="chronicle-scroll">
        {events.length ? <div className="event-list">{events.map(entry => <article key={entry.id} className={`story-entry ${entry.kind}`}>
          <div className="entry-meta"><span className="entry-avatar">{entry.kind === 'narration' ? '✦' : entry.actor_name[0].toUpperCase()}</span><strong>{entry.kind === 'narration' ? `${entry.actor_name} · Narrator` : entry.actor_name}</strong><span className="entry-kind">{entry.kind === 'ooc' ? 'Out of character' : entry.kind === 'action' ? 'Action' : 'Narration'}</span></div>
          <p>{entry.content}</p>
        </article>)}</div> : <div className="empty-story"><div className="ornament">✦</div><span className="section-kicker">A BLANK PAGE</span><h3>The story starts with you.</h3><p>Set the scene, speak in character, or tell your party what you do next.</p></div>}
        <div ref={endRef} />
      </div>
      <div className="composer-wrap">
        {error && <div className={`notice ${error.includes('copied') ? 'success' : 'error'}`} role="status">{error}</div>}
        {canWrite ? <form className="composer" onSubmit={send}>
          <div className="composer-top"><label className="sr-only" htmlFor="kind">Message type</label><select id="kind" value={kind} onChange={event => setKind(event.target.value as Event['kind'])}><option value="action">Player action</option><option value="ooc">Out of character</option>{canNarrate && <option value="narration">GM narration</option>}</select><span>What happens next?</span></div>
          <textarea value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} placeholder={kind === 'narration' ? 'The old door creaks open…' : 'I step into the room and look around…'} maxLength={4000} rows={3} />
          <div className="composer-bottom"><span>Enter to send · Shift + Enter for a new line</span><button className="button primary" disabled={sending || !draft.trim()}>{sending ? 'Sending…' : 'Send'} <span aria-hidden="true">↗</span></button></div>
        </form> : <div className="spectator-note">You are watching this story as a spectator.</div>}
      </div>
    </section>
  </main>
}

export default function App() {
  const [theme, setTheme] = useState<Flavor>(() => {
    const saved = localStorage.getItem('vdm-theme')
    return flavors.includes(saved as Flavor) ? saved as Flavor : 'mocha'
  })
  const [user, setUser] = useState<User | null>(null)
  const [room, setRoom] = useState<Room | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('vdm-theme', theme)
  }, [theme])

  useEffect(() => {
    api.me().then(async current => {
      setUser(current)
      const id = new URLSearchParams(location.search).get('room')
      if (id) { try { setRoom(await api.room(id)) } catch { /* Join from the lobby. */ } }
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  function enter(next: Room) {
    setRoom(next)
    history.replaceState(null, '', `/?room=${encodeURIComponent(next.id)}`)
  }

  function leave() {
    setRoom(null)
    history.replaceState(null, '', '/')
  }

  async function logout() {
    await api.logout()
    setUser(null); leave()
  }

  return <div className="app-shell">
    <header className="site-header"><div className="header-inner"><button className="brand" onClick={leave} aria-label="VDM home"><span className="brand-mark">✦</span><span>VDM</span><small>Virtual Dungeon Master</small></button><div className="header-actions"><ThemePicker theme={theme} onChange={setTheme} />{user && <button className="header-logout" onClick={logout}>Sign out <span aria-hidden="true">↗</span></button>}</div></div></header>
    {loading ? <main className="loading-screen">Opening the story…</main> : !user ? <AuthScreen onAuthenticated={setUser} /> : room ? <RoomView key={room.id} room={room} user={user} onBack={leave} /> : <Lobby user={user} onEnter={enter} />}
  </div>
}
