# VDM - The Virtual Dungeon Master

VDM is a multiplayer, AI-driven storytelling game designed for immersive, collaborative role-playing. It combines a powerful, locally-run backend with a clean web interface, allowing you and your friends to create and experience epic adventures narrated by a sophisticated AI Game Master.

The project is built with a "Keep It Simple, Stupid" (KISS) philosophy, leveraging modern, high-performance tools to create a robust foundation that is easy to understand, maintain, and extend.

![VDM Thematic UI Screenshot](https://i.imgur.com/your-screenshot-url.png) <!-- Replace with a real screenshot URL -->

---

## ✨ Features

* **AI-Powered Game Master:** A sophisticated LLM (Large Language Model) acts as the storyteller, reacting to player actions, describing the world, and narrating events.
* **Real-Time Multiplayer:** Join a room with friends from anywhere. The game state is synchronized in real-time for a seamless collaborative experience.
* **Thematic & Modern UI:** A beautiful and immersive user interface with selectable "Material" and "Thematic" (fantasy manuscript) styles, complete with a persistent light/dark mode.
* **Dynamic Voice Narration:** The GM's responses are brought to life with high-quality, server-side Text-to-Speech.
* **Long-Term Memory (RAG):** The AI has a true long-term memory, powered by a local vector database (`ChromaDB`). It automatically remembers key events and can be manually prompted to remember specific facts with the `/remember` command.
* **Session Persistence:** Save your game at any time with the `/save` command. The server automatically reloads your session when you rejoin the room, so you can continue your adventure later.
* **Turn-Based Gameplay:** A structured turn system allows players to declare their actions, which are then submitted to the GM as a single turn for resolution.
* **Player-Driven Setup:** The adventure begins with the AI collaborating with the players to define the genre, tone, and setting of the story.
* **Secure & Accessible:** Runs locally on your machine and can be securely accessed over your network (LAN, ZeroTier, Hamachi) via HTTPS.
* **Pluggable AI Backends:** Easily switch between different LLM providers, including local options like **LM Studio** and **Ollama**, or cloud services like **OpenRouter**.

---

## 🚀 Getting Started

Follow these steps to get your VDM server up and running.

### Prerequisites

* **Python 3.11+**
* **`uv`:** A fast Python package installer. If you don't have it, run:  
  ```bash
  pip install uv
  ```
* **`mkcert`:** For generating a trusted local SSL certificate (required for microphone access). [See mkcert installation instructions](https://github.com/FiloSottile/mkcert).
* **(Optional) NVIDIA GPU:** For the best performance with local LLMs and RVC.

---

### 1. Project Setup

First, clone or download the project repository.

---

### 2. Create the Virtual Environment

We use `uv` to create a consistent and fast virtual environment. Open your terminal or command prompt in the project's root directory and run:

```bash
# This creates a .venv folder using Python 3.11
uv venv --python 3.11 --seed
```

---

### 3. Activate the Environment

You must activate the environment in your terminal session before installing packages or running the server.

**On Windows (Command Prompt/PowerShell):**
```cmd
.venv\Scripts\activate
```

**On macOS / Linux:**
```bash
source .venv/bin/activate
```

Your terminal prompt should now be prefixed with `(.venv)`.

---

### 4. Install Dependencies

Install all required Python packages using the requirements.txt file.

```bash
# This will install FastAPI, PyTorch, ChromaDB, and all other dependencies
uv pip install -r requirements.txt
```

> **Note:** The first time you run this, it may take a few minutes to download the PyTorch libraries and the Sentence Transformer model for the RAG system.

---

### 5. Configure the VDM

The VDM is configured using simple YAML files.

* **Main Configuration:** Copy `config.yml.example` to `config.yml`. Open the new file and configure it, paying special attention to the `llm` section to select your AI backend (`lmstudio`, `ollama`, `openrouter`) and provide your API key if needed.
* **Prompts (Optional):** Edit `prompts.yml` to change the GM's personality and instructions.
* **Voices (Optional):** If you enable `enable_dynamic_casting` in your config, edit `voices.yml` to assign custom voices to characters.

---

### 6. Generate SSL Certificate (for HTTPS)

The microphone feature requires a secure (HTTPS) connection.

1. **(One-Time Setup) Install a local Certificate Authority:**
   ```bash
   mkcert -install
   ```

2. **Generate Certificate:**  
   From your project's root directory, create a `ssl` folder. Then run the mkcert command, replacing `<YOUR_IP_HERE>` with your actual local network or ZeroTier IP address.

   ```bash
   mkdir ssl
   mkcert -key-file ./ssl/key.pem -cert-file ./ssl/cert.pem localhost 127.0.0.1 ::1 <YOUR_IP_HERE>
   ```

---

### 7. Launch the Server!

Simply run the launch script. It will handle activating the environment and starting the server with all the correct settings.

**On Windows:**
```cmd
launch.bat
```

The server will be running at [https://localhost:8000](https://localhost:8000) (or your configured port). You and your friends can now connect and play!

---

## 🎮 How to Play

1. **Connect:** Open your browser to the server's HTTPS address. Enter a Room ID and a Player Name.
2. **Lobby:** Wait for your friends to join. The first player in the room is the host and will see a "Start Game" button.
3. **Start Game:** The host clicks "Start Game" to begin the collaborative setup.
4. **Define Your World:** The GM will ask what kind of adventure you want to play. Anyone can reply. The first in-character reply sets the stage for the game.
5. **Declare Actions:** During gameplay, type what your character does or says. This adds your action to the current turn's queue.
6. **Submit the Turn:** When all players have declared their actions, anyone can click the "Continue Story" button (or type `/next`) to submit the turn to the GM.
7. **Enjoy the Story:** The GM will narrate the outcome of your combined actions.

---

## ⌨️ Slash Commands

* `/roll [dice]`: Rolls dice (e.g., `/roll 2d6+3`). Defaults to `1d20`.
* `/ooc [message]`: Sends an out-of-character message to other players.
* `/remember [fact]`: Saves a critical fact to the GM's long-term memory.
* `/save`: Saves the current game session.
* `/next`: Submits the current turn's actions to the GM.
