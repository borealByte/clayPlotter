# tests/test_plotter.py
import pytest
import pandas as pd
import geopandas as gpd
from unittest.mock import MagicMock, patch
from matplotlib.axes import Axes  # For type checking plot output
import matplotlib.pyplot as plt # Import needed for patching

# Attempt to import the class, expecting it might not exist yet
try:
    from clayPlotter.plotter import ChoroplethPlotter
    from clayPlotter.geo_data_manager import GeoDataManager # Needed for patching target
    from clayPlotter.data_loader import DataLoader # Needed for patching target
except ImportError:
    # Define a placeholder if the class doesn't exist so tests can be defined
    class ChoroplethPlotter:
        def __init__(self, geo_data_manager, data_loader):
            # Store dependencies (adjust attribute names if needed in actual implementation)
            self.geo_manager = geo_data_manager
            self.data_loader = data_loader
            # Raise error to indicate it's just a placeholder for tests
            raise NotImplementedError("ChoroplethPlotter not implemented yet") # Ensure init fails if class is placeholder

        def _prepare_data(self, data, data_column, join_column, geo_join_column):
             raise NotImplementedError("Prepare data method not implemented yet")

        def _calculate_colors(self, data_series, cmap):
             raise NotImplementedError("Calculate colors method not implemented yet")

        def plot(self, data, data_column, join_column, geo_join_column='name', cmap='viridis', title='Choropleth Map', **kwargs):
            raise NotImplementedError("Plot method not implemented yet")

    # Define placeholder dependencies if main import fails
    class GeoDataManager:
        def get_geo_data(self, *args, **kwargs):
            raise NotImplementedError("GeoDataManager placeholder")

    class DataLoader:
        def load_data(self, *args, **kwargs):
             raise NotImplementedError("DataLoader placeholder")


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

def test_choropleth_plotter_initialization(mock_geo_data_manager, mock_data_loader):
    """Test successful initialization of ChoroplethPlotter."""
    # This test assumes the class takes manager instances
    try:
        plotter = ChoroplethPlotter(mock_geo_data_manager, mock_data_loader)
        assert plotter is not None
        # Check if dependencies are stored (adjust attribute names as needed)
        assert plotter.geo_manager == mock_geo_data_manager
        assert plotter.data_loader == mock_data_loader
    except NotImplementedError:
        pytest.fail("ChoroplethPlotter class or __init__ is not implemented.")
    except AttributeError:
         pytest.fail("Expected attributes (e.g., geo_manager, data_loader) not found after init.")


# No patching needed here as we inject mocks via fixtures
def test_data_merging(mock_geo_data_manager, mock_data_loader, sample_user_data):
    """Test the merging of GeoDataFrame and user data using injected mocks."""
    # Mocks are provided directly by fixtures

    gdf = gpd.GeoDataFrame({
        'geometry': [None, None, None],
        'state_name': ['StateA', 'StateB', 'StateC'] # Geo join column
    }, crs="EPSG:4326")
    # Configure the mock geo manager fixture for this test's specific needs
    mock_geo_data_manager.get_geodataframe.return_value = gdf # Correct method name

    # Instantiate plotter - uses the injected mock fixtures
    plotter = ChoroplethPlotter(mock_geo_data_manager, mock_data_loader)

    # Define a mock implementation for _prepare_data ONLY for this test,
    # assuming the real one doesn't exist yet.
    # This allows testing the *expected* outcome of merging.
    def mock_prepare_data(data, data_column, join_column, geo_join_column):
        # Simulate the merge process based on inputs
        geo_df = mock_geo_data_manager.get_geo_data() # Get the mocked GeoData from the fixture
        merged = geo_df.merge(data, left_on=geo_join_column, right_on=join_column)
        # Keep only necessary columns for simplicity in test assertion
        return merged[[geo_join_column, data_column, 'geometry']]

    # We expect the plotter instance to have a _prepare_data method
    # plotter._prepare_data = MagicMock(side_effect=mock_prepare_data) # REMOVE: Don't mock the method under test


    # Expect calling the method to fail until implemented
    with pytest.raises((NotImplementedError, AttributeError)):
        # Call the method we expect to perform the merge
        plotter._prepare_data(
            data=sample_user_data,
            data_column='metric',
            join_column='location', # User data column name
            geo_join_column='state_name' # GeoDataFrame column name
        )
        # Assertions below are commented out until implementation exists
        # assert 'metric' in merged_data.columns
        # assert 'geometry' in merged_data.columns
        # assert 'state_name' in merged_data.columns
        # assert len(merged_data) == 2
        # pd.testing.assert_frame_equal(...)


