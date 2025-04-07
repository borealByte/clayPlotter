# src/clayPlotter/plotter.py
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from matplotlib import cm

# Import dependencies (adjust if they are structured differently)
# Use relative imports within the package
from .geo_data_manager import GeoDataManager
from .data_loader import DataLoader

class ChoroplethPlotter:
    """
    Handles the creation of choropleth maps by merging geographical data
    with user-provided data and plotting the results.
    """
    def __init__(self, geo_data_manager: GeoDataManager, data_loader: DataLoader):
        """
        Initializes the plotter with data management dependencies.

        Args:
            geo_data_manager: An instance capable of providing GeoDataFrames.
            data_loader: An instance capable of loading user data (though may not be used directly if data passed to plot).
        """
        # Basic type checking for dependencies
        if not isinstance(geo_data_manager, GeoDataManager):
             raise TypeError("geo_data_manager must be an instance of GeoDataManager")
        # Allow data_loader to be None or DataLoader instance if it's optional later
        if data_loader is not None and not isinstance(data_loader, DataLoader):
             raise TypeError("data_loader must be an instance of DataLoader or None")

        self.geo_manager = geo_data_manager
        self.data_loader = data_loader # Store it even if plot takes data directly

    def _prepare_data(self, data: pd.DataFrame, data_column: str, join_column: str, geo_join_column: str) -> gpd.GeoDataFrame:
        """
        Prepares data for plotting by merging geographical data with user data.

        Args:
            data: User data as a Pandas DataFrame.
            data_column: The column in the user data containing values to plot.
            join_column: The column in the user data used for joining with geo data.
            geo_join_column: The column in the GeoDataFrame used for joining.

        Returns:
            A GeoDataFrame ready for plotting.

        Raises:
            ValueError: If join columns or data column are not found, or merge results in empty DataFrame.
            TypeError: If input data is not a DataFrame or geo_manager doesn't provide a GeoDataFrame.
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input 'data' must be a Pandas DataFrame.")

        # Retrieve the base geographical data
        # Use the correct method name based on GeoDataManager implementation
        try:
            # Assuming the method is get_geodataframe based on test mocks
            geo_df = self.geo_manager.get_geodataframe()
        except AttributeError:
             # Fallback or alternative name if needed
             try:
                 geo_df = self.geo_manager.get_geo_data()
             except AttributeError:
                 raise AttributeError("GeoDataManager instance does not have a recognized method like 'get_geodataframe' or 'get_geo_data'")

        if not isinstance(geo_df, gpd.GeoDataFrame):
             raise TypeError("GeoDataManager did not return a GeoDataFrame.")

        # Validate columns exist before merging
        if geo_join_column not in geo_df.columns:
            raise ValueError(f"Geo join column '{geo_join_column}' not found in GeoDataFrame columns: {geo_df.columns.tolist()}")
        if join_column not in data.columns:
            raise ValueError(f"User data join column '{join_column}' not found in DataFrame columns: {data.columns.tolist()}")
        if data_column not in data.columns:
             raise ValueError(f"Data column '{data_column}' not found in DataFrame columns: {data.columns.tolist()}")

        # Perform the merge
        # Keep only necessary columns from user data to avoid conflicts (like geometry if present)
        data_to_merge = data[[join_column, data_column]].copy() # Use .copy() to avoid SettingWithCopyWarning
        merged_gdf = geo_df.merge(data_to_merge, left_on=geo_join_column, right_on=join_column, how='left')

        # Check if merge was successful and resulted in data
        if merged_gdf.empty:
            # Provide more context in the error message
            print(f"Warning: Merge between GeoDataFrame (on '{geo_join_column}') and DataFrame (on '{join_column}') resulted in an empty GeoDataFrame.")
            # Depending on requirements, could raise ValueError or return empty GDF
            # raise ValueError("Merge resulted in an empty GeoDataFrame. Check join columns and data.")

        # Optional: Check for rows that didn't merge (NaNs in data_column where geometry exists)
        # merged_gdf[data_column].isnull().sum() # Count rows in geo_df that didn't find a match

        return merged_gdf


    def _calculate_colors(self, data_series: pd.Series, cmap: str):
        """
        Calculates colors based on data values.
        NOTE: This method is currently not used by the primary plot() logic,
              as GeoPandas handles color mapping internally. It's kept for potential
              future use or more complex coloring schemes.

        Args:
            data_series: The Pandas Series containing the data to color.
            cmap: The name of the colormap to use.

        Returns:
            A list or array of colors corresponding to the data. (Not implemented)

         Raises:
             NotImplementedError: If called, as the logic isn't needed currently.
        """
        # This logic is handled directly by geopandas plot(column=..., cmap=...)
        # If custom color logic were needed, it would go here.
        # For now, raise error if called directly, as it's not expected.
        raise NotImplementedError("_calculate_colors is not intended for direct use with the current plot implementation.")


    def plot(self, data: pd.DataFrame, data_column: str, join_column: str, geo_join_column: str = 'name', cmap: str = 'viridis', title: str = 'Choropleth Map', figsize: tuple = (10, 10), legend: bool = True, missing_kwds: dict = None, **kwargs) -> Axes:
        """
        Generates and returns a choropleth map.

        Args:
            data: User data as a Pandas DataFrame.
            data_column: The column in the user data containing values to plot.
            join_column: The column in the user data used for joining with geo data.
            geo_join_column: The column in the GeoDataFrame used for joining (default: 'name').
            cmap: The matplotlib colormap name (default: 'viridis').
            title: The title for the plot (default: 'Choropleth Map').
            figsize: The figure size (default: (10, 10)).
            legend (bool): Whether to display a legend (colorbar). Default is True.
            missing_kwds (dict, optional): Styling options for geometries with missing data.
                                           Example: {'color': 'lightgrey', 'edgecolor': 'red', 'hatch': '///', 'label': 'Missing Data'}
            **kwargs: Additional keyword arguments passed directly to the GeoPandas plot() method
                      (e.g., linewidth=0.8, edgecolor='0.8').

        Returns:
            A matplotlib Axes object containing the plot.

        Raises:
            ValueError: If data preparation fails (e.g., bad columns, empty merge).
            TypeError: If input data types are incorrect.
            AttributeError: If the GeoDataManager instance is missing expected methods.
        """
        # 1. Prepare the data by merging
        try:
            merged_gdf = self._prepare_data(data, data_column, join_column, geo_join_column)
        except (ValueError, TypeError, AttributeError) as e:
            # Re-raise errors from data preparation to indicate failure cause
            # Use f-string for cleaner formatting
            raise ValueError(f"Data preparation failed: {e}") from e

        # Handle cases where merge might be empty but not raise error in _prepare_data
        if merged_gdf.empty:
             print(f"Warning: Plotting skipped as the merged GeoDataFrame is empty (using columns '{geo_join_column}' and '{join_column}').")
             # Create an empty plot as a fallback or raise error
             fig, ax = plt.subplots(1, 1, figsize=figsize)
             ax.set_title(f"{title} (No data to plot)")
             ax.set_axis_off()
             return ax
             # Alternatively: raise ValueError("Cannot plot, merged data is empty.")

        # 2. Create the plot figure and axes
        fig, ax = plt.subplots(1, 1, figsize=figsize)

        # 3. Plot the merged data
        # Sensible defaults for plotting style
        plot_kwargs = {
            'column': data_column,
            'cmap': cmap,
            'linewidth': 0.5,
            'edgecolor': '0.8', # Light grey edges
            'legend': legend,
            # Provide default legend keywords only if legend is True
            'legend_kwds': {'label': data_column, 'orientation': "horizontal"} if legend else None,
            # Provide default missing keywords, ensuring 'label' is included if missing_kwds is provided but lacks 'label'
            'missing_kwds': missing_kwds if missing_kwds else {'color': 'lightgrey', 'label': 'Missing'}
        }
        # Update default missing_kwds if user provided some but not 'label'
        if missing_kwds and 'label' not in missing_kwds:
             plot_kwargs['missing_kwds']['label'] = 'Missing' # Add default label

        # Allow user to override defaults or add new args via **kwargs
        # Make sure legend_kwds and missing_kwds from kwargs properly merge/override
        if 'legend_kwds' in kwargs:
            # Merge user legend_kwds with defaults if legend is True
            if legend and plot_kwargs['legend_kwds']:
                default_legend_kwds = plot_kwargs['legend_kwds']
                default_legend_kwds.update(kwargs.pop('legend_kwds')) # Update defaults with user kwargs
                plot_kwargs['legend_kwds'] = default_legend_kwds
            else: # If legend is False or no defaults, just use user's
                 plot_kwargs['legend_kwds'] = kwargs.pop('legend_kwds')
        if 'missing_kwds' in kwargs:
             # Merge user missing_kwds with defaults
             default_missing_kwds = plot_kwargs['missing_kwds']
             default_missing_kwds.update(kwargs.pop('missing_kwds')) # Update defaults with user kwargs
             plot_kwargs['missing_kwds'] = default_missing_kwds

        # Update with any remaining kwargs
        plot_kwargs.update(kwargs)

        # Remove legend_kwds if legend is False
        if not legend:
            plot_kwargs.pop('legend_kwds', None) # Remove safely

        try:
            merged_gdf.plot(ax=ax, **plot_kwargs)
        except Exception as e:
            # Catch potential errors during the actual plotting call
            raise RuntimeError(f"GeoPandas plotting failed: {e}") from e


        # 4. Customize the plot
        ax.set_title(title)
        ax.set_axis_off() # Remove axis ticks and labels

        return ax