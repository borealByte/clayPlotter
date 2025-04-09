# src/clayPlotter/geo_data_manager.py
import requests
import geopandas as gpd
from pathlib import Path
import logging
import os
import zipfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "clayPlotter"
GEOPACKAGE_ZIP_URL = "https://naciscdn.org/naturalearth/packages/natural_earth_vector.gpkg.zip"
GEOPACKAGE_FILENAME = "natural_earth_vector.gpkg" # Expected filename inside the zip

# Layer mapping is now handled in individual config files (data_hints.geopackage_layer)
# This dictionary is no longer needed.


class GeoDataManager:
    """
    Manages downloading, caching, and loading of geographic data layers
    from a single Natural Earth vector GeoPackage.
    """
    def __init__(self, cache_dir: Path | str | None = None):
        """
        Initializes the GeoDataManager.

        Args:
            cache_dir: The directory to use for caching the downloaded GeoPackage zip
                       and the extracted GeoPackage file. Defaults to ~/.cache/clayPlotter.
        """
        if cache_dir is None:
            self.cache_dir = DEFAULT_CACHE_DIR
        else:
            self.cache_dir = Path(cache_dir)

        # Ensure the cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using cache directory: {self.cache_dir}")

        # Define paths for the zip and the extracted gpkg file
        self.zip_filename = Path(GEOPACKAGE_ZIP_URL).name
        self.zip_path = self.cache_dir / self.zip_filename
        self.gpkg_path = self.cache_dir / GEOPACKAGE_FILENAME

    def _download_file(self, url: str, local_path: Path) -> None:
        """Downloads a file from a URL to a local path."""
        logger.info(f"Downloading {url} to {local_path}...")
        try:
            response = requests.get(url, stream=True, timeout=60) # Added timeout
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                # Use shutil.copyfileobj for efficient streaming download
                shutil.copyfileobj(response.raw, f)
            logger.info(f"Successfully downloaded {local_path.name}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            if local_path.exists():
                try:
                    local_path.unlink()
                except OSError:
                    logger.warning(f"Could not remove incomplete file: {local_path}")
            raise ValueError(f"Download failed for {url}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during download or saving: {e}")
            if local_path.exists():
                 try:
                    local_path.unlink()
                 except OSError:
                    logger.warning(f"Could not remove file after error: {local_path}")
            raise

    def _unzip_geopackage(self) -> None:
        """Extracts the GeoPackage file from the downloaded zip archive."""
        if not self.zip_path.exists():
            raise FileNotFoundError(f"Cannot unzip: Zip file not found at {self.zip_path}")

        logger.info(f"Extracting {GEOPACKAGE_FILENAME} from {self.zip_path} to {self.cache_dir}...")
        try:
            # Define the expected path within the zip archive
            gpkg_path_in_zip = f"packages/{GEOPACKAGE_FILENAME}"

            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                # Check if the specific gpkg file exists in the zip at the expected path
                if gpkg_path_in_zip not in zip_ref.namelist():
                     raise FileNotFoundError(f"'{gpkg_path_in_zip}' not found inside '{self.zip_path}'. Contents: {zip_ref.namelist()}")
                # Extract the specific file to the cache directory
                # Note: extract() keeps the base filename, not the full path from the zip
                zip_ref.extract(gpkg_path_in_zip, path=self.cache_dir)
                # If the file was extracted inside a 'packages' subdirectory in the cache, move it up
                extracted_file_path = self.cache_dir / gpkg_path_in_zip
                if extracted_file_path.exists() and extracted_file_path != self.gpkg_path:
                    logger.debug(f"Moving extracted file from {extracted_file_path} to {self.gpkg_path}")
                    try:
                        # Ensure parent directory exists (it should, it's the cache dir)
                        self.gpkg_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(extracted_file_path), str(self.gpkg_path))
                        # Clean up the potentially empty 'packages' directory
                        try:
                            extracted_file_path.parent.rmdir()
                        except OSError:
                             logger.debug(f"Could not remove empty directory {extracted_file_path.parent}, it might not be empty.")
                    except Exception as move_err:
                         logger.error(f"Failed to move extracted file: {move_err}")
                         raise RuntimeError(f"Failed to move extracted file to {self.gpkg_path}") from move_err
            logger.info(f"Successfully extracted {self.gpkg_path}")
        except zipfile.BadZipFile as e:
            logger.error(f"Failed to unzip file: {e}. It might be corrupted. Deleting zip.")
            self.zip_path.unlink(missing_ok=True)
            raise ValueError(f"Failed to unzip {self.zip_path}") from e
        except Exception as e:
            logger.error(f"An error occurred during unzipping: {e}")
            # Clean up potentially partially extracted file
            self.gpkg_path.unlink(missing_ok=True)
            raise

    def _ensure_geopackage_available(self) -> None:
        """Ensures the GeoPackage file is available in the cache, downloading and unzipping if needed."""
        if self.gpkg_path.exists():
            logger.debug(f"GeoPackage found at {self.gpkg_path}")
            return # Already available

        logger.info(f"GeoPackage not found at {self.gpkg_path}. Checking for zip file...")

        if not self.zip_path.exists():
            logger.info(f"Zip file not found at {self.zip_path}. Downloading...")
            self._download_file(GEOPACKAGE_ZIP_URL, self.zip_path)
        else:
            logger.info(f"Zip file found at {self.zip_path}. Skipping download.")

        # If we reach here, the zip file should exist (either found or downloaded)
        self._unzip_geopackage()

        # Final check
        if not self.gpkg_path.exists():
             raise RuntimeError(f"Failed to make GeoPackage available at {self.gpkg_path} after download/unzip attempt.")


    def get_geodataframe(self, layer_name: str, **kwargs) -> gpd.GeoDataFrame:
        """
        Loads a specific geographic layer by name from the cached Natural Earth GeoPackage.

        Args:
            layer_name: The exact name of the layer within the GeoPackage file
                        (e.g., 'ne_50m_admin_1_states_provinces').
            **kwargs: Additional keyword arguments passed directly to
                      geopandas.read_file() when reading the layer.

        Returns:
            A GeoDataFrame containing the requested geographic layer.

        Raises:
            ValueError: If download/unzip fails.
            FileNotFoundError: If the GeoPackage file cannot be made available.
            RuntimeError: If reading the specific layer from the GeoPackage fails.
        """
        # Validation of layer_name happens implicitly when geopandas tries to read it.
        # We could add explicit checking using fiona.listlayers if desired, but
        # letting geopandas handle it provides a more direct error if the layer is missing.
        if not isinstance(layer_name, str) or not layer_name:
             raise ValueError("layer_name must be a non-empty string.")

        try:
            # Ensure the .gpkg file is downloaded and extracted
            self._ensure_geopackage_available()
        except (ValueError, FileNotFoundError, RuntimeError) as e:
             # Re-raise errors related to getting the gpkg file ready
             raise ValueError(f"Failed to prepare GeoPackage to read layer '{layer_name}': {e}") from e

        logger.info(f"Reading layer '{layer_name}' from {self.gpkg_path}")
        try:
            # Read the specific layer from the GeoPackage file
            gdf = gpd.read_file(self.gpkg_path, layer=layer_name, **kwargs)
            logger.info(f"Successfully loaded layer '{layer_name}'")
            return gdf
        except Exception as e:
            # Handle errors during the actual layer reading
            logger.error(f"Failed to read layer '{layer_name}' from GeoPackage '{self.gpkg_path}': {e}")
            # You might want to check if the layer actually exists in the GPKG file here
            # import fiona
            # try:
            #     available_layers = fiona.listlayers(self.gpkg_path)
            #     logger.error(f"Available layers: {available_layers}")
            # except Exception as fe:
            #     logger.error(f"Could not list layers in {self.gpkg_path}: {fe}")
            raise RuntimeError(f"Failed to read layer '{layer_name}' from {self.gpkg_path}") from e
