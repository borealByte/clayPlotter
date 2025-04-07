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

@pytest.fixture
def sample_user_data():
    """Provides sample user data as a DataFrame."""
    return pd.DataFrame({
        'location': ['StateA', 'StateB'], # Use 'location' as in test
        'metric': [15, 25]
    })

# --- Test Cases ---

def test_choropleth_plotter_initialization(sample_user_data):
    """Test successful initialization of ChoroplethPlotter."""
    # Test with minimal valid inputs
    geography_key = "usa_states" # Example key
    location_col = "location"
    value_col = "metric"

    # Patch GeoDataManager to avoid actual file operations during init
    with patch('clayPlotter.plotter.GeoDataManager') as MockGeoDataManager, \
         patch('clayPlotter.plotter.pkg_resources.files') as mock_pkg_files: # Patch resource loading

        # Configure mock resource loading
        mock_resource_ref = MagicMock()
        mock_resource_ref.is_file.return_value = True
        mock_pkg_files.return_value.__truediv__.return_value.__truediv__.return_value = mock_resource_ref
        # Mock the context manager for opening the file
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value.read.return_value = """
figure:
  figsize: [10, 8]
styling:
  cmap: 'viridis'
main_map_settings: {}
""" # Minimal valid YAML
        mock_resource_ref.open.return_value = mock_file_handle

        # Instantiate the plotter
        plotter = ChoroplethPlotter(
            geography_key=geography_key,
            data=sample_user_data,
            location_col=location_col,
            value_col=value_col
        )

        # Assertions
        assert plotter is not None
        assert plotter.geography_key == geography_key
        assert plotter.data is sample_user_data
        assert plotter.location_col == location_col
        assert plotter.value_col == value_col
        assert isinstance(plotter.geo_manager, MagicMock) # Check it used the patched GeoDataManager
        assert plotter.plot_config is not None # Check config was loaded
        MockGeoDataManager.assert_called_once() # Check GeoDataManager was instantiated


# Note: Tests for internal methods like _prepare_data and _calculate_colors
# are removed as these are implementation details tested via the main plot() method.

@patch('clayPlotter.plotter.plt.subplots')
@patch('clayPlotter.plotter.GeoDataManager') # Patch the class used internally
@patch('clayPlotter.plotter.pkg_resources.files') # Patch resource loading
@patch('geopandas.GeoDataFrame.plot') # Patch the final plotting call
def test_plot_generation_returns_axes(mock_gdf_plot, mock_pkg_files, MockGeoDataManager, mock_subplots, sample_user_data):
    """Test that the plot method orchestrates calls and returns matplotlib Figure and Axes."""
    # Configure the mock for plt.subplots to return a figure and axes
    mock_fig = MagicMock()
    mock_ax = MagicMock(spec=Axes) # Mock the Axes object
    mock_subplots.return_value = (mock_fig, mock_ax) # Make plt.subplots return the mocks

    # Configure the mock GeoDataFrame plot method to return the mock axes
    mock_gdf_plot.return_value = mock_ax

    # --- Mock GeoDataManager and Resource Loading ---
    mock_geo_manager_instance = MockGeoDataManager.return_value
    # Mock the return of get_geodataframe
    mock_geo_df = gpd.GeoDataFrame({
        'geometry': [None, None],
        'state_name': ['StateA', 'StateB'] # Column to join on
    }, crs="EPSG:4326")
    mock_geo_manager_instance.get_geodataframe.return_value = mock_geo_df

    # Mock resource loading for config
    mock_resource_ref = MagicMock()
    mock_resource_ref.is_file.return_value = True
    mock_pkg_files.return_value.__truediv__.return_value.__truediv__.return_value = mock_resource_ref
    mock_file_handle = MagicMock()
    mock_file_handle.__enter__.return_value.read.return_value = """
figure:
  figsize: [12, 9]
styling:
  cmap: 'plasma'
main_map_settings: {}
""" # Minimal valid YAML for test
    mock_resource_ref.open.return_value = mock_file_handle

    # --- Instantiate Plotter ---
    geography_key = "usa_states"
    location_col = "location"
    value_col = "metric"
    plotter = ChoroplethPlotter(
        geography_key=geography_key,
        data=sample_user_data,
        location_col=location_col,
        value_col=value_col
    )

    # --- Call the plot method ---
    # Pass necessary arguments for merging and plotting
    result_fig, result_ax = plotter.plot(
        geo_join_column='state_name', # Column name in the mocked GeoDataFrame
        title='Test Plot Title',
        cmap='plasma' # Example override kwarg
    )

    # --- Assertions ---
    # Check that dependencies were called
    mock_geo_manager_instance.get_geodataframe.assert_called_once_with(geography_key=geography_key)
    mock_subplots.assert_called_once() # Check figure/axes were created
    mock_gdf_plot.assert_called_once() # Check the final plot call was made

    # Check arguments passed to the final plot call
    call_args, call_kwargs = mock_gdf_plot.call_args
    assert call_kwargs.get('column') == value_col # Check correct value column used
    assert call_kwargs.get('cmap') == 'plasma' # Check cmap override was used
    assert call_kwargs.get('ax') == mock_ax # Check plotted on correct axes

    # Check returned objects
    assert result_fig is mock_fig
    assert result_ax is mock_ax
    # Check title was set (assuming set_title is called on the mock_ax)
    # Note: Depending on implementation (fig.suptitle vs ax.set_title), adjust this
    # If using fig.suptitle: mock_fig.suptitle.assert_called_with('Test Plot Title')
    # If using ax.set_title: mock_ax.set_title.assert_called_with('Test Plot Title')
    # Based on current plotter code, it uses fig.suptitle
    mock_fig.suptitle.assert_called_with('Test Plot Title')
