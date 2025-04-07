# src/clayPlotter/plotter.py
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from matplotlib import cm
from pathlib import Path
import yaml
import importlib.resources as pkg_resources
import logging
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from shapely.geometry import Polygon, MultiPolygon # Needed for label clipping
from shapely.ops import transform
# import pyproj # For coordinate transformations if needed for offsets - Keep commented for now

# Import dependencies
from .geo_data_manager import GeoDataManager, GEOGRAPHY_LAYERS

logger = logging.getLogger(__name__)

class ChoroplethPlotter:
    """
    Handles the creation of choropleth maps by merging geographical data
    with user-provided data and plotting the results based on configuration.
    """
    def __init__(self, geography_key: str, data: pd.DataFrame, location_col: str, value_col: str, cache_dir: Path | str | None = None):
        """
        Initializes the plotter using a predefined geography key.

        Args:
            geography_key: The key identifying the geographic dataset and configuration
                           (e.g., 'usa_states'). Must correspond to a layer key in
                           GeoDataManager.GEOGRAPHY_LAYERS and a config file in resources.
            data: User data as a Pandas DataFrame.
            location_col: The column in the user data used for joining with geo data (e.g., 'State').
            value_col: The column in the user data containing values to plot (e.g., 'Value').
            cache_dir: Optional directory for caching downloaded files.
                       Defaults to ~/.cache/clayPlotter.
        """
        # Validate data types
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input 'data' must be a Pandas DataFrame.")
        if not isinstance(location_col, str) or not location_col:
             raise ValueError("'location_col' must be a non-empty string.")
        if not isinstance(value_col, str) or not value_col:
             raise ValueError("'value_col' must be a non-empty string.")
        if location_col not in data.columns:
             raise ValueError(f"Location column '{location_col}' not found in data columns: {data.columns.tolist()}")
        if value_col not in data.columns:
             raise ValueError(f"Value column '{value_col}' not found in data columns: {data.columns.tolist()}")

        # Store configuration
        self.geography_key = geography_key
        self.data = data
        self.location_col = location_col
        self.value_col = value_col

        # Instantiate GeoDataManager internally
        self.geo_manager = GeoDataManager(cache_dir=cache_dir)

        # Validate the geography_key exists in the layer mapping constant
        if self.geography_key not in GEOGRAPHY_LAYERS:
            raise ValueError(f"Unknown geography_key: '{self.geography_key}'. Available keys: {list(GEOGRAPHY_LAYERS.keys())}")

        # Load the plotting configuration YAML based on the key
        self.plot_config = self._load_plot_config(self.geography_key)
        # Basic validation of loaded config structure (can be expanded)
        if not all(k in self.plot_config for k in ['figure', 'styling', 'main_map_settings']):
             logger.warning(f"Plot configuration for '{self.geography_key}' might be missing essential keys like 'figure', 'styling', 'main_map_settings'.")


    def _load_plot_config(self, config_key: str) -> dict:
        """Loads the plot configuration YAML file for the given key."""
        config_filename = f"{config_key}.yaml"
        logger.info(f"Attempting to load plot configuration: {config_filename}")
        try:
            # Access the resources directory within the installed package
            resource_ref = pkg_resources.files('clayPlotter') / 'resources' / config_filename
            if not resource_ref.is_file():
                 raise FileNotFoundError(f"Configuration file '{config_filename}' not found in package resources.")

            with resource_ref.open('r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if not isinstance(config, dict):
                    raise TypeError(f"Configuration file '{config_filename}' did not load as a dictionary.")
                logger.info(f"Successfully loaded plot configuration for key '{config_key}'")
                return config
        except FileNotFoundError as e:
             logger.error(f"Plot configuration file not found for key '{config_key}': {e}")
             raise ValueError(f"Could not find plot configuration for key '{config_key}'.") from e
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration for key '{config_key}': {e}")
            raise ValueError(f"Invalid YAML format in configuration for key '{config_key}'.") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred loading configuration for key '{config_key}': {e}")
            raise RuntimeError(f"Failed to load plot configuration for key '{config_key}'.") from e

    def _prepare_data(self, geo_join_column: str) -> gpd.GeoDataFrame:
        """
        Prepares data for plotting by merging geographical data with user data.
        """
        logger.debug(f"Preparing data for key '{self.geography_key}' using join column '{geo_join_column}'")
        # Retrieve the base geographical data using the stored key
        try:
            geo_df = self.geo_manager.get_geodataframe(geography_key=self.geography_key)
            logger.debug(f"Loaded GeoDataFrame with {len(geo_df)} features.")
        except (ValueError, FileNotFoundError, RuntimeError, Exception) as e:
            logger.error(f"Failed to load geographic data for key '{self.geography_key}'", exc_info=True)
            raise ValueError(f"Failed to load geographic data for key '{self.geography_key}': {e}") from e

        if not isinstance(geo_df, gpd.GeoDataFrame):
             raise TypeError(f"GeoDataManager did not return a GeoDataFrame for key '{self.geography_key}'.")

        # Validate columns exist before merging
        if geo_join_column not in geo_df.columns:
            raise ValueError(f"Geo join column '{geo_join_column}' not found in GeoDataFrame columns: {geo_df.columns.tolist()}")
        if self.location_col not in self.data.columns:
            raise ValueError(f"User data join column '{self.location_col}' not found in DataFrame columns: {self.data.columns.tolist()}")
        if self.value_col not in self.data.columns:
             raise ValueError(f"Data column '{self.value_col}' not found in DataFrame columns: {self.data.columns.tolist()}")

        # Perform the merge
        logger.debug(f"Merging geo data on '{geo_join_column}' with user data on '{self.location_col}'")
        data_to_merge = self.data[[self.location_col, self.value_col]].copy()
        # Ensure join columns have compatible types if possible (e.g., both strings)
        try:
             # Convert both join columns to string for robust merging
             geo_df[geo_join_column] = geo_df[geo_join_column].astype(str).str.strip()
             data_to_merge[self.location_col] = data_to_merge[self.location_col].astype(str).str.strip()
        except Exception as e:
             logger.warning(f"Could not ensure string types for join columns: {e}")

        merged_gdf = geo_df.merge(data_to_merge, left_on=geo_join_column, right_on=self.location_col, how='left')
        logger.debug(f"Merge resulted in {len(merged_gdf)} features.")

        # Check if merge was successful and resulted in data
        if merged_gdf.empty:
            logger.warning(f"Merge between GeoDataFrame (on '{geo_join_column}') and DataFrame (on '{self.location_col}') resulted in an empty GeoDataFrame.")

        # Add check for completely failed merge (all values in value_col are NaN after merge)
        if self.value_col in merged_gdf.columns and merged_gdf[self.value_col].isnull().all():
             logger.warning(f"All values in data column '{self.value_col}' are null after merge. Check join columns ('{geo_join_column}' vs '{self.location_col}') and data content.")

        return merged_gdf

    # --- Labeling Helper Method ---
    def _add_labels(self, gdf: gpd.GeoDataFrame, ax: Axes, label_config: dict, level1_code_col: str | None):
        """Adds labels or annotations to the map based on configuration."""
        logger.info("Adding labels based on configuration...")
        if not label_config.get('add_labels', False) or not level1_code_col or level1_code_col not in gdf.columns:
            logger.info("Labeling skipped: 'add_labels' is false, 'level1_code_column' is not defined, or column not found in data.")
            return

        # --- Get Label Settings from Config ---
        value_format = label_config.get('value_format', "{:.0f}")
        label_format = label_config.get('label_format', "{code} - {value}")
        na_value_text = label_config.get('na_value_text', "N/A")
        label_fontsize = label_config.get('label_fontsize', 7)
        annotation_fontsize = label_config.get('annotation_fontsize', 6)
        label_bbox_style = label_config.get('label_bbox_style', None)
        annotation_bbox_style = label_config.get('annotation_bbox_style', None)
        annotation_arrowprops = label_config.get('annotation_arrowprops', None)

        # Get offsets directly, default to empty dict if not found
        offsets = label_config.get('offsets', {})
        clipped_regions = label_config.get('clipped_regions', {})
        logger.debug(f"Offsets loaded from config: {list(offsets.keys())}") # Log loaded offset keys

        # --- Iterate and Add Labels/Annotations ---
        for idx, row in gdf.iterrows():
            # Ensure the code column exists and get the code, converting to string
            if level1_code_col not in row or pd.isna(row[level1_code_col]):
                logger.warning(f"Skipping label for row index {idx}: Missing or invalid code in column '{level1_code_col}'.")
                continue
            code = str(row[level1_code_col]).strip() # Ensure code is string and stripped for dict lookup

            # Ensure value column exists for formatting
            if self.value_col not in row:
                 logger.warning(f"Skipping label for code '{code}': Value column '{self.value_col}' not found in row.")
                 continue
            value = row[self.value_col]
            geometry = row['geometry']

            if pd.isna(geometry):
                logger.warning(f"Skipping label for code '{code}': Missing geometry.")
                continue

            # Format label text
            value_str = na_value_text if pd.isna(value) else value_format.format(value)
            label_text = label_format.format(code=code, value=value_str)

            # Determine base placement point (use representative_point for robustness)
            try:
                # Ensure geometry is valid before calculating representative point
                if not geometry.is_valid:
                    geometry = geometry.buffer(0) # Attempt to fix invalid geometry
                    if not geometry.is_valid:
                         logger.warning(f"Skipping label for code '{code}': Invalid geometry even after buffer(0).")
                         continue
                base_point = geometry.representative_point()
                base_x, base_y = base_point.x, base_point.y
            except Exception as e:
                logger.warning(f"Skipping label for code '{code}': Error calculating representative point - {e}")
                continue


            # --- Apply Placement Logic ---
            try:
                # Check if code exists in the offsets dictionary for annotation
                logger.debug(f"Checking offsets for code: '{code}' (type: {type(code)})")
                if code in offsets:
                    logger.debug(f"Found offset for code '{code}'. Applying annotation.")
                    offset_coords = offsets[code]
                    if isinstance(offset_coords, list) and len(offset_coords) == 2:
                        offset_x, offset_y = offset_coords
                        # Use data coordinate offsets from YAML for text placement
                        ax.annotate(label_text,
                                    xy=(base_x, base_y), # Point arrow to representative point
                                    xytext=(base_x + offset_x, base_y + offset_y), # Place text at offset in data coords
                                    fontsize=annotation_fontsize,
                                    ha='center', va='center', # Center alignment for data coords
                                    arrowprops=annotation_arrowprops,
                                    bbox=annotation_bbox_style)
                    else:
                         logger.warning(f"Invalid offset format for code '{code}': {offset_coords}. Placing label directly.")
                         ax.text(base_x, base_y, label_text, fontsize=label_fontsize, ha='center', va='center', bbox=label_bbox_style)

                elif code in clipped_regions:
                    logger.debug(f"Applying clipping for code '{code}'.")
                    # --- Text within Clipped Region ---
                    clip_side, clip_percentage = clipped_regions[code]
                    minx, miny, maxx, maxy = geometry.bounds
                    width = maxx - minx
                    height = maxy - miny
                    clip_poly = None

                    # Create a clipping polygon based on the side and percentage
                    if clip_side == 'top':
                        clip_poly = Polygon([(minx, maxy - height * clip_percentage), (maxx, maxy - height * clip_percentage), (maxx, maxy), (minx, maxy)])
                    elif clip_side == 'bottom':
                        clip_poly = Polygon([(minx, miny), (maxx, miny), (maxx, miny + height * clip_percentage), (minx, miny + height * clip_percentage)])
                    elif clip_side == 'left':
                        clip_poly = Polygon([(minx, miny), (minx + width * clip_percentage, miny), (minx + width * clip_percentage, maxy), (minx, maxy)])
                    elif clip_side == 'right':
                        clip_poly = Polygon([(maxx - width * clip_percentage, miny), (maxx, miny), (maxx, maxy), (maxx - width * clip_percentage, maxy)])

                    if clip_poly:
                        try:
                            clipped_geom = geometry.intersection(clip_poly)
                            if not clipped_geom.is_empty:
                                # Place label within the representative point of the clipped area
                                placement_point = clipped_geom.representative_point()
                                ax.text(placement_point.x, placement_point.y, label_text,
                                        fontsize=label_fontsize, ha='center', va='center',
                                        bbox=label_bbox_style)
                                logger.debug(f"Added clipped label for region '{code}'.")
                            else:
                                logger.warning(f"Clipping resulted in empty geometry for code '{code}'. Placing at base point.")
                                ax.text(base_x, base_y, label_text,
                                        fontsize=label_fontsize, ha='center', va='center',
                                        bbox=label_bbox_style)
                        except Exception as clip_err:
                             logger.warning(f"Error during clipping or placement for code '{code}': {clip_err}. Placing at base point.")
                             ax.text(base_x, base_y, label_text,
                                     fontsize=label_fontsize, ha='center', va='center',
                                     bbox=label_bbox_style)
                    else:
                         logger.warning(f"Invalid clip_side '{clip_side}' for code '{code}'. Placing at base point.")
                         ax.text(base_x, base_y, label_text,
                                 fontsize=label_fontsize, ha='center', va='center',
                                 bbox=label_bbox_style)

                else:
                    # --- Default Text Placement ---
                    logger.debug(f"Applying default placement for code '{code}'.") # Log default placement
                    ax.text(base_x, base_y, label_text,
                            fontsize=label_fontsize, ha='center', va='center',
                            bbox=label_bbox_style)

            except Exception as label_err:
                 logger.error(f"Failed to add label/annotation for code '{code}': {label_err}", exc_info=True)

    # --- Plotting Method ---
    def plot(self, geo_join_column: str = 'name', title: str | None = None, **kwargs) -> tuple[plt.Figure, Axes]:
        """
        Generates and returns the choropleth map based on the data and configuration
        provided during initialization.
        """
        logger.info(f"Starting plot generation for geography key: '{self.geography_key}'")

        # --- Get Config Settings ---
        fig_config = self.plot_config.get('figure', {})
        style_config = self.plot_config.get('styling', {})
        main_map_config = self.plot_config.get('main_map_settings', {})
        inset_regions = self.plot_config.get('inset_level1_regions', [])
        label_config = self.plot_config.get('label_settings', {})
        level1_code_col = label_config.get('level1_code_column', None) # Needed early for filtering/labeling

        # --- Prepare Data ---
        try:
            # Use the geo_join_column argument passed to the plot function
            merged_gdf = self._prepare_data(geo_join_column=geo_join_column)
        except (ValueError, TypeError) as e:
            logger.error("Data preparation failed.", exc_info=True)
            raise ValueError(f"Data preparation failed for geography '{self.geography_key}': {e}") from e

        if merged_gdf.empty:
             logger.warning("Plotting skipped as the merged GeoDataFrame is empty.")
             fig, ax = plt.subplots(1, 1, figsize=fig_config.get('figsize', (10, 10)))
             plot_title = title if title is not None else fig_config.get('title', f"Choropleth Map ({self.geography_key})")
             ax.set_title(f"{plot_title} (No data to plot)")
             ax.set_axis_off()
             return fig, ax

        # --- Create Figure and Main Axes ---
        fig, ax = plt.subplots(1, 1, figsize=fig_config.get('figsize', (10, 10)))
        plot_title = title if title is not None else fig_config.get('title', f"Choropleth Map ({self.geography_key})")
        fig.suptitle(plot_title) # Use suptitle for overall figure

        # Set main map background (Limits and aspect ratio applied *after* potential reprojection)
        ax.set_facecolor(style_config.get('ocean_color', 'aliceblue'))
        ax.set_xticks([])
        ax.set_yticks([])

        # --- Define Base Plotting Arguments from Config ---
        base_plot_kwargs = {
            'column': self.value_col,
            'cmap': style_config.get('cmap', 'viridis'),
            'linewidth': style_config.get('level1_linewidth', 0.5),
            'edgecolor': style_config.get('level1_edge_color', '0.8'),
            'missing_kwds': {
                'color': style_config.get('missing_color', 'lightgrey'),
                'edgecolor': style_config.get('level1_edge_color', 'darkgrey'),
                'hatch': style_config.get('missing_hatch', '///'),
                'label': style_config.get('missing_label', 'Missing Data')
             }
        }
        legend_kwargs_config = {
            'label': self.value_col,
            'orientation': style_config.get('colorbar_orientation', 'vertical'),
            'fraction': style_config.get('colorbar_fraction', 0.046),
            'pad': style_config.get('colorbar_pad', 0.02),
        }
        main_plot_kwargs = base_plot_kwargs.copy()
        main_plot_kwargs['legend'] = style_config.get('legend', True)
        main_plot_kwargs['legend_kwds'] = legend_kwargs_config
        main_plot_kwargs.update(kwargs)

        inset_plot_kwargs = base_plot_kwargs.copy()
        inset_plot_kwargs['legend'] = False
        inset_plot_kwargs.update(kwargs)

        # --- Filter and Reproject Main Data ---
        logger.info("Filtering and potentially reprojecting main map area...")
        main_gdf = gpd.GeoDataFrame() # Initialize
        target_crs = None # Initialize target CRS
        original_crs = None # Store original CRS before reprojection

        try:
            # --- Filter by Country Code First ---
            country_codes = self.plot_config.get('country_codes')
            country_code_col = self.plot_config.get('data_hints', {}).get('country_code_column', 'iso_a2')
            filtered_by_country_gdf = merged_gdf # Start with the merged data

            if country_codes and country_code_col in merged_gdf.columns:
                filtered_by_country_gdf = merged_gdf[merged_gdf[country_code_col].isin(country_codes)]
                logger.info(f"Filtered data to {len(filtered_by_country_gdf)} features based on country_codes: {country_codes}")
            elif country_codes:
                 logger.warning(f"Could not filter by country_codes: Column '{country_code_col}' not found.")
                 # Proceed with potentially unfiltered data if country filtering fails

            # --- Filter by Level 1 Codes (Optional, applied to country-filtered data) ---
            main_codes = self.plot_config.get('main_level1_codes')
            if main_codes and level1_code_col and level1_code_col in filtered_by_country_gdf.columns:
                 main_gdf = filtered_by_country_gdf[filtered_by_country_gdf[level1_code_col].astype(str).isin([str(c) for c in main_codes])]
                 logger.info(f"Filtered main map data further to {len(main_gdf)} features based on 'main_level1_codes'.")
            else:
                 main_gdf = filtered_by_country_gdf # Use country-filtered data if no L1 codes specified/applicable
                 if main_codes:
                      logger.warning("Could not filter main map further by 'main_level1_codes': 'level1_code_column' missing or not found.")

            # Store original CRS before potential reprojection
            original_crs = main_gdf.crs
            if not original_crs:
                 logger.warning("Main GDF has no CRS set, assuming EPSG:4326.")
                 original_crs = 'EPSG:4326'
                 main_gdf.set_crs(original_crs, inplace=True)

            # Reproject if specified in config
            target_crs = main_map_config.get('target_crs') # Read from config
            if target_crs:
                 logger.info(f"Reprojecting main map data from {original_crs} to {target_crs} based on configuration.")
                 try:
                      main_gdf = main_gdf.to_crs(target_crs)
                 except Exception as reproj_err:
                      logger.error(f"Failed to reproject main_gdf to {target_crs}: {reproj_err}", exc_info=True)
                      target_crs = None # Fallback to no projection if reprojection fails
            else:
                 logger.info("No target_crs specified in config, using original projection.")

        except Exception as filter_err:
             logger.error(f"Error during main GDF filtering: {filter_err}", exc_info=True)
             main_gdf = merged_gdf # Fallback for now

        # --- Plot Main Data ---
        if not main_gdf.empty:
             ax = main_gdf.plot(ax=ax, **main_plot_kwargs)
             # Set aspect after plotting only if NOT using a specific projection
             if not target_crs:
                  ax.set_aspect('equal', adjustable='box')
             # Apply limits *after* plotting main data
             if target_crs: # Use bounds of reprojected data for projected maps
                  minx, miny, maxx, maxy = main_gdf.total_bounds
                  # Add a small buffer to the bounds for projected maps
                  x_buffer = (maxx - minx) * 0.02
                  y_buffer = (maxy - miny) * 0.02
                  ax.set_xlim(minx - x_buffer, maxx + x_buffer)
                  ax.set_ylim(miny - y_buffer, maxy + y_buffer)
                  logger.info(f"Set projected map limits based on data bounds: xlim=({minx-x_buffer}, {maxx+x_buffer}), ylim=({miny-y_buffer}, {maxy+y_buffer})")
             elif 'xlim' in main_map_config: # Use config limits for non-projected maps
                  ax.set_xlim(main_map_config['xlim'])
             elif 'ylim' in main_map_config:
                  ax.set_ylim(main_map_config['ylim'])
        else:
             logger.warning("Main GeoDataFrame is empty after filtering/reprojection, skipping main plot.")


        # --- Plot Lakes (if configured) ---
        lakes_gdf = gpd.GeoDataFrame() # Initialize
        lakes_to_plot = gpd.GeoDataFrame() # Initialize
        if main_map_config.get('include_lakes', False):
            logger.info("Plotting lakes...")
            try:
                lakes_gdf = self.geo_manager.get_geodataframe(geography_key='ne_lakes')
                lake_names_to_plot = main_map_config.get('include_lake_names')
                lake_name_col = self.plot_config.get('data_hints', {}).get('lake_name_column', 'name')

                if lake_names_to_plot and lake_name_col in lakes_gdf.columns:
                    lakes_to_plot = lakes_gdf[lakes_gdf[lake_name_col].isin(lake_names_to_plot)]
                    logger.info(f"Filtered to plot {len(lakes_to_plot)} specific lakes.")
                else:
                    lakes_to_plot = lakes_gdf
                    if lake_names_to_plot:
                         logger.warning(f"Could not filter lakes by name: Column '{lake_name_col}' not found.")

                if not lakes_to_plot.empty:
                    # Reproject lakes if main map was reprojected
                    lakes_plot_gdf = lakes_to_plot.copy() # Use copy to avoid modifying original
                    if target_crs:
                         logger.info(f"Reprojecting lake data to {target_crs}")
                         try:
                              lake_original_crs = lakes_plot_gdf.crs
                              if not lake_original_crs:
                                   logger.warning("Lakes GDF has no CRS set, assuming original CRS of main GDF.")
                                   lake_original_crs = original_crs if original_crs else 'EPSG:4326'
                                   lakes_plot_gdf.set_crs(lake_original_crs, inplace=True)
                              lakes_plot_gdf = lakes_plot_gdf.to_crs(target_crs)
                         except Exception as lake_reproj_err:
                              logger.error(f"Failed to reproject lakes_gdf to {target_crs}: {lake_reproj_err}", exc_info=True)
                              lakes_plot_gdf = lakes_to_plot # Plot original if reprojection fails

                    lakes_plot_gdf.plot(
                        ax=ax,
                        color=style_config.get('lake_color', 'lightblue'),
                        edgecolor=style_config.get('lake_edge_color', 'grey'),
                        linewidth=style_config.get('lake_linewidth', 0.3),
                        zorder=2
                    )
            except Exception as e:
                logger.error(f"Failed to load or plot lakes: {e}", exc_info=True)

        # --- Plot Neighboring Level 1 Regions (if configured) ---
        if main_map_config.get('include_neighboring_level1', False):
            logger.info("Plotting neighboring level 1 regions...")
            try:
                neighbor_codes = self.plot_config.get('data_hints', {}).get('neighboring_country_codes', [])
                country_code_col = self.plot_config.get('data_hints', {}).get('country_code_column', 'iso_a2')

                if neighbor_codes:
                    # Fetch the more detailed 10m admin 1 layer for neighbors
                    base_admin1_gdf = self.geo_manager.get_geodataframe(geography_key="admin1_10m")

                    if country_code_col in base_admin1_gdf.columns:
                        neighbors_l1_gdf = base_admin1_gdf[base_admin1_gdf[country_code_col].isin(neighbor_codes)]
                        logger.info(f"Found {len(neighbors_l1_gdf)} potential neighboring level 1 features.")

                        if not neighbors_l1_gdf.empty:
                            # Reproject and clip neighbors_l1_gdf as before
                            neighbors_l1_plot_gdf = neighbors_l1_gdf.copy()
                            if target_crs:
                                # ... (reprojection logic as before) ...
                                try:
                                    neighbor_original_crs = neighbors_l1_plot_gdf.crs
                                    if not neighbor_original_crs:
                                        neighbor_original_crs = original_crs if original_crs else 'EPSG:4326'
                                        neighbors_l1_plot_gdf.set_crs(neighbor_original_crs, inplace=True)
                                    neighbors_l1_plot_gdf = neighbors_l1_plot_gdf.to_crs(target_crs)
                                except Exception as neighbor_reproj_err:
                                    logger.error(f"Failed to reproject neighbors_l1_gdf: {neighbor_reproj_err}", exc_info=True)
                                    neighbors_l1_plot_gdf = neighbors_l1_gdf

                            current_xlim = ax.get_xlim()
                            current_ylim = ax.get_ylim()
                            try:
                                # ... (clipping logic as before) ...
                                if neighbors_l1_plot_gdf.crs and neighbors_l1_plot_gdf.crs.is_projected:
                                     bbox_poly = Polygon([(current_xlim[0], current_ylim[0]), (current_xlim[1], current_ylim[0]), (current_xlim[1], current_ylim[1]), (current_xlim[0], current_ylim[1])])
                                     clip_box = gpd.GeoDataFrame([1], geometry=[bbox_poly], crs=neighbors_l1_plot_gdf.crs)
                                     neighbors_l1_plot_gdf = gpd.clip(neighbors_l1_plot_gdf, clip_box)
                                else:
                                     neighbors_l1_plot_gdf = neighbors_l1_plot_gdf.cx[current_xlim[0]:current_xlim[1], current_ylim[0]:current_ylim[1]]
                            except Exception as clip_err:
                                 logger.warning(f"Could not clip L1 neighbors to map extent: {clip_err}")

                            if not neighbors_l1_plot_gdf.empty:
                                neighbors_l1_plot_gdf.plot(
                                    ax=ax,
                                    color=style_config.get('neighbor_l1_fill_color', 'none'),
                                    edgecolor=style_config.get('neighbor_l1_edgecolor', 'grey'),
                                    linewidth=style_config.get('neighbor_l1_linewidth', 0.5),
                                    linestyle=style_config.get('neighbor_l1_linestyle', '--'),
                                    zorder=1
                                )
                            else:
                                logger.info("No neighboring L1 regions fall within the current map extent after clipping.")
                    else:
                         logger.warning(f"Cannot plot L1 neighbors: Country code column '{country_code_col}' not found in base layer.")
                else:
                    logger.info("No neighboring country codes defined for L1 neighbors.")

            except Exception as e:
                logger.error(f"Failed to load or plot neighboring L1 regions: {e}", exc_info=True)

        # --- Plot Neighboring Countries (if configured) ---
        if main_map_config.get('include_neighboring_countries', False):
             logger.info("Plotting neighboring countries...")
             try:
                neighbor_codes = self.plot_config.get('data_hints', {}).get('neighboring_country_codes', [])
                # Use a specific column name for admin 0 layer, default to ADM0_A3 if not in hints
                admin0_country_code_col = self.plot_config.get('data_hints', {}).get('admin0_country_code_column', 'ADM0_A3')

                if neighbor_codes:
                    # Fetch the admin 0 (countries) layer
                    # Ensure 'world_countries' key exists in GEOGRAPHY_LAYERS
                    if 'world_countries' in GEOGRAPHY_LAYERS:
                        base_countries_gdf = self.geo_manager.get_geodataframe(geography_key='world_countries')

                        if admin0_country_code_col in base_countries_gdf.columns:
                            neighbor_countries_gdf = base_countries_gdf[base_countries_gdf[admin0_country_code_col].isin(neighbor_codes)]
                            logger.info(f"Found {len(neighbor_countries_gdf)} potential neighboring country features.")

                            if not neighbor_countries_gdf.empty:
                                # Reproject and clip neighbor countries similar to L1 neighbors
                                neighbor_countries_plot_gdf = neighbor_countries_gdf.copy()
                                if target_crs:
                                    # ... (reprojection logic) ...
                                    try:
                                        nc_original_crs = neighbor_countries_plot_gdf.crs
                                        if not nc_original_crs:
                                            nc_original_crs = original_crs if original_crs else 'EPSG:4326'
                                            neighbor_countries_plot_gdf.set_crs(nc_original_crs, inplace=True)
                                        neighbor_countries_plot_gdf = neighbor_countries_plot_gdf.to_crs(target_crs)
                                    except Exception as nc_reproj_err:
                                        logger.error(f"Failed to reproject neighbor_countries_gdf: {nc_reproj_err}", exc_info=True)
                                        neighbor_countries_plot_gdf = neighbor_countries_gdf

                                current_xlim = ax.get_xlim()
                                current_ylim = ax.get_ylim()
                                try:
                                    # ... (clipping logic) ...
                                    if neighbor_countries_plot_gdf.crs and neighbor_countries_plot_gdf.crs.is_projected:
                                         bbox_poly = Polygon([(current_xlim[0], current_ylim[0]), (current_xlim[1], current_ylim[0]), (current_xlim[1], current_ylim[1]), (current_xlim[0], current_ylim[1])])
                                         clip_box = gpd.GeoDataFrame([1], geometry=[bbox_poly], crs=neighbor_countries_plot_gdf.crs)
                                         neighbor_countries_plot_gdf = gpd.clip(neighbor_countries_plot_gdf, clip_box)
                                    else:
                                         neighbor_countries_plot_gdf = neighbor_countries_plot_gdf.cx[current_xlim[0]:current_xlim[1], current_ylim[0]:current_ylim[1]]
                                except Exception as nc_clip_err:
                                     logger.warning(f"Could not clip neighbor countries to map extent: {nc_clip_err}")

                                if not neighbor_countries_plot_gdf.empty:
                                    neighbor_countries_plot_gdf.plot(
                                        ax=ax,
                                        color=style_config.get('country_color', 'lightgrey'), # Use country styling
                                        edgecolor=style_config.get('country_edge_color', 'darkgrey'),
                                        linewidth=style_config.get('country_linewidth', 0.5),
                                        zorder=0 # Plot underneath everything else
                                    )
                                else:
                                     logger.info("No neighboring countries fall within the current map extent after clipping.")
                        else:
                             logger.warning(f"Cannot plot neighbor countries: Country code column '{admin0_country_code_col}' not found in countries layer.")
                    else:
                         logger.warning("Cannot plot neighbor countries: 'world_countries' key not defined in GEOGRAPHY_LAYERS.")
                else:
                     logger.info("No neighboring country codes defined in config, skipping neighbor country plot.")
             except Exception as e:
                 logger.error(f"Failed to load or plot neighboring countries: {e}", exc_info=True)


        # --- Plot Insets ---
        logger.info(f"Processing {len(inset_regions)} inset regions...")
        if not level1_code_col and inset_regions:
             logger.warning("`level1_code_column` not found in config's label_settings. Cannot filter data for insets.")

        for inset_cfg in inset_regions:
            codes = inset_cfg.get('codes')
            location = inset_cfg.get('location')
            xlim = inset_cfg.get('xlim')
            ylim = inset_cfg.get('ylim')

            if not codes or not location or not level1_code_col:
                logger.warning(f"Skipping inset due to missing 'codes', 'location', or unavailable 'level1_code_column': {inset_cfg}")
                continue

            logger.info(f"Creating inset for codes: {codes}")
            try:
                bbox_transform_val = ax.transAxes if location.get("bbox_transform") == 'ax.transAxes' else None
                ax_inset = inset_axes(ax,
                                      width=location.get("width", "20%"),
                                      height=location.get("height", "20%"),
                                      loc=location.get("loc", 'lower left'),
                                      bbox_to_anchor=location.get("bbox_to_anchor", (0, 0, 1, 1)),
                                      bbox_transform=bbox_transform_val,
                                      borderpad=location.get("borderpad", 0))

                # Filter from the original merged_gdf before any reprojection
                inset_data = merged_gdf[merged_gdf[level1_code_col].astype(str).isin([str(c) for c in codes])]

                if inset_data.empty:
                     logger.warning(f"No data found for inset codes {codes} using column '{level1_code_col}'. Skipping plot.")
                     ax_inset.set_visible(False)
                     continue

                # Plot inset data (no legend)
                ax_inset = inset_data.plot(ax=ax_inset, **inset_plot_kwargs)

                # Set limits and appearance for inset (using geographic coords)
                if xlim: ax_inset.set_xlim(xlim)
                if ylim: ax_inset.set_ylim(ylim)
                ax_inset.set_xticks([])
                ax_inset.set_yticks([])
                ax_inset.set_aspect('equal', adjustable='box') # Insets use geographic
                ax_inset.set_facecolor(style_config.get('ocean_color', 'aliceblue'))

                # Optionally plot lakes in inset (using original lakes_to_plot)
                if inset_cfg.get('include_lakes', False) and not lakes_to_plot.empty:
                     # Clip original lakes data to inset bounds
                     lakes_inset = lakes_to_plot.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]] if xlim and ylim else lakes_to_plot
                     if not lakes_inset.empty:
                          lakes_inset.plot(
                              ax=ax_inset,
                              color=style_config.get('lake_color', 'lightblue'),
                              edgecolor=style_config.get('lake_edge_color', 'grey'),
                              linewidth=style_config.get('lake_linewidth', 0.3),
                              zorder=2
                          )
            except Exception as e:
                 logger.error(f"Failed to create or plot inset for codes {codes}: {e}", exc_info=True)


        # --- Add Labels (Call the helper method) ---
        country_codes_to_label = self.plot_config.get('country_codes')
        country_code_col = self.plot_config.get('data_hints', {}).get('country_code_column', 'iso_a2')

        if not main_gdf.empty: # Use the potentially reprojected main_gdf for labeling base
            gdf_to_label = main_gdf.copy() # Use copy to avoid modifying main_gdf
            # Filter based on country code *after* potential reprojection
            if country_codes_to_label and country_code_col in gdf_to_label.columns:
                gdf_to_label = gdf_to_label[gdf_to_label[country_code_col].isin(country_codes_to_label)]
                logger.info(f"Filtered data for labeling to {len(gdf_to_label)} features based on country_codes: {country_codes_to_label}")
            elif country_codes_to_label:
                 logger.warning(f"Could not filter data for labeling by country_codes: Column '{country_code_col}' not found.")

            # Labeling should happen on the reprojected data if target_crs is set
            if not gdf_to_label.empty:
                 self._add_labels(gdf_to_label, ax, label_config, level1_code_col)
            else:
                 logger.warning("GeoDataFrame for labeling is empty after filtering; skipping labeling.")

        # TODO: Add logic to call _add_labels for inset_data on ax_inset if needed

        # --- Final Touches ---
        if 'tight_layout_rect' in fig_config:
             try:
                 fig.tight_layout(rect=fig_config['tight_layout_rect'])
             except Exception as e:
                  logger.warning(f"Failed to apply tight_layout: {e}")

        logger.info("Plot generation complete.")
        return fig, ax