# src/clayPlotter/geo_data_manager.py
import requests
import geopandas as gpd
from pathlib import Path
import logging
import os
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "clayPlotter"

class GeoDataManager:
    """
    Manages downloading, caching, and loading of geographic data files (like shapefiles).
    """
    def __init__(self, cache_dir: Path | str | None = None):
        """
        Initializes the GeoDataManager.

        Args:
            cache_dir: The directory to use for caching downloaded files.
                       Defaults to ~/.cache/clayPlotter.
        """
        if cache_dir is None:
            self.cache_dir = DEFAULT_CACHE_DIR
        else:
            self.cache_dir = Path(cache_dir)

        # Ensure the cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using cache directory: {self.cache_dir}")

    def _get_filename_from_url(self, url: str) -> str:
        """Extracts the filename from a URL."""
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            # Fallback or raise error if filename cannot be determined
            raise ValueError(f"Could not determine filename from URL: {url}")
        return filename

    def get_shapefile(self, url: str) -> Path:
        """
        Ensures a shapefile (or zip containing it) is downloaded and cached.

        Args:
            url: The URL of the shapefile (often a zip archive).

        Returns:
            The local path to the downloaded file.

        Raises:
            requests.exceptions.RequestException: If the download fails.
            ValueError: If the filename cannot be determined from the URL.
        """
        filename = self._get_filename_from_url(url)
        local_path = self.cache_dir / filename

        if local_path.exists():
            logger.info(f"Cache hit: Using existing file {local_path}")
            return local_path
        else:
            logger.info(f"Cache miss: Downloading {url} to {local_path}")
            try:
                # Note: The test mocks `requests.get` and `Path.write_bytes`.
                # The actual implementation uses `requests.get` and `Path.write_bytes`.
                response = requests.get(url, stream=True) # stream=True is good practice, but content is read at once for write_bytes
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

                # Use write_bytes to align with the test mock structure
                local_path.write_bytes(response.content)

                logger.info(f"Successfully downloaded and saved {filename}")
                return local_path
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download {url}: {e}")
                # Clean up potentially incomplete file
                if local_path.exists():
                    try:
                        local_path.unlink()
                    except OSError: # Handle potential race conditions or permission issues
                        logger.warning(f"Could not remove incomplete file: {local_path}")
                raise  # Re-raise the exception
            except Exception as e:
                logger.error(f"An unexpected error occurred during download or saving: {e}")
                if local_path.exists():
                     try:
                        local_path.unlink()
                     except OSError:
                        logger.warning(f"Could not remove file after error: {local_path}")
                raise


    def get_geodataframe(self, url: str, **kwargs) -> gpd.GeoDataFrame:
        """
        Downloads (if necessary) and reads a shapefile from a URL into a GeoDataFrame.

        Args:
            url: The URL of the shapefile (often a zip archive).
            **kwargs: Additional keyword arguments passed directly to geopandas.read_file().

        Returns:
            A GeoDataFrame containing the geographic data.

        Raises:
            Exception: If reading the shapefile fails.
        """
        local_path = None # Initialize local_path
        try:
            local_path = self.get_shapefile(url)
            logger.info(f"Reading GeoDataFrame from {local_path}")

            # Geopandas can often read directly from zip files containing shapefiles.
            # The tests mock read_file to be called with the zip path directly.
            gdf = gpd.read_file(local_path, **kwargs)

            logger.info(f"Successfully loaded GeoDataFrame from {url}")
            return gdf
        except Exception as e:
            # Log the specific local_path if available
            path_info = f"(local path: {local_path})" if local_path else "(local path not determined)"
            logger.error(f"Failed to read GeoDataFrame from {url} {path_info}: {e}")
            raise # Re-raise the exception