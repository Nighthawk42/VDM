# VDM - The Virtual Dungeon Master

![VDM Logo](https://i.imgur.com/10m2zls.png)

VDM is a multiplayer, AI-driven storytelling game designed for immersive, collaborative role-playing. It combines a powerful, locally-run backend with a clean, modular web interface, allowing you and your friends to create and experience epic adventures narrated by a sophisticated AI Game Master.

The project is built with a focus on stability and cutting-edge features, leveraging modern, high-performance tools to create a robust foundation that is easy to understand, maintain, and extend.

---

## ✨ Features

### Core Gameplay
* **AI-Powered Game Master:** A sophisticated LLM acts as the storyteller, reacting to player actions, describing the world, and narrating events.
* **Real-Time Multiplayer:** Join a room with friends from anywhere. The game state is synchronized in real-time for a seamless collaborative experience.
* **Turn-Based System:** A structured turn system allows players to declare their actions, which are then submitted to the GM as a single turn for resolution.
* **Session Persistence:** Save your game with the `/save` command. The server automatically reloads your session when you rejoin the room.

### Advanced AI Memory
* **State-of-the-Art RAG Pipeline:** The AI has a true long-term memory, powered by Google's **EmbeddingGemma** model for top-tier embeddings and the **Chonkie** library for intelligent semantic chunking.
* **Local Vector Store:** All memories are stored locally in a `ChromaDB` vector database.
* **Manual Memory Control:** Players can use the `/remember` command to ensure critical facts are permanently stored in the AI's memory.

### Immersive Experience
* **High-Quality Voice Narration:** The GM's responses are brought to life with server-side Text-to-Speech using the `kokoro` library.
* **Speech-to-Text Input:** A "Hold to Talk" microphone button allows players to speak their actions instead of typing.
* **Markdown Rendering:** GM and player messages are rendered with Markdown for better formatting and readability (e.g., *italics* and **bold**).

### Modern UI/UX
* **Clean & Responsive Interface:** A modern single-page application that works on any device.
* **Light/Dark Modes:** A persistent theme toggle for user comfort.
* **Modular Frontend:** The JavaScript is broken down into small, maintainable modules for features like auth, commands, and avatars.
* **Visual Turn Indicator:** See at a glance which players have submitted their action for the current turn.

### Robust Backend
* **Pluggable AI Backends:** Easily switch between different LLM providers, including local options like **LM Studio** and **Ollama**, or cloud services like **OpenRouter**.
* **Secure User Accounts:** Player accounts are stored with hashed passwords in a dedicated SQLite database.
* **Persistent Sessions:** User logins survive server restarts, allowing for a seamless reconnection experience.

---

## 🚀 Getting Started

Follow these steps to get your VDM server up and running.

### Prerequisites

* **Python 3.11+**
* **`uv`**: A fast Python package installer. If you don't have it, run:
    ```bash
    pip install uv
    ```
* **(Optional) NVIDIA GPU**: For the best performance with local LLMs and TTS.

### 1. Project Setup

First, clone or download the project repository.

### 2. Create and Activate the Virtual Environment

Open your terminal in the project's root directory and run:

```bash
# Create the virtual environment
uv venv

# Activate the environment
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
# source .venv/bin/activate
```

### 3. Install Dependencies

Install all required Python packages. **Note:** This step will download large AI models for embeddings and TTS, which may take some time.

```bash
uv pip install -r requirements.txt
```

### 4. Configure the VDM

  * **Environment Variables**: Copy `.env.example` to `.env` and fill in any necessary API keys or change the default URLs for your local LLM providers.
  * **Main Configuration**: Open `settings.yml` to configure the core behavior, especially the `llm` and `memory` sections to select your AI backend and chunking strategy.
  * **Prompts & Voices (Optional)**: Edit `prompts.yml` to change the GM's personality or `voices.yml` for dynamic voice casting.

### 5. Launch the Server!

Simply run the launch script. It will activate the environment and start the Uvicorn server.

```cmd
uvicorn server.main:app --reload --reload-dir ./server --reload-dir ./web --host 127.0.0.1 --port 8000
```

The server will be running at `http://127.0.0.1:8000`. You and your friends can now connect and play!

---

## 🎮 How to Play

1. **Connect:** Open your browser to the server's address.  
2. **Login/Register:** Create a persistent player account.  
3. **Join a Room:** Enter a Room ID to join or create a game. The first player becomes the room's permanent owner.  
4. **Start the Game:** The room owner clicks "Start Game" to begin the collaborative setup.  
5. **Declare Actions:** During gameplay, type or speak what your character does or says. Your action is added to the turn queue.  
6. **Submit the Turn:** When all players are ready, anyone can click the "Continue Story" button (or type `/next`) to submit the turn to the GM.  
7. **Enjoy the Story:** The GM will narrate the outcome of your combined actions.  

---

## ⌨️ Slash Commands

* `/roll [dice]`: Rolls dice (e.g., `/roll 2d6+3`). Defaults to `1d20`.
* `/ooc [message]`: Sends an out-of-character message to other players.
* `/remember [fact]`: Saves a critical fact to the GM's long-term memory.
* `/save`: Saves the current game session.
* `/next`: Submits the current turn's actions to the GM.
