# src/clayPlotter/mcp/config.py
import os
from pydantic_settings import BaseSettings
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Server configuration settings."""
    APP_NAME: str = "ClayPlotter MCP Server"
    APP_VERSION: str = "0.1.0" # Consider linking to package version if needed
    LOG_LEVEL: str = "INFO"
    CACHE_DIR: Path = Path.home() / ".cache" / "clayPlotter"
    OUTPUT_DIR: Path = Path.cwd() / "output_maps" # Default to project root/output_maps
    ALLOW_ARBITRARY_OUTPUT_PATH: bool = False # Security: Disallow arbitrary paths by default
    MAX_DATA_POINTS: int = 1000 # Limit input data size

    # Optional: Add settings for host/port if running standalone
    # SERVER_HOST: str = "127.0.0.1"
    # SERVER_PORT: int = 8000

    class Config:
        # If using environment variables, define prefix if needed
        # env_prefix = 'CLAYPLOTTER_MCP_'
        env_file = '.env' # Optional: Load from a .env file
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from env/file

# Instantiate settings
settings = Settings()

# Ensure output directory exists
try:
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured output directory exists: {settings.OUTPUT_DIR}")
except Exception as e:
    logger.error(f"Could not create output directory {settings.OUTPUT_DIR}: {e}")
    # Decide if this is a fatal error or if we can proceed without it
    # For now, log and continue, but map saving might fail.

# Configure logging based on settings
log_level_upper = settings.LOG_LEVEL.upper()
numeric_level = getattr(logging, log_level_upper, None)
if not isinstance(numeric_level, int):
    logger.warning(f"Invalid log level: {settings.LOG_LEVEL}. Defaulting to INFO.")
    numeric_level = logging.INFO

# Basic logging config (can be enhanced)
logging.basicConfig(
    level=numeric_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger.info(f"Logging configured with level: {log_level_upper}")
logger.info(f"Cache directory set to: {settings.CACHE_DIR}")
logger.info(f"Default output directory set to: {settings.OUTPUT_DIR}")
logger.info(f"Allow arbitrary output paths: {settings.ALLOW_ARBITRARY_OUTPUT_PATH}")
logger.info(f"Max data points allowed: {settings.MAX_DATA_POINTS}")