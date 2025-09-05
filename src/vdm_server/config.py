# server/config.py
import yaml
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field

# --- Provider sub-models (for .env) ---
class OpenRouterSettings(BaseModel):
    api_key: str

class OllamaSettings(BaseModel):
    base_url: str

class LMStudioSettings(BaseModel):
    base_url: str

class LLMProvidersFromEnv(BaseModel):
    openrouter: OpenRouterSettings
    ollama: OllamaSettings
    lmstudio: LMStudioSettings

# --- Pydantic models for settings.yml ---
class LLMSettings(BaseModel):
    backend: Literal["openrouter", "ollama", "lmstudio"]
    story_model: str
    prompting_strategy: Literal["json", "legacy_text"]
    llm_uses_tags: bool
    context_messages: int

class AudioSettings(BaseModel):
    enable_streaming: bool
    enable_dynamic_casting: bool
    default_voice: str

class MemorySettings(BaseModel):
    """
    Settings for memory and database persistence.
    """
    chunker: Literal["simple", "chonkie"]
    embedding_model: str
    sessions_db_file: str
    users_db_file: str

class PathsSettings(BaseModel):
    prompts_file: str
    voices_file: str
    memory_dir: str
    audio_out_dir: str

# --- Main Settings Class ---
class Settings(BaseSettings):
    # From .env
    server_host: str = Field("0.0.0.0", alias="SERVER_HOST")
    server_port: int = Field(8000, alias="SERVER_PORT")
    llm_providers: LLMProvidersFromEnv

    # From settings.yml
    llm: LLMSettings
    audio: AudioSettings
    memory: MemorySettings
    paths: PathsSettings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

def load_settings(path: str = "settings.yml") -> Settings:
    """Load YAML and merge with env variables (env wins)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
        return Settings.model_validate(yaml_data)
    except FileNotFoundError:
        print(f"ERROR: Settings file not found at '{path}'. Exiting.")
        raise SystemExit(1)
    except Exception as e:
        print(f"ERROR: Failed to load or validate configuration from '{path}' or '.env': {e}. Exiting.")
        raise SystemExit(1)

# Global instance
settings = load_settings()