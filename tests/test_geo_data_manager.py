import pytest
import os
import shutil
import geopandas as gpd
from pathlib import Path
from unittest.mock import patch, MagicMock

# Assuming the class will be in src/clayPlotter/geo_data_manager.py
# We'll need to create this file later in the implementation step.
from clayPlotter.geo_data_manager import GeoDataManager # Assuming this path

# Placeholder for where data might be cached
TEST_CACHE_DIR = Path("./test_cache")

@pytest.fixture(scope="function", autouse=True)
def setup_teardown():
    """Create and remove the test cache directory for each test."""
    TEST_CACHE_DIR.mkdir(exist_ok=True)
    yield
    if TEST_CACHE_DIR.exists():
        shutil.rmtree(TEST_CACHE_DIR)

# --- Tests for GeoDataManager ---

# Note: The tests below assume the GeoDataManager downloads a single GeoPackage
# and loads layers from it, matching the current implementation.

# Define a valid geography key for testing
TEST_GEOGRAPHY_KEY = "usa_states"
EXPECTED_LAYER_NAME = "ne_50m_admin_1_states_provinces" # From GEOGRAPHY_LAYERS in geo_data_manager.py

@patch('geopandas.read_file')
@patch.object(GeoDataManager, '_ensure_geopackage_available') # Mock the internal method that handles download/unzip
def test_get_geodataframe_loads_layer(mock_ensure_gpkg, mock_gpd_read):
    """
    Test that get_geodataframe calls internal methods and geopandas.read_file correctly.
    """
    # --- Setup Mocks ---
    # Mock _ensure_geopackage_available to prevent actual download/unzip
    mock_ensure_gpkg.return_value = None # It doesn't need to return anything
    
    # Mock geopandas.read_file to return a dummy GeoDataFrame
    dummy_gdf = MagicMock(spec=gpd.GeoDataFrame)
    mock_gpd_read.return_value = dummy_gdf

    # --- Test Execution ---
    manager = GeoDataManager(cache_dir=TEST_CACHE_DIR)
    # Assume a method get_geodataframe orchestrates getting and reading
    # Pass the layer name directly, as the method signature changed
    gdf = manager.get_geodataframe(layer_name=EXPECTED_LAYER_NAME)

    # --- Assertions ---
    # 1. Check that _ensure_geopackage_available was called
    mock_ensure_gpkg.assert_called_once()
    
    # 2. Check that geopandas.read_file was called with the correct gpkg path and layer name
    mock_gpd_read.assert_called_once_with(manager.gpkg_path, layer=EXPECTED_LAYER_NAME)

    # 3. Check that the returned value is the dummy GeoDataFrame
    assert gdf is dummy_gdf