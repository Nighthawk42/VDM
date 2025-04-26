# modules/config.py

"""
Loads and validates the application configuration from config.yaml.
Uses dataclasses for type hinting and structured access.
Refactored to separate TTS (Kokoro) and RVC voice configurations.
"""

import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Dict, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

# --- Dataclasses for Configuration Sections ---

# (PromptsConfig, NetworkConfig, VadConfig, SttConfig, SpeakerConfig, LlmConfig remain unchanged)
@dataclass
class PromptsConfig:
    system: str
    game_start: str
    assist_template: str

@dataclass
class NetworkConfig:
    host: str
    port: int

@dataclass
class VadConfig:
    min_silence_duration_ms: int

@dataclass
class SttConfig:
    model_size: str
    device: str
    compute_type: str
    vad: VadConfig

@dataclass
class SpeakerConfig:
    use_embeddings: bool
    model_name: str
    similarity_threshold: float
    enrollment_duration_s: int

@dataclass
class LlmConfig:
    model_key: str
    temperature: float
    max_tokens: int
    extra_params: Dict[str, Any] = field(default_factory=dict)


# --- TTS (Kokoro) Specific Dataclasses ---
@dataclass
class KokoroVoiceConfig:
    """Configuration for a native Kokoro TTS voice."""
    voice: str  # Kokoro voice ID (e.g., "en-US-Neural2-J") - Made mandatory
    speed: float = 1.0

@dataclass
class TtsConfig:
    """Text-to-Speech configuration for native Kokoro voices."""
    default_voice: str # Tag name (must exist as a key in voices)
    voices: Dict[str, KokoroVoiceConfig] # Maps tag name to Kokoro config

    def __post_init__(self):
        """Ensure the default voice tag exists in the voices dictionary."""
        if self.default_voice not in self.voices:
            raise ValueError(f"Default TTS voice tag '{self.default_voice}' "
                             f"not found in the defined tts.voices.")


# --- RVC Specific Dataclasses ---
@dataclass
class RvcVoiceConfig:
    """Configuration for a single RVC voice overlay."""
    model_path: str             # Path to the RVC .pth model file - Made mandatory
    base_kokoro_voice: str      # Kokoro voice ID to use for base audio - Made mandatory
    index_path: Optional[str] = None # Optional path to the .index file
    pitch: int = 0                  # Pitch adjustment in semitones
    index_rate: float = 0.75        # Feature search ratio (0.0 to 1.0)
    protect: float = 0.33           # Voiceless consonant protection (0.0 to 0.5)
    base_kokoro_speed: float = 1.0  # Speed for base audio generation

@dataclass
class RvcConfig:
    """RVC configuration, containing multiple RVC voices."""
    # Maps tag name (e.g., "dwarf") to its RVC configuration
    # Can be an empty dictionary if no RVC voices are configured
    voices: Dict[str, RvcVoiceConfig] = field(default_factory=dict)


# --- Other Dataclasses (Paths, UI, Audio remain unchanged) ---
@dataclass
class PathsConfig:
    enrollment_dir: Path
    gamestate_file: Path
    rvc_models_dir: Path

    def __post_init__(self):
        try:
            self.enrollment_dir = Path(self.enrollment_dir).resolve()
            self.gamestate_file = Path(self.gamestate_file).resolve()
            self.rvc_models_dir = Path(self.rvc_models_dir).resolve()
            self.enrollment_dir.mkdir(parents=True, exist_ok=True)
            self.gamestate_file.parent.mkdir(parents=True, exist_ok=True)
            self.rvc_models_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured data directories exist: {self.enrollment_dir}, {self.gamestate_file.parent}, {self.rvc_models_dir}")
        except Exception as e:
            logger.error(f"Error processing paths configuration: {e}", exc_info=True)
            raise ValueError(f"Error setting up application paths: {e}") from e

@dataclass
class UiConfig:
    max_log_lines: int
    timestamp_format: str

@dataclass
class AudioConfig:
    input_device_index: Optional[int]
    output_device_index: Optional[int]
    sample_rate: int
    channels: int
    chunk_size_ms: int


