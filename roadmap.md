# VDM development roadmap

The local ignored `plan.md` is the living architecture reference. This tracked roadmap records actual progress; a checked box means the new `dev` implementation has been verified.

## Phase 1: Foundation and identity

- [x] Start a clean orphan `dev` branch while preserving `main` and the local legacy source.
- [x] Package the Python 3.12 backend with `uv`, Ruff, mypy, and pytest.
- [x] Add validated configuration and four split SQLite domain schemas.
- [x] Add a runnable service, readiness endpoint, and a simple testing landing page.
- [x] Refuse to open a database with an unknown newer schema version.
- [ ] Add versioned migrations before changing database schemas.
- [ ] Add accounts, Argon2id password hashing, sessions, room roles, and TOTP.

## Phase 2: Rules and turns

- [ ] Add a safe dice expression parser and freeform ruleset as default.
- [ ] Add structured 5e, 3.5e, and Star Wars ruleset adapters.
- [ ] Implement the room turn state machine and structured tag parser.

## Phase 3: Intelligence and audio

- [ ] Build campaign isolated memory ingestion and recall.
- [ ] Integrate an LLM provider behind a narrow client interface.
- [ ] Connect audio generation and transcription with persona profiles.

## Phase 4: Frontend and live play

- [ ] Build the Catppuccin themed React interface.
- [ ] Connect authentication, rooms, chat, and turns.
- [ ] Add voice input and the GM dashboard.

## Operations

- [ ] Inspect the existing `z1-hestia` deployment and preserve its data.
- [ ] Replace the old `vdm.nighthawk.moe` deployment with an approved testing build.
- [ ] Check the public URL, service status, and logs after deployment.
