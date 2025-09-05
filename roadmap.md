# VDM Project Roadmap

This document outlines the history, current state, and planned future of the Virtual Dungeon Master application.

---

## ✅ **Phase 1: Core Systems (Completed)**

This phase focused on building a stable, feature-rich, and fully playable foundation. All items in this section are implemented and working.

-   **Core Backend & Networking:**
    -   [x] FastAPI server with WebSocket manager.
    -   [x] LAN/VPN accessibility via `0.0.0.0` and HTTPS/SSL support.
    -   [x] CORS configuration for deployment flexibility.

-   **Professional Tooling:**
    -   [x] Centralized YAML-based configuration (`config.yml`, `prompts.yml`, `voices.yml`).
    -   [x] Type-safe Pydantic settings models.
    -   [x] Beautiful console logging with `rich` and intelligent warning suppression.

-   **AI & Storytelling:**
    -   [x] Pluggable LLM provider system (LM Studio, Ollama, OpenRouter).
    -   [x] Externalized, customizable GM prompts.
    -   [x] Configurable LLM tag parsing (`<thinking>`/`<RESPONSE>`).

-   **Long-Term Memory (RAG):**
    -   [x] Custom RAG pipeline using `sentence-transformers` and `ChromaDB`.
    -   [x] Automatic memory creation from GM responses.
    -   [x] Manual memory creation via the `/remember` command.
    -   [x] RAG-augmented prompts to provide the AI with long-term context.

-   **Audio Narration:**
    -   [x] High-quality TTS using the stable `kokoro` (PyTorch) library.
    -   [x] Intelligent text sanitization for clean, immersive audio.

-   **Frontend UI/UX:**
    -   [x] Modern, single-page application with a polished Material Design theme.
    -   [x] Persistent Light/Dark mode.
    -   [x] Discord-style slash command preview.
    -   [x] Dynamic, auto-generating player avatars.

-   **Game Mechanics & Persistence:**
    -   [x] Full session saving and loading (`/save` command and automatic loading).
    -   [x] Multiplayer lobby system with a designated host and "Start Game" flow.
    -   [x] Turn-based action system (`/next` command or "Continue Story" button).
    -   [x] Dice roller (`/roll`) and OOC chat (`/ooc`).

---

## 🎯 **Phase 2: Advanced Immersion & Interaction (Current Focus)**

This phase is about adding layers of dynamic interaction and immersion on top of our stable foundation.

### 1. Dynamic Voice Casting System (RVC Integration)
-   **Goal:** Allow the GM to use different voices for different characters, including custom voice models.
-   **Status:** The configuration (`voices.yml`), prompting (`<v>` tags), and feature flags are **DONE**.
-   **To-Do:**
    -   [ ] Rebuild the `AudioManager` into an "Audio Director" that parses `<v>` tags, consults the casting sheet, and orchestrates the TTS/RVC pipeline for each dialogue segment.
    -   [ ] Fully integrate the PyTorch-based `tts-with-rvc` library for handling voice conversions.

### 2. Speech-to-Text (Client-Side)
-   **Goal:** Allow players to speak their actions instead of typing.
-   **Plan:**
    -   [ ] Implement the browser's **Web Speech API**, which requires no backend changes.
    -   [ ] Add a "Hold to Talk" microphone button to the UI.
    -   [ ] The browser will handle transcription, and the resulting text will be placed in the input box.

---

## 🚀 **Phase 3: Structured Gameplay & World Systems**

This phase will transform the VDM from a pure storyteller into a true "Game Master" that understands and enforces rules.

### 1. Structured Game Mechanics (`game_manager.py`)
-   **Character Sheets:** Implement a simple Pydantic model for character sheets (`hp`, `stats`, `inventory`) and store them in the `Room` state.
-   **Inventory System:** Allow the LLM to grant items via a special tag (e.g., `<ITEM name="Health Potion" />`), which is then parsed by the server and added to a player's character sheet.
-   **Systematized Skill Checks:** This is a major goal.
    1.  Teach the LLM to request a skill check instead of deciding an outcome (e.g., `<ACTION type="skill_check" skill="dexterity" difficulty="15" />`).
    2.  The server parses this, calls our `DiceRoller`, compares the result to the difficulty, and determines success/failure.
    3.  The server then calls the LLM *again* with the result ("System: The dexterity check succeeded. Narrate the outcome.").
    4.  This separates the **Rules Arbitrator** (our code) from the **Storyteller** (the AI).

### 2. Deeper AI & World Integration
-   **AI-Powered Image Generation:** Allow the GM to generate images for scenes or characters via a tag like `<IMAGE prompt="A dark, mossy cave entrance" />`. The server would send this to an image generation API and display the result in the chat.
-   **NPC Management:** Create a dedicated system for managing Non-Player Characters, storing their character sheets, personalities, and key memories in the RAG database.

### 3. Production & Quality of Life
-   **User Authentication:** A simple user system to allow for persistent player identities.
-   **Database Backend:** For larger scale, migrate from JSON file persistence to a more robust database like SQLite.
-   **Admin Dashboard:** A simple web interface for the server host to view logs, manage rooms, and adjust AI settings on the fly.