# --- Root Configuration Dataclass ---
@dataclass
class Config:
    """Root configuration object."""
    mode: Literal["host", "client"]
    prompts: PromptsConfig
    network: NetworkConfig
    stt: SttConfig
    speaker: SpeakerConfig
    llm: LlmConfig
    tts: TtsConfig       # Now holds only Kokoro voices config
    rvc: RvcConfig       # New section for RVC voices config
    paths: PathsConfig
    ui: UiConfig
    audio: AudioConfig


# --- Helper Parsing Functions ---

# (_parse_llm_config remains unchanged)
def _parse_llm_config(raw_llm: Dict) -> LlmConfig:
    if not isinstance(raw_llm, dict):
        raise ValueError("LLM configuration must be a dictionary.")
    known_keys = {"model_key", "temperature", "max_tokens"}
    llm_args = {k: v for k, v in raw_llm.items() if k in known_keys}
    extra_params = {k: v for k, v in raw_llm.items() if k not in known_keys}
    for key in ["model_key", "temperature", "max_tokens"]:
        if key not in llm_args:
            raise ValueError(f"LLM config missing required key: '{key}'")
    return LlmConfig(**llm_args, extra_params=extra_params)

def _parse_tts_config(raw_tts: Dict) -> TtsConfig:
    """Parses the TTS section (now specifically for Kokoro voices)."""
    if not isinstance(raw_tts, dict):
        raise ValueError("TTS configuration (tts:) must be a dictionary.")
    if "default_voice" not in raw_tts:
        raise ValueError("TTS config (tts:) missing 'default_voice'")
    if "voices" not in raw_tts or not isinstance(raw_tts["voices"], dict):
        raise ValueError("TTS config (tts:) missing 'voices' dictionary or it's not a dictionary")

    parsed_kokoro_voices = {}
    for tag, params in raw_tts["voices"].items():
        if not isinstance(params, dict):
            raise ValueError(f"Configuration for Kokoro voice tag '{tag}' under 'tts.voices' must be a dictionary.")
        try:
            # Directly instantiate KokoroVoiceConfig
            # It will raise ValueError if 'voice' is missing in __post_init__ (implicitly)
            parsed_kokoro_voices[tag] = KokoroVoiceConfig(**params)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Error parsing Kokoro voice configuration for tag '{tag}' under 'tts.voices': {e}") from e

    # TtsConfig __post_init__ will validate default_voice existence
    return TtsConfig(
        default_voice=raw_tts["default_voice"],
        voices=parsed_kokoro_voices
    )

def _parse_rvc_config(raw_rvc: Optional[Dict]) -> RvcConfig:
    """Parses the RVC section."""
    # RVC section might be missing or null/empty if not used
    if raw_rvc is None:
        logger.info("No 'rvc' section found in config, RVC voices will be unavailable.")
        return RvcConfig(voices={}) # Return empty config
    if not isinstance(raw_rvc, dict):
        raise ValueError("RVC configuration (rvc:) must be a dictionary if present.")

    # Handle the case where rvc: section exists but voices: is missing or null
    raw_rvc_voices = raw_rvc.get("voices")
    if raw_rvc_voices is None or raw_rvc_voices == 'pass': # Handle the 'pass' placeholder
         logger.info("No voices defined under 'rvc.voices', RVC voices will be unavailable.")
         return RvcConfig(voices={})
    if not isinstance(raw_rvc_voices, dict):
         raise ValueError("RVC voices configuration (rvc.voices:) must be a dictionary if present.")

    parsed_rvc_voices = {}
    for tag, params in raw_rvc_voices.items():
        if not isinstance(params, dict):
             raise ValueError(f"Configuration for RVC voice tag '{tag}' under 'rvc.voices' must be a dictionary.")
        try:
            # RvcVoiceConfig __post_init__ handles validation implicitly
            parsed_rvc_voices[tag] = RvcVoiceConfig(**params)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Error parsing RVC voice configuration for tag '{tag}' under 'rvc.voices': {e}") from e

    return RvcConfig(voices=parsed_rvc_voices)

# --- Main Loading Function ---

