# VDM Project Roadmap

This document outlines the history, current state, and planned future of the Virtual Dungeon Master application.

---
## ✅ Completed Milestones

This section lists the major features and architectural improvements that are fully implemented, stable, and working in the current version of the project.

#### Core Backend & Systems
- **[x] Robust Server Foundation**: FastAPI backend with a real-time WebSocket manager for multiplayer communication.
- **[x] Pluggable LLM Backends**: Support for multiple AI providers, including LM Studio, Ollama, and OpenRouter.
- **[x] Secure User Accounts**: Persistent user accounts with hashed passwords stored in a dedicated SQLite database.
- **[x] Persistent Server Sessions**: User logins survive server restarts for a seamless experience.
- **[x] Room & Game Persistence**: Full game state (messages, players) is saved and loaded automatically from a SQLite database.

#### Advanced RAG Pipeline
- **[x] State-of-the-Art Embeddings**: Utilizes Google's `EmbeddingGemma` model for high-quality text embeddings.
- **[x] Intelligent Chunking**: Integrated the `Chonkie` library to perform advanced semantic chunking on text for superior memory creation.
- **[x] Local Vector Store**: Employs `ChromaDB` for efficient, local long-term memory storage and retrieval.

#### Immersive Frontend & UI/UX
- **[x] Modular Frontend Architecture**: The entire JavaScript frontend has been refactored into small, maintainable modules for features like auth, audio, commands, and rendering.
- **[x] Speech-to-Text**: Players can use their microphone to speak their actions.
- **[x] Secure Markdown Rendering**: Chat messages are rendered with Markdown for rich text formatting (*italics*, **bold**) and sanitized with DOMPurify for security.
- **[x] Visual Turn Indicator**: The UI clearly shows which players have submitted their action for the current turn.
- **[x] Persistent Light/Dark Modes**: A modern, clean interface with a theme toggle.
- **[x] Helper UI**: Includes a command previewer and dynamic avatar selection.

---
## 🎯 Current Focus

This section outlines the next set of user-facing features we are focused on developing.

- **[ ] GM-Triggered Sound Effects**: Implement a system where the AI can use a special tag (e.g., `<sfx name="door_creak" />`) in its response to trigger pre-loaded sound effects on the client side, enhancing immersion.
- **[ ] Player "Typing..." Indicator**: Add a visual indicator to the UI that shows when other players in the room are actively typing a message, improving the sense of presence in multiplayer.
- **[ ] GM-to-Player Whispers**: Create a system for the AI to send secret messages to a single player via a tag like `<whisper to="PlayerName">You notice a secret...</whisper>`, allowing for private information and plot twists.

---
## 🚀 Future Goals

This section lists larger, more complex systems to be considered after the current feature set is complete and polished.

#### Structured Gameplay Systems
- **Character Sheets**: Introduce a simple data model for character sheets to track stats like HP, attributes, and inventory.
- **Systematized Skill Checks**: Evolve the AI from a storyteller into a true Game Master by teaching it to request skill checks from the backend (e.g., `<check skill="dexterity" difficulty="15" />`) rather than deciding outcomes itself. This separates the **Rules Arbitrator** (our code) from the **Storyteller** (the AI).

#### Advanced Multimedia & Immersion
- **Dynamic Voice Casting (RVC)**: Fully integrate a Retrieval-based Voice Conversion (RVC) library to give unique, custom voices to different NPCs based on the `<v name="...">` tags.
- **AI-Generated Scene Imagery**: Allow the AI to generate and display images for key scenes or characters using a tag like `<image prompt="..." />`.

#### Operational Excellence
- **Docker Support**: Containerize the entire application with a `Dockerfile` and `docker-compose.yml` for easy, one-command deployment.
- **Automated Testing**: Build a test suite using `pytest` to ensure code quality and prevent regressions.