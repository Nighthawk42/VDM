export type User = { id: string; username: string; is_admin: boolean }
export type Role = 'host' | 'lead_gm' | 'co_gm' | 'player' | 'spectator'
export type Room = { id: string; name: string; ruleset_id: string; role: Role }
export type Event = {
  id: string
  room_id: string
  actor_id: string
  actor_name: string
  kind: 'action' | 'ooc' | 'narration' | 'roll'
  content: string
  created_at: string
  details?: Record<string, unknown> | null
}
export type MessageKind = Exclude<Event['kind'], 'roll'>
export type Ability = 'STR' | 'DEX' | 'CON' | 'INT' | 'WIS' | 'CHA'
export type Skill = { ability: Ability; ranks: number; misc: number }
export type CharacterSheet = {
  abilities: Record<Ability, number>
  skills: Record<string, Skill>
  notes: string
  [key: string]: unknown
}
export type Character = {
  id: string
  room_id: string
  owner_id: string
  name: string
  sheet: CharacterSheet
  version: number
  updated_at: string
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  me: () => request<User>('/api/auth/me'),
  register: (username: string, password: string) =>
    request<User>('/api/auth/register', { method: 'POST', body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) =>
    request<User>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  rooms: () => request<Room[]>('/api/rooms'),
  room: (id: string) => request<Room>(`/api/rooms/${encodeURIComponent(id)}`),
  createRoom: (name: string, ruleset_id: string) =>
    request<Room>('/api/rooms', { method: 'POST', body: JSON.stringify({ name, ruleset_id }) }),
  joinRoom: (id: string) => request<Room>(`/api/rooms/${encodeURIComponent(id)}/join`, { method: 'POST' }),
  events: (id: string) => request<Event[]>(`/api/rooms/${encodeURIComponent(id)}/events`),
  post: (id: string, kind: MessageKind, content: string) =>
    request<Event>(`/api/rooms/${encodeURIComponent(id)}/events`, {
      method: 'POST', body: JSON.stringify({ kind, content }),
    }),
  narrate: (id: string) => request<Event>(`/api/rooms/${encodeURIComponent(id)}/narrate`, { method: 'POST' }),
  characters: (roomId: string) => request<Character[]>(`/api/rooms/${encodeURIComponent(roomId)}/characters`),
  createCharacter: (roomId: string, name: string) => request<Character>(
    `/api/rooms/${encodeURIComponent(roomId)}/characters`,
    { method: 'POST', body: JSON.stringify({ name, sheet: {} }) },
  ),
  updateCharacter: (roomId: string, character: Character) => request<Character>(
    `/api/rooms/${encodeURIComponent(roomId)}/characters/${encodeURIComponent(character.id)}`,
    { method: 'PUT', body: JSON.stringify({ name: character.name, sheet: character.sheet, version: character.version }) },
  ),
  rollCheck: (roomId: string, characterId: string, kind: 'ability' | 'skill', target: string, dc?: number) =>
    request<Event>(`/api/rooms/${encodeURIComponent(roomId)}/characters/${encodeURIComponent(characterId)}/checks`, {
      method: 'POST', body: JSON.stringify({ kind, target, dc }),
    }),
}
