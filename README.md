# Virtual Dungeon Master (VDM)

<center><img src="https://i.imgur.com/qGDHTpk.png" alt="Virtual Dungeon Master Logo"></center>

A Python-based application designed to act as a virtual dungeon master for tabletop role-playing games, facilitating freeform storytelling for up to 8 players primarily through voice interaction.

## Project Goal

To create an AI-powered co-DM that can handle narration, NPC interaction, and basic game state tracking, allowing human players (including the host) to focus on role-playing and decision-making. The system uses STT -> LLM -> TTS pipeline for interaction.

## Project Status

This project is very much in its infancy, the code will likely be in a skeletal state for the first week or two as things get built out. Any contributions are welcomed. 

Discord: https://discord.gg/FGUgzat3

## Features

*   **AI Dungeon Master:** Leverages a Large Language Model (LLM) via LM Studio for dynamic storytelling and NPC dialogue. Ideally, LM Studio will be replaced with a generic OpenAI API.
*   **Voice Interaction:** Uses faster-whisper for Speech-to-Text (STT) with Voice Activity Detection (VAD).
*   **Text-to-Speech (TTS):** Employs Kokoro-TTS for generating DM and NPC voices.
*   **Multiple Voices:** Supports distinct voices for different characters/narrator using `<voice:TAG>` syntax processed by the backend (Kokoro and potentially RVC overlays - RVC currently optional/commented out).
*   **Speaker Identification:** Can identify players using voice embeddings (via pyannote.audio) or rely on separate audio tracks (if using appropriate WebRTC setup). (Configurable)
*   **Real-time Networking:** Uses WebSockets/WebRTC (via libraries like `aiortc`) for transmitting audio and text between host and clients.
*   **Unified Application:** Single codebase runs as either the 'host' (processing AI and audio) or 'client' (player interface).
*   **Configurable:** Settings managed via `config.yaml`.
*   **Cross-Platform:** Built with Python and standard libraries, aiming for compatibility (primary target Windows).
*   **GPU Acceleration:** Utilizes PyTorch with CUDA support for ML model inference (STT, Speaker ID, RVC).
*   **Modern Tooling:** Uses `uv` for fast dependency and environment management.

## Technology Stack

*   **Python:** 3.11+
*   **Package/Environment Management:** `uv`
*   **Deep Learning Framework:** PyTorch (with CUDA 12.8 support)
*   **STT:** `faster-whisper` (with Silero VAD)
*   **Speaker ID:** `pyannote.audio` (optional, for embedding-based ID)
*   **LLM Interaction:** `lmstudio-python` SDK (requires LM Studio running)
*   **TTS (Base):** `kokoro-tts` (requires espeak-ng)
*   **TTS (Voice Cloning - Optional):** `rvc-python`
*   **Networking:** `websockets`, `aiortc` (or similar WebRTC library)
*   **Configuration:** `PyYAML`
*   **UI:** Basic Console Output (Future: PyGame or other GUI)

## Setup Instructions

1.  **Prerequisites:**
    *   **Git:** For cloning and version control.
    *   **Python:** 3.11 recommended (install from [python.org](https://python.org)).
    *   **`uv`:** Follow installation instructions at [astral.sh/uv](https://astral.sh/uv).
    *   **NVIDIA GPU:** Required for CUDA acceleration.
    *   **CUDA Drivers:** Install appropriate NVIDIA drivers for your GPU.
    *   **CUDA Toolkit:** While PyTorch bundles CUDA runtime libraries, having the full toolkit matching the build (e.g., 12.1 for PyTorch built against CUDA 12.8, check PyTorch install matrix) might be needed for some dependencies or debugging.
    *   **cuDNN:** Required by faster-whisper. Ensure it's compatible with your CUDA version (see faster-whisper docs for installation).
    *   **LM Studio:** Download and install from [lmstudio.ai](https://lmstudio.ai/). Download and load the desired LLM within LM Studio (e.g., Llama 3.1 8B Instruct GGUF) and start the local inference server.
    *   **espeak-ng:** Required by `kokoro-tts`. Install system-wide (see kokoro-tts docs for Windows/Linux instructions).

2.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd Storyteller # Or your repository name
    ```

3.  **Initialize Environment & Install Dependencies:**
    *   Ensure `uv` is installed and in your PATH.
    *   Pin the Python version (if `.python-version` file is present, `uv` uses it automatically; otherwise, run `uv python pin 3.11`).
    *   Install dependencies using `uv`:
        ```bash
        # Create the virtual environment if it doesn't exist
        uv venv

        # Install standard dependencies (uv reads pyproject.toml)
        uv sync

        # Install PyTorch with specific CUDA version (uv sync might handle this if specified correctly in pyproject.toml, otherwise use pip install)
        # Example using uv pip install:
        uv pip install torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128 --index-url https://download.pytorch.org/whl/cu128
        ```
    *   *(Note: The `uv sync` command should ideally install PyTorch correctly if `pyproject.toml` is configured properly with the index URL and versions. The `uv pip install` is a fallback/explicit method.)*

4.  **Configure the Application:**
    *   Edit `config.yaml`.
    *   **Crucially:** Set `llm.model_key` to match the exact identifier of the model loaded and served by your LM Studio instance.
    *   Review and adjust paths, STT model size, device (`cuda` or `cpu`), TTS voices, etc.
    *   If using speaker embeddings, ensure `speaker.model_name` points to a valid model.
    *   If planning to use RVC, uncomment and configure the desired voice(s) under the `rvc:` section, ensuring model files exist at the specified paths.

5.  **(Optional) Download Models:**
    *   Faster-whisper models will download automatically on first use if not found locally.
    *   Ensure the Speaker ID model (`speaker.model_name`) is available (it might download automatically via huggingface libraries).
    *   Ensure the LLM is downloaded and running in LM Studio.
    *   If using RVC, manually place the `.pth` and `.index` files in the location specified in `config.yaml` (e.g., `data/rvc_models/dwarf_voice/`).

## Running the Application

1.  **Start LM Studio Server:** Launch LM Studio, load your desired LLM, and start the local inference server (usually on `localhost:1234`).
2.  **Run the Script:**
    *   Open a command prompt or terminal in the project root directory (`C:\Users\Nighthawk\Documents\GitHub\Storyteller`).
    *   Use the provided batch scripts:
        *   Double-click `launch.bat` to run `main.py` directly using the `uv` environment.

## Configuration (`config.yaml`)

*   `mode`: `host` or `client`. Determines the application's role.
*   `prompts`: Contains system instructions and templates for the LLM.
*   `network`: Host and port for the server.
*   `stt`: Faster-whisper model settings (size, device, compute type, VAD params).
*   `speaker`: Speaker identification settings (enable embeddings, model, threshold).
*   `llm`: LM Studio model identifier and inference parameters.
*   `tts`: Native Kokoro voice configurations (default voice tag, available voices).
*   `rvc`: RVC voice configurations (available voices, model paths, parameters).
*   `paths`: Filesystem paths for data storage.
*   `ui`: Basic UI settings (e.g., log length).
*   `audio`: Audio device settings (input/output device, sample rate).

## Basic Usage

*   **Host Mode:** Runs the full backend pipeline (STT, SpeakerID, LLM, TTS) and serves clients. Requires significant compute resources (especially GPU VRAM). The host can also act as a player.
*   **Client Mode:** Connects to a running host. Handles local audio input/output and displays text chat/narration. Requires fewer resources.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
