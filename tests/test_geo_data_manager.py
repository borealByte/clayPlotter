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

# Mock URL for testing
TEST_URL = "http://example.com/test_shapefile.zip"
EXPECTED_FILENAME = "test_shapefile.zip"
EXPECTED_CACHE_PATH = TEST_CACHE_DIR / EXPECTED_FILENAME

@patch('requests.get')
def test_download_shapefile_success(mock_get):
    """
    Test that download_shapefile attempts to download from the correct URL
    and saves the file to the cache directory.
    """
    # Configure the mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"dummy shapefile content"
    mock_get.return_value = mock_response

    manager = GeoDataManager(cache_dir=TEST_CACHE_DIR)
    # We expect the manager to handle the download and saving internally
    # For this test, we primarily care about the interaction (URL call)
    # and the intended outcome (file path).
    # The actual file writing is mocked/assumed in this specific test focus.
    
    # Let's assume a method like get_shapefile handles download/cache logic
    # and returns the path. We'll refine this as needed.
    # For now, let's assume a more direct download method for the test.
    
    # Mocking open is tricky, let's assume download_shapefile takes url and target path
    # Or better, assume get_shapefile returns the path after ensuring it's downloaded.
    
    # Revised approach: Assume get_shapefile orchestrates download if needed.
    # We need to mock the file writing part too if we want to check existence directly
    # without actual download. Let's mock Path.write_bytes.
    
    with patch.object(Path, 'write_bytes') as mock_write_bytes:
        file_path = manager.get_shapefile(TEST_URL) # Assume this triggers download

        # 1. Check if requests.get was called correctly
        mock_get.assert_called_once_with(TEST_URL, stream=True)

        # 2. Check if the file write was attempted with the dummy content
        mock_write_bytes.assert_called_once_with(mock_response.content)
        
        # 3. Check if the returned path is the expected one
        assert file_path == EXPECTED_CACHE_PATH
        
        # 4. Check that the instance used for write_bytes was the expected path
        # The instance write_bytes was called on is the first argument of the call tuple
        called_on_path = mock_write_bytes.call_args[0][0]
        assert called_on_path == EXPECTED_CACHE_PATH


@patch('pathlib.Path.exists')
@patch('pathlib.Path.write_bytes')
@patch('requests.get')
def test_shapefile_caching(mock_get, mock_write_bytes, mock_exists):
    """
    Test that get_shapefile uses the cached file if it exists
    and avoids re-downloading.
    """
    # --- First Call (Simulate Download) ---
    mock_exists.return_value = False # File doesn't exist initially
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"dummy shapefile content"
    mock_get.return_value = mock_response

    manager = GeoDataManager(cache_dir=TEST_CACHE_DIR)
    
    # Call once to trigger download
    file_path1 = manager.get_shapefile(TEST_URL)

    # Assertions for the first call (download happened)
    mock_exists.assert_called_with() # Check if existence was checked
    mock_get.assert_called_once_with(TEST_URL, stream=True)
    mock_write_bytes.assert_called_once_with(mock_response.content)
    assert file_path1 == EXPECTED_CACHE_PATH
    
    # --- Second Call (Simulate Cache Hit) ---
    mock_exists.return_value = True # Now simulate the file exists
    mock_get.reset_mock() # Reset mock for the second call check
    mock_write_bytes.reset_mock() # Reset mock for the second call check
    
    # Call again
    file_path2 = manager.get_shapefile(TEST_URL)

    # Assertions for the second call (cache hit)
    mock_get.assert_not_called() # Should not download again
    mock_write_bytes.assert_not_called() # Should not write again
    # Path.exists would be called again by the implementation
    assert mock_exists.call_count >= 2 # Called at least once per get_shapefile call
    assert file_path2 == EXPECTED_CACHE_PATH # Should return the same path


@patch('geopandas.read_file')
@patch.object(GeoDataManager, 'get_shapefile') # Mock the method within the class
def test_read_shapefile_to_geodataframe(mock_get_shapefile, mock_gpd_read):
    """
    Test that get_geodataframe uses the cached path provided by get_shapefile
    and calls geopandas.read_file correctly.
    """
    # --- Setup Mocks ---
    # Mock get_shapefile to return the expected path without actual download/cache logic
    mock_get_shapefile.return_value = EXPECTED_CACHE_PATH
    
    # Mock geopandas.read_file to return a dummy GeoDataFrame
    dummy_gdf = MagicMock(spec=gpd.GeoDataFrame)
    mock_gpd_read.return_value = dummy_gdf

    # --- Test Execution ---
    manager = GeoDataManager(cache_dir=TEST_CACHE_DIR)
    # Assume a method get_geodataframe orchestrates getting and reading
    gdf = manager.get_geodataframe(TEST_URL)

    # --- Assertions ---
    # 1. Check that get_shapefile was called with the URL
    mock_get_shapefile.assert_called_once_with(TEST_URL)
    
    # 2. Check that geopandas.read_file was called with the path from get_shapefile
    #    Note: geopandas might need a specific layer or file within the zip.
    #    For now, we assume it's called with the zip path directly.
    #    This might need refinement based on the actual implementation.
    #    Example: zip://EXPECTED_CACHE_PATH!/path/inside/zip/file.shp
    #    Let's keep it simple for the initial failing test.
    mock_gpd_read.assert_called_once_with(EXPECTED_CACHE_PATH)

    # 3. Check that the returned value is the dummy GeoDataFrame
    assert gdf is dummy_gdf