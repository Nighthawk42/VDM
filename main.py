# main.py

import logging
import sys
from pathlib import Path
import traceback
import yaml

# Ensure the 'modules' directory is in the Python path
# This allows importing modules like 'config' using 'from modules.config import ...'
project_root = Path(__file__).resolve().parent
modules_dir = project_root / "modules"
if str(modules_dir) not in sys.path:
    sys.path.insert(0, str(modules_dir))

# Now import from modules (disable noqa E402 if your linter complains)
from modules.config import load_config, Config

# --- Logging Setup ---
# Configure root logger
logging.basicConfig(
    level=logging.INFO, # Set to DEBUG for more verbose output during development
    format='%(asctime)s [%(levelname)-8s] %(name)-15s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout) # Log to console
        # Optionally add FileHandler later:
        # logging.FileHandler("vdm_app.log")
    ]
)
# Get a logger specific to this main module
logger = logging.getLogger("main")

# --- Main Application Logic ---

def run_host_mode(cfg: Config):
    """Placeholder for initializing and running server components."""
    logger.info(">>> Starting Host Mode <<<")
    # --- Initialization (Future Steps) ---
    logger.info("Initializing STT Manager...")
    # from stt_manager import STTManager
    # stt_manager = STTManager(cfg.stt)
    # logger.info("STT Manager Initialized.")

    logger.info("Initializing Speaker Manager...")
    # from speaker_manager import SpeakerManager
    # speaker_manager = SpeakerManager(cfg.speaker)
    # logger.info("Speaker Manager Initialized.")

    # ... Initialize other managers (LLM, TTS, GameState, Server) ...

    logger.info("Host initializations complete (placeholders).")
    logger.warning("Host run loop not implemented yet.")
    # --- Main Loop (Future Step) ---
    # try:
    #     # server.run_forever() or similar blocking call
    #     pass
    # except KeyboardInterrupt:
    #     logger.info("Host mode interrupted by user.")
    # finally:
    #     # Cleanup resources
    #     logger.info("Shutting down host components.")
    #     # server.shutdown() etc.

def run_client_mode(cfg: Config):
    """Placeholder for initializing and running client components."""
    logger.info(">>> Starting Client Mode <<<")
    # --- Initialization (Future Steps) ---
    logger.info("Initializing Network Client...")
    # from client import Client
    # client = Client(cfg.network, cfg.paths.some_client_config) # Adjust as needed
    # logger.info("Network Client Initialized.")

    logger.info("Initializing UI Manager...")
    # from ui import UIManager
    # ui_manager = UIManager(cfg.ui)
    # logger.info("UI Manager Initialized.")

    # ... Initialize Audio IO ...

    logger.info("Client initializations complete (placeholders).")
    logger.warning("Client run loop not implemented yet.")
    # --- Main Loop (Future Step) ---
    # try:
    #     # ui_manager.run() or client.connect_and_run()
    #     pass
    # except KeyboardInterrupt:
    #     logger.info("Client mode interrupted by user.")
    # finally:
    #     # Cleanup resources
    #     logger.info("Shutting down client components.")
    #     # client.disconnect() etc.

def main():
    """Loads configuration and starts the application in the configured mode."""
    logger.info("--- Starting Virtual Dungeon Master Application ---")

    try:
        # Define the expected path to config.yaml relative to this script file
        config_path = project_root / "config.yaml"
        logger.debug(f"Attempting to load configuration from: {config_path}")

        # Load the configuration using the dedicated function
        cfg = load_config(config_path)

        logger.info(f"Successfully loaded configuration. Mode set to: '{cfg.mode}'")

        # Optionally log more config details at DEBUG level for verification
        logger.debug(f"LLM Config: {cfg.llm}")
        logger.debug(f"STT Config: {cfg.stt}")
        logger.debug(f"TTS Config: Default='{cfg.tts.default_voice}', Voices={list(cfg.tts.voices.keys())}")
        logger.debug(f"Paths: {cfg.paths}")

        # Branch execution based on the loaded mode
        if cfg.mode == "host":
            run_host_mode(cfg)
        elif cfg.mode == "client":
            run_client_mode(cfg)
        else:
            # This should theoretically be caught by Literal typing in Config,
            # but belt-and-suspenders approach is good.
            logger.critical(f"FATAL: Invalid mode '{cfg.mode}' detected after loading config. Exiting.")
            sys.exit(1)

    except FileNotFoundError:
        logger.critical(f"FATAL: Configuration file 'config.yaml' not found at expected location: {config_path}")
        logger.critical("Please ensure the file exists in the project root directory.")
        sys.exit(1)
    except (ValueError, yaml.YAMLError) as e:
        logger.critical(f"FATAL: Failed to load or validate configuration from 'config.yaml'.")
        logger.critical(f"Error details: {e}")
        # Include traceback for YAML errors or complex ValueErrors if helpful
        # logger.critical(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        # Catch any other unexpected exceptions during startup
        logger.critical(f"FATAL: An unexpected error occurred during application startup.")
        logger.critical(f"Error details: {e}")
        logger.critical(traceback.format_exc()) # Log the full traceback for unexpected errors
        sys.exit(1)

    logger.info("--- Virtual Dungeon Master Application Finished ---")


# --- Script Entry Point ---
if __name__ == "__main__":
    # Keep the entry point clean, just call main()
    main()