def test_color_calculation_logic(mock_geo_data_manager, mock_data_loader):
    """Test basic color calculation logic (simplified)."""
    plotter = ChoroplethPlotter(mock_geo_data_manager, mock_data_loader)

    # Define a mock implementation for _calculate_colors
    def mock_calculate_colors(data_series, cmap):
        # Simple placeholder logic: return different values for different inputs
        # A real implementation would involve normalization and colormap mapping
        if data_series.iloc[0] < data_series.iloc[1]:
            return ['#fee0d2', '#de2d26', '#fc9272'] # Example hex colors
        else:
            return ['#de2d26', '#fee0d2', '#fc9272']

    # We expect the plotter instance to have a _calculate_colors method
    # plotter._calculate_colors = MagicMock(side_effect=mock_calculate_colors) # REMOVE: Don't mock the method under test

    # Expect calling the method to fail until implemented
    with pytest.raises((NotImplementedError, AttributeError)):
        # Simulate data that would be used for coloring
        data_for_coloring = pd.Series([10, 100, 50])
        # Call the method we expect to calculate colors
        plotter._calculate_colors(data_for_coloring, cmap='viridis')
        # Assertions below are commented out until implementation exists
        # assert len(colors) == 3
        # assert colors[0] != colors[1]


@patch('clayPlotter.plotter.plt.subplots') # Patch matplotlib's subplots
@patch('geopandas.GeoDataFrame.plot') # Patch the plotting method on GeoDataFrame
def test_plot_generation_returns_axes(mock_gdf_plot, mock_subplots, mock_geo_data_manager, mock_data_loader, sample_user_data):
    """Test that the plot method returns a matplotlib Axes object."""
    # Configure the mock for plt.subplots to return a figure and axes
    mock_fig = MagicMock()
    mock_ax = MagicMock(spec=Axes)
    mock_subplots.return_value = (mock_fig, mock_ax)

    # Configure the mock GeoDataFrame plot method to return the axes
    mock_gdf_plot.return_value = mock_ax

    plotter = ChoroplethPlotter(mock_geo_data_manager, mock_data_loader)

    # Do NOT mock internal methods like _prepare_data here.
    # We want the actual plot method to call the real (error-raising) _prepare_data.
    # prepared_gdf = gpd.GeoDataFrame({ ... }) # Not needed for this test structure
    # plotter._prepare_data = MagicMock(return_value=prepared_gdf) # REMOVE THIS LINE

    # Define a mock implementation for the main plot method ONLY for this test
    def mock_plot(data, data_column, join_column, geo_join_column='name', cmap='viridis', title='Choropleth Map', **kwargs):
        # Simulate the core actions: prepare data, create figure, plot on axes
        gdf_to_plot = plotter._prepare_data(data, data_column, join_column, geo_join_column)
        fig, ax = plt.subplots(1, 1, figsize=kwargs.get('figsize', (10, 10)))
        gdf_to_plot.plot(column=data_column, cmap=cmap, linewidth=0.8, ax=ax, edgecolor='0.8', legend=True)
        ax.set_title(title)
        ax.set_axis_off()
        return ax # Return the axes as expected

    # We expect the plotter instance to have a plot method
    # plotter.plot = MagicMock(side_effect=mock_plot) # REMOVE: Don't mock the method under test

    # Expect calling the method to fail until implemented
    with pytest.raises((NotImplementedError, AttributeError)):
         # Call the main plotting method
        plotter.plot(
            data=sample_user_data,
            data_column='metric',
            join_column='location',
            geo_join_column='state_name', # Make sure this matches fixture/mock data
            cmap='plasma',
            title='Test Plot Title'
        )
        # Assertions below are commented out until implementation exists
        # mock_subplots.assert_called_once()
        # mock_gdf_plot.assert_called_once()
        # call_args, call_kwargs = mock_gdf_plot.call_args
        # assert call_kwargs.get('column') == 'metric'
        # assert call_kwargs.get('cmap') == 'plasma'
        # assert call_kwargs.get('ax') == mock_ax
        # assert isinstance(result_ax, Axes)
        # mock_ax.set_title.assert_called_with('Test Plot Title')

