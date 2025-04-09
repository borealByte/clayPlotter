# tests/test_plotter.py
import pytest
import pandas as pd
import geopandas as gpd
from unittest.mock import MagicMock, patch
from matplotlib.axes import Axes  # For type checking plot output
import matplotlib.pyplot as plt # Import needed for patching

# Import the actual classes
from clayPlotter.plotter import ChoroplethPlotter
from clayPlotter.geo_data_manager import GeoDataManager
from clayPlotter.data_loader import DataLoader # Although not directly used in plotter init, keep for potential future tests or spec
# --- Fixtures ---

@pytest.fixture
def mock_geo_data_manager():
    """Provides a mock GeoDataManager."""
    mock = MagicMock(spec=GeoDataManager) # Use spec for better mocking
    # Create a simple GeoDataFrame for testing
    gdf = gpd.GeoDataFrame({
        'geometry': [None, None],  # Placeholder geometries
        'state_name': ['StateA', 'StateB'] # Use consistent naming
    }, crs="EPSG:4326")
    mock.get_geodataframe.return_value = gdf # Correct method name
    return mock

@pytest.fixture
def mock_data_loader():
    """Provides a mock DataLoader."""
    mock = MagicMock(spec=DataLoader) # Use spec
    # Create a simple DataFrame for testing
    df = pd.DataFrame({
        'state_name': ['StateA', 'StateB'], # Use consistent naming
        'value': [10, 20]
    })
    # Assume data loader isn't used if data is passed directly to plot
    # mock.load_data.return_value = df
    return mock

@pytest.fixture(scope="module")
def sample_user_data_map():
    """Provides sample user data for different geographies."""
    return {
        "usa_states": pd.DataFrame({
            'location': ['StateA', 'StateB'],
            'metric': [15, 25]
        }),
        "china_provinces": pd.DataFrame({
            'province_name': ['ProvinceX', 'ProvinceY'], # Example location column
            'population': [1000000, 500000] # Example value column
        })
    }

@pytest.fixture(scope="module")
def mock_geo_data_map():
    """Provides mock GeoDataFrames for different geographies."""
    return {
        "usa_states": gpd.GeoDataFrame({
            'geometry': [None, None],
            'state_name': ['StateA', 'StateB'] # Join column for USA
        }, crs="EPSG:4326"),
        "china_provinces": gpd.GeoDataFrame({
            'geometry': [None, None],
            'name_en': ['ProvinceX', 'ProvinceY'] # Expected join column for China based on config
        }, crs="EPSG:4326")
    }

@pytest.fixture(scope="module")
def mock_config_map():
    """Provides mock plot configurations for different geographies, including data_hints."""
    return {
        "usa_states": {
            'figure': {'figsize': [12, 9], 'title': 'USA Default Title', 'title_fontsize': 12}, # Added fontsize
            'styling': {'cmap': 'plasma'},
            'main_map_settings': {},
            'label_settings': {'level1_code_column': 'state_code'}, # Example
            'data_hints': {'geopackage_layer': 'ne_50m_admin_1_states_provinces'} # Add required hint
        },
        "china_provinces": {
            'figure': {'figsize': [16, 12], 'title': 'China Default Title', 'title_fontsize': 16}, # Added fontsize
            'styling': {'cmap': ['#FF0000', '#FFFFFF']}, # Example custom cmap
            'main_map_settings': {'target_crs': 'EPSG:4479'},
            'label_settings': {'level1_code_column': 'name_en'}, # Match mock GDF
            'data_hints': {'geopackage_layer': 'ne_50m_admin_1_states_provinces'} # Add required hint
        }
    }

# --- Test Cases ---

def test_choropleth_plotter_initialization(sample_user_data_map): # Use the map fixture
    """Test successful initialization of ChoroplethPlotter."""
    # Test with minimal valid inputs
    geography_key = "usa_states" # Example key
    location_col = "location"
    value_col = "metric"

    # Patch GeoDataManager and yaml.safe_load to avoid file/network operations during init
    with patch('clayPlotter.plotter.GeoDataManager') as MockGeoDataManager, \
         patch('clayPlotter.plotter.yaml.safe_load') as mock_safe_load:

        # Configure mock yaml loading
        # Configure mock yaml loading to include data_hints
        mock_safe_load.return_value = {
            'figure': {'figsize': [10, 8]},
            'styling': {'cmap': 'viridis'},
            'main_map_settings': {},
            'data_hints': {'geopackage_layer': 'ne_50m_admin_1_states_provinces'} # Add required hint
        }

        # Instantiate the plotter
        # Use data from the map fixture for a specific key
        plotter = ChoroplethPlotter(
            geography_key=geography_key,
            data=sample_user_data_map[geography_key], # Access data using the key
            location_col=location_col,
            value_col=value_col
        )

        # Assertions
        assert plotter is not None
        assert plotter.geography_key == geography_key
        assert plotter.data is sample_user_data_map[geography_key] # Compare with the correct data from the map
        assert plotter.location_col == location_col
        assert plotter.value_col == value_col
        assert isinstance(plotter.geo_manager, MagicMock) # Check it used the patched GeoDataManager
        assert plotter.plot_config is not None # Check config was loaded
        MockGeoDataManager.assert_called_once() # Check GeoDataManager was instantiated
        mock_safe_load.assert_called_once() # Check config load was attempted