def load_config(path: Path = Path("config.yaml")) -> Config:
    """Loads the application configuration from the specified YAML file."""
    absolute_path = path.resolve()
    if not absolute_path.is_file():
        logger.error(f"Configuration file not found at: {absolute_path}")
        raise FileNotFoundError(f"Configuration file not found: {absolute_path}")

    logger.info(f"Loading configuration from: {absolute_path}")
    try:
        with absolute_path.open("r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file '{absolute_path}': {e}")
        raise ValueError(f"Malformed YAML in configuration file: {e}") from e

    if not isinstance(raw_config, dict):
        raise ValueError(f"Config file '{absolute_path}' does not contain a valid YAML dictionary structure.")

    try:
        # Adjusted required keys - 'rvc' is now optional at the top level
        required_keys = {"mode", "prompts", "network", "stt", "speaker", "llm", "tts", "paths", "ui", "audio"}
        present_keys = set(raw_config.keys())
        missing_keys = required_keys - present_keys
        if missing_keys:
            raise ValueError(f"Missing required configuration sections: {', '.join(sorted(list(missing_keys)))}")

        # Parse sections using helpers
        llm_config = _parse_llm_config(raw_config["llm"])
        tts_config = _parse_tts_config(raw_config["tts"])
        # Parse RVC config - handle if the section is missing entirely
        rvc_config = _parse_rvc_config(raw_config.get("rvc")) # Use .get() for optional section

        # Construct the final Config object
        config = Config(
            mode=raw_config["mode"],
            prompts=PromptsConfig(**raw_config["prompts"]),
            network=NetworkConfig(**raw_config["network"]),
            stt=SttConfig(
                **{k: v for k, v in raw_config["stt"].items() if k != "vad"},
                vad=VadConfig(**raw_config["stt"]["vad"])
            ),
            speaker=SpeakerConfig(**raw_config["speaker"]),
            llm=llm_config,
            tts=tts_config, # Contains Kokoro voices
            rvc=rvc_config, # Contains RVC voices (possibly empty)
            paths=PathsConfig(**raw_config["paths"]),
            ui=UiConfig(**raw_config["ui"]),
            audio=AudioConfig(**raw_config["audio"]),
        )
        logger.info("Configuration loaded and validated successfully.")
        # Log how many RVC voices were loaded for clarity
        logger.info(f"Loaded {len(config.rvc.voices)} RVC voice configurations.")
        return config

    except (TypeError, KeyError, ValueError, FileNotFoundError) as e:
        logger.error(f"Invalid or incomplete configuration in '{absolute_path}': {e}", exc_info=True)
        raise ValueError(f"Invalid configuration: {e}") from e
    except Exception as e:
        logger.critical(f"An unexpected error occurred during configuration loading: {e}", exc_info=True)
        raise RuntimeError(f"Unexpected error loading config: {e}") from e


# --- Direct Execution Test Block ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Running config.py direct execution test (Refactored TTS/RVC) ---")
    try:
        config_file_path = Path(__file__).resolve().parent.parent / "config.yaml"
        print(f"Attempting to load config from: {config_file_path}")
        cfg = load_config(config_file_path)

        print("\n--- Configuration Loaded Successfully ---")
        print(f"Mode: {cfg.mode}")
        print(f"Default TTS Voice Tag: {cfg.tts.default_voice}")
        print(f"Kokoro Voices ({len(cfg.tts.voices)}):")
        for tag, voice_cfg in cfg.tts.voices.items():
            print(f"  - <voice:{tag}> -> Kokoro ID: {voice_cfg.voice}, Speed: {voice_cfg.speed}")

        print(f"RVC Voices ({len(cfg.rvc.voices)}):")
        if cfg.rvc.voices:
            for tag, voice_cfg in cfg.rvc.voices.items():
                 print(f"  - <voice:{tag}> -> RVC Model: {voice_cfg.model_path}, Base: {voice_cfg.base_kokoro_voice}")
        else:
            print("  (No RVC voices configured)")

        print(f"LLM Model Key: {cfg.llm.model_key}")
        print("---------------------------------------\n")

    except (FileNotFoundError, ValueError, yaml.YAMLError, RuntimeError) as e:
        print(f"\n--- ERROR during config.py direct test ---")
        print(f"{type(e).__name__}: {e}")
        print("------------------------------------------\n")