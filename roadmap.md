# VDM development roadmap

The local ignored `plan.md` is the living architecture reference. This tracked roadmap records actual progress; a checked box means the new `dev` implementation has been verified.

## Phase 1: Foundation and identity

- [x] Start a clean orphan `dev` branch while preserving `main` and the local legacy source.
- [x] Package the Python 3.12 backend with `uv`, Ruff, mypy, and pytest.
- [x] Add validated configuration and four split SQLite domain schemas.
- [x] Add a runnable service, readiness endpoint, and a simple testing landing page.
- [x] Refuse to open a database with an unknown newer schema version.
- [x] Add versioned migrations before changing database schemas.
- [x] Add accounts, Argon2id password hashing, revocable sessions, and the initial host/player room roles.
- [x] Add stored room messages and live WebSocket delivery.
- [ ] Add GM role management, platform admin bootstrap, TOTP, and login rate limits.

## Phase 2: Rules and turns

- [ ] Add a safe dice expression parser and freeform ruleset as default.
- [ ] Add structured 5e, 3.5e, and Star Wars ruleset adapters.
- [x] Add the first D&D 3.5e character sheets and server-resolved ability/skill checks.
- [ ] Implement the room turn state machine and structured tag parser.

## Phase 3: Intelligence and audio

- [ ] Build campaign isolated memory ingestion and recall.
- [ ] Integrate an LLM provider behind a narrow client interface.
- [ ] Connect audio generation and transcription with persona profiles.

## Phase 4: Frontend and live play

- [x] Build a Catppuccin themed React interface for authentication, rooms, and chat.
- [ ] Connect the turn queue and GM narration.
- [x] Add GM-requested narration and the first 3.5e sheet/check interface.
- [ ] Add voice input and the GM dashboard.

## Operations

- [x] Inspect the existing `z1-hestia` deployment and preserve its data.
- [x] Replace the old `vdm.nighthawk.moe` deployment with the new testing build.
- [x] Check the public URL, service status, and logs after deployment.