# Note: Tests for internal methods like _prepare_data and _calculate_colors
# are removed as these are implementation details tested via the main plot() method.

@pytest.mark.parametrize("geography_key, location_col, value_col, geo_join_col", [
    ("usa_states", "location", "metric", "state_name"),
    ("china_provinces", "province_name", "population", "name_en")
])
@patch('clayPlotter.plotter.plt.subplots')
@patch('clayPlotter.plotter.GeoDataManager') # Patch the class used internally
@patch('clayPlotter.plotter.yaml.safe_load') # Patch yaml loading
@patch('geopandas.GeoDataFrame.plot') # Patch the final plotting call
def test_plot_generation_returns_axes(
    mock_gdf_plot, mock_safe_load, MockGeoDataManager, mock_subplots,
    geography_key, location_col, value_col, geo_join_col, # Added parameters
    sample_user_data_map, mock_geo_data_map, mock_config_map # Use map fixtures
):
    """Test that the plot method orchestrates calls and returns matplotlib Figure and Axes."""
    # Configure the mock for plt.subplots to return a figure and axes
    mock_fig = MagicMock()
    mock_ax = MagicMock(spec=Axes) # Mock the Axes object
    mock_subplots.return_value = (mock_fig, mock_ax) # Make plt.subplots return the mocks

    # Configure the mock GeoDataFrame plot method to return the mock axes
    mock_gdf_plot.return_value = mock_ax

    # --- Mock GeoDataManager and Resource Loading ---
    mock_geo_manager_instance = MockGeoDataManager.return_value
    # Mock get_geodataframe based on parameterized key
    mock_geo_df = mock_geo_data_map[geography_key]
    mock_geo_manager_instance.get_geodataframe.return_value = mock_geo_df

    # Mock yaml loading based on parameterized key
    mock_safe_load.return_value = mock_config_map[geography_key]

    # --- Instantiate Plotter using parameterized values ---
    plotter = ChoroplethPlotter(
        geography_key=geography_key,
        data=sample_user_data_map[geography_key], # Use correct user data
        location_col=location_col,
        value_col=value_col
    )

    # --- Call the plot method ---
    # Pass necessary arguments for merging and plotting
    # --- Call the plot method using parameterized values ---
    test_title = f'Test Plot {geography_key}'
    result_fig, result_ax = plotter.plot(
        geo_join_column=geo_join_col, # Use parameterized join column
        title=test_title,
        # cmap='plasma' # Remove override unless testing specific kwargs
    )

    # --- Assertions ---
    # Check that dependencies were called
    # Check that get_geodataframe was called with the layer name from the mock config
    expected_layer_name = mock_config_map[geography_key]['data_hints']['geopackage_layer']
    mock_geo_manager_instance.get_geodataframe.assert_called_once_with(layer_name=expected_layer_name)
    mock_subplots.assert_called_once() # Check figure/axes were created
    mock_gdf_plot.assert_called_once() # Check the final plot call was made

    # Check arguments passed to the final plot call
    call_args, call_kwargs = mock_gdf_plot.call_args
    assert call_kwargs.get('column') == value_col # Check correct value column used
    # Check cmap based on mock config type
    expected_cmap_config = mock_config_map[geography_key]['styling'].get('cmap', 'viridis')
    actual_cmap = call_kwargs.get('cmap')
    if isinstance(expected_cmap_config, list):
        # If config was a list, plotter should create a LinearSegmentedColormap
        from matplotlib.colors import LinearSegmentedColormap
        assert isinstance(actual_cmap, LinearSegmentedColormap)
    else:
        # If config was a string, plotter should use it directly
        assert actual_cmap == expected_cmap_config
    assert call_kwargs.get('ax') == mock_ax # Check plotted on correct axes

    # Check returned objects
    assert result_fig is mock_fig
    assert result_ax is mock_ax
    # Check title was set (assuming set_title is called on the mock_ax)
    # Note: Depending on implementation (fig.suptitle vs ax.set_title), adjust this
    # If using fig.suptitle: mock_fig.suptitle.assert_called_with('Test Plot Title')
    # If using ax.set_title: mock_ax.set_title.assert_called_with('Test Plot Title')
    # Based on current plotter code, it uses fig.suptitle with fontsize
    expected_fontsize = mock_config_map[geography_key]['figure'].get('title_fontsize', 12) # Get expected fontsize
    mock_fig.suptitle.assert_called_with(test_title, fontsize=expected_fontsize, y=0.98) # Check title, fontsize, and new y position
