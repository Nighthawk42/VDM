# server/logger.py
import logging
import sys
import warnings # <-- NEW IMPORT
from rich.logging import RichHandler

# --- NEW: Suppress specific, harmless warnings from dependencies ---
# This keeps the console clean during startup. We are ignoring warnings that are
# internal to the 'torch' library and are not actionable by us.

# 1. The 'dropout' warning is informational from PyTorch about the Kokoro model's architecture.
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r".*dropout option adds dropout after all but last recurrent layer.*"
)
# 2. The 'weight_norm' warning is a forward-compatibility notice from PyTorch.
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=r".*`torch.nn.utils.weight_norm` is deprecated.*"
)

# 3. The 'pkg_ resources' warning.
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r".*pkg_resources is deprecated as an API.*"
)

# --- The rest of the logger configuration is unchanged ---

# Configure the RichHandler for beautiful console output
handler = RichHandler(show_time=False, rich_tracebacks=True, log_time_format="[%X]")

# Define the format for our log messages
FORMAT = "%(message)s"
formatter = logging.Formatter(FORMAT)
handler.setFormatter(formatter)

# Get the root logger and configure it
logger = logging.getLogger("vdm")
logger.setLevel(logging.INFO)

# Add our rich handler
logger.addHandler(handler)

# Prevent the log messages from being duplicated by the root logger
logger.propagate = False

logger.info("Logging started")