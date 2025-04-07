import geopandas as gpd
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import pandas as pd
import yaml
import logging
import os
from shapely.geometry import Polygon
import importlib # Used for dynamic transform loading
import requests # Needed for downloading data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# +++ Data Preparation Function +++

def prepare_geo_data(data_dict, value_column_name, target_country_codes=['US'], resolution='110m', state_name_key='NAME', state_code_column='postal', neighbor_country_codes=['CA', 'MX']):
    """
    Downloads and prepares geographic data (target admin level 1 regions, lakes, countries, neighbors)
    from Natural Earth, merges input data, and returns GeoDataFrames.

    Args:
        data_dict (dict): A dictionary mapping region names (or other keys specified
                          by state_name_key) to values.
        value_column_name (str): The name to give the column holding the values from data_dict.
        target_country_codes (list): List of ISO A2 codes for the primary countries/regions to plot. Defaults to ['US'].
        resolution (str): The resolution for Natural Earth data ('10m', '50m', '110m'). Defaults to '110m'.
        state_name_key (str): The key in the data_dict representing the region name.
                               Defaults to 'NAME' assuming the dict keys match the shapefile's 'NAME' column after potential renaming.
        state_code_column (str): The expected column name for region codes (e.g., postal codes) in the
                                 Natural Earth data. Defaults to 'postal'.
        neighbor_country_codes (list): List of ISO A2 codes for neighboring countries whose L1 regions should be included. Defaults to ['CA', 'MX'].


    Returns:
        tuple: (target_level1_gdf, lakes_gdf, countries_gdf, neighbors_level1_gdf)
               GeoDataFrames for merged target regions, lakes, countries, and neighboring L1 regions.
               Returns None for a specific GeoDataFrame if processing fails for that part.
    """
    if not isinstance(data_dict, dict):
        raise ValueError("data_dict must be a dictionary.")
    if not data_dict:
        raise ValueError("data_dict cannot be empty.")

    allowed_resolutions = ['10m', '50m', '110m']
    if resolution not in allowed_resolutions:
        raise ValueError(f"Invalid resolution '{resolution}'. Allowed values are: {allowed_resolutions}")

    # Create DataFrame from input data_dict
    data_df = pd.DataFrame(list(data_dict.items()), columns=[state_name_key, value_column_name])

    states_gdf = None
    lakes_gdf = None
    countries_gdf = None # Initialize countries GeoDataFrame
    neighbors_states_gdf = None # Initialize neighbor states GeoDataFrame
    resources_dir = 'resources'

    # --- Define Paths and URLs using resolution ---
    states_file_name = f'ne_{resolution}_admin_1_states_provinces.zip'
    local_states_zip_path = os.path.join(resources_dir, states_file_name)
    states_url = f'https://naturalearth.s3.amazonaws.com/{resolution}_cultural/{states_file_name}'

    lakes_file_name = f'ne_{resolution}_lakes.zip'
    local_lakes_zip_path = os.path.join(resources_dir, lakes_file_name)
    lakes_url = f'https://naturalearth.s3.amazonaws.com/{resolution}_physical/{lakes_file_name}'

    # --- Countries Data (Using 50m for consistency) ---
    countries_file_name = 'ne_50m_admin_0_countries.zip'
    local_countries_zip_path = os.path.join(resources_dir, countries_file_name)
    countries_url = f'https://naturalearth.s3.amazonaws.com/50m_cultural/{countries_file_name}'

    # --- Process States ---
    try:
        if os.path.exists(local_states_zip_path):
            states_gdf = gpd.read_file(f"zip://{local_states_zip_path}")
        else:
            if not os.path.exists(resources_dir):
                logging.info(f"Creating directory: {resources_dir}")
                os.makedirs(resources_dir)
            logging.info(f"Downloading states data from {states_url}")
            response = requests.get(states_url, stream=True)
            response.raise_for_status()
            with open(local_states_zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            states_gdf = gpd.read_file(f"zip://{local_states_zip_path}")

        # Separate target regions from neighbors based on provided codes
        all_level1_gdf = states_gdf # Keep the full dataset temporarily

        # Filter for target countries
        states_gdf = all_level1_gdf[all_level1_gdf['iso_a2'].isin(target_country_codes)].copy()
        if states_gdf.empty:
             logging.error(f"No regions found matching target country codes: {target_country_codes}. Aborting.")
             return None, None, None, None # Return None for all if target is empty

        # Filter for neighbors (ensure neighbors are not also targets)
        actual_neighbor_codes = [code for code in neighbor_country_codes if code not in target_country_codes]
        neighbors_states_gdf = all_level1_gdf[all_level1_gdf['iso_a2'].isin(actual_neighbor_codes)].copy()

        logging.info(f"Filtered down to {len(states_gdf)} target admin regions for countries: {target_country_codes}.")
        logging.info(f"Filtered {len(neighbors_states_gdf)} neighbor L1 regions for countries: {actual_neighbor_codes}.")

        # Rename the state name column
        renamed = False
        name_cols = ['name', 'admin', 'gn_name']
        for col in name_cols:
            if col in states_gdf.columns:
                states_gdf = states_gdf.rename(columns={col: 'NAME'})
                renamed = True
                logging.info(f"Renamed '{col}' column to 'NAME'.")
                break
        if 'NAME' in states_gdf.columns and not renamed:
             logging.info("Column 'NAME' already exists.")
             renamed = True
        elif not renamed:
            logging.warning(f"Could not find expected state name column in {name_cols}. Merging might fail.")
            logging.warning(f"Available columns: {states_gdf.columns}")

        # Merge data
        if renamed and 'NAME' in states_gdf.columns:
            logging.info(f"Merging data based on 'NAME' column using value column '{value_column_name}'.")

            # Keep essential columns including geometry, the state code column, and the country code column
            keep_cols = ['NAME', 'geometry']
            country_code_col = 'iso_a2' # Standard column name in Natural Earth data for country code

            # Ensure state_code_column exists before trying to keep it
            current_state_code_column = None # Track the actual column name found
            if state_code_column and state_code_column in states_gdf.columns:
                 logging.info(f"Found state code column: '{state_code_column}'")
                 keep_cols.append(state_code_column)
                 current_state_code_column = state_code_column
            else:
                 logging.warning(f"Expected state code column '{state_code_column}' not found in states GeoDataFrame. State codes will not be available.")
                 # state_code_column remains the requested name, but it won't be added to keep_cols

            # Ensure country_code_column exists before trying to keep it
            if country_code_col in states_gdf.columns:
                 logging.info(f"Found country code column: '{country_code_col}'")
                 keep_cols.append(country_code_col)
            else:
                 logging.error(f"CRITICAL: Expected country code column '{country_code_col}' not found in states GeoDataFrame. Plotting function will likely fail.")

            # Select necessary columns before merge
            actual_keep_cols = [col for col in keep_cols if col in states_gdf.columns]
            if len(actual_keep_cols) < len(keep_cols):
                logging.warning(f"Some requested keep_cols were not found: {set(keep_cols) - set(actual_keep_cols)}")
            if not actual_keep_cols:
                logging.error("CRITICAL: No columns left to select for merging. Aborting merge.")
                states_gdf = None
            else:
                states_gdf_subset = states_gdf[actual_keep_cols].copy()

                # Perform the merge
                states_gdf = states_gdf_subset.merge(data_df, on='NAME', how='left')

                initial_count = len(states_gdf)
                # Keep all rows after the left merge. Missing data will have NaN in value_column_name.
                # states_gdf = states_gdf.dropna(subset=[value_column_name]) # DO NOT DROP MISSING
                # dropped_count = initial_count - len(states_gdf)
                # if dropped_count > 0:
                #      logging.info(f"Dropped {dropped_count} regions without matching data in data_dict.")
                logging.info(f"Kept all {initial_count} target regions after merge. Regions without matching data will have NaN values.")
                try:
                    states_gdf[value_column_name] = pd.to_numeric(states_gdf[value_column_name])
                    logging.info(f"Converted '{value_column_name}' column to numeric.")
                except ValueError:
                    logging.warning(f"Could not convert '{value_column_name}' column to numeric.")

        elif 'NAME' not in states_gdf.columns:
             logging.error("Skipping merge because 'NAME' column could not be identified.")
             states_gdf = None # Ensure GDF is None if merge skipped
        else: # renamed is False
             logging.error("Skipping merge due to state name column renaming issue.")
             states_gdf = None # Ensure GDF is None if merge skipped

    except Exception as e:
        logging.error(f"CRITICAL ERROR during states data processing: {e}", exc_info=True)
        states_gdf = None # Ensure states_gdf is None if state processing fails critically

    # --- Process Lakes ---
    try:
        if os.path.exists(local_lakes_zip_path):
            lakes_gdf = gpd.read_file(f"zip://{local_lakes_zip_path}")
        else:
            if not os.path.exists(resources_dir):
                logging.info(f"Creating directory: {resources_dir}")
                os.makedirs(resources_dir)
            logging.info(f"Downloading lakes data from {lakes_url}")
            response_lakes = requests.get(lakes_url, stream=True)
            response_lakes.raise_for_status()
            with open(local_lakes_zip_path, 'wb') as f:
                for chunk in response_lakes.iter_content(chunk_size=8192): f.write(chunk)
            lakes_gdf = gpd.read_file(f"zip://{local_lakes_zip_path}")
        logging.info(f"Loaded {len(lakes_gdf)} lake features.")
    except Exception as e:
        logging.error(f"Error during lakes data processing: {e}", exc_info=True)
        lakes_gdf = None

    # --- Process Countries ---
    try:
        if os.path.exists(local_countries_zip_path):
            countries_gdf = gpd.read_file(f"zip://{local_countries_zip_path}")
        else:
            if not os.path.exists(resources_dir):
                logging.info(f"Creating directory: {resources_dir}")
                os.makedirs(resources_dir)
            logging.info(f"Downloading countries data from {countries_url}")
            response_countries = requests.get(countries_url, stream=True)
            response_countries.raise_for_status()
            with open(local_countries_zip_path, 'wb') as f:
                for chunk in response_countries.iter_content(chunk_size=8192): f.write(chunk)
            countries_gdf = gpd.read_file(f"zip://{local_countries_zip_path}")
        logging.info(f"Loaded {len(countries_gdf)} country features.")
    except Exception as e:
        logging.error(f"Error during countries data processing: {e}", exc_info=True)
        countries_gdf = None

    # --- Log final CRS and Return ---
    if states_gdf is not None: logging.info(f"Final target_level1_gdf CRS: {states_gdf.crs}")
    else: logging.warning("Target Level 1 GeoDataFrame is None after processing.")
    if lakes_gdf is not None: logging.info(f"Final lakes_gdf CRS: {lakes_gdf.crs}")
    else: logging.warning("Lakes GeoDataFrame is None after processing.")
    if countries_gdf is not None: logging.info(f"Final countries_gdf CRS: {countries_gdf.crs}")
    else: logging.warning("Countries GeoDataFrame is None after processing.")
    if neighbors_states_gdf is not None: logging.info(f"Final neighbors_level1_gdf CRS: {neighbors_states_gdf.crs}")
    else: logging.warning("Neighbor Level 1 GeoDataFrame is None after processing.")

    # Return variable names match the updated docstring
    target_level1_gdf = states_gdf
    neighbors_level1_gdf = neighbors_states_gdf
    return target_level1_gdf, lakes_gdf, countries_gdf, neighbors_level1_gdf

# --- End Data Preparation Function ---

def _load_yaml_config(config_path):
    """Loads the YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.info(f"Successfully loaded configuration from {config_path}")
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {config_path}: {e}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred loading config {config_path}: {e}")
        raise

def _get_clipped_representative_point(geometry, clip_side, clip_percentage):
    """
    Calculates the representative point within a clipped portion of a geometry.
    (Helper function adapted from the original class)
    """
    try:
        minx, miny, maxx, maxy = geometry.bounds
        width = maxx - minx
        height = maxy - miny

        if clip_side == 'top':
            clip_miny = maxy - height * clip_percentage
            clip_coords = [(minx, clip_miny), (maxx, clip_miny), (maxx, maxy), (minx, maxy), (minx, clip_miny)]
        elif clip_side == 'bottom':
            clip_maxy = miny + height * clip_percentage
            clip_coords = [(minx, miny), (maxx, miny), (maxx, clip_maxy), (minx, clip_maxy), (minx, miny)]
        elif clip_side == 'left':
            clip_maxx = minx + width * clip_percentage
            clip_coords = [(minx, miny), (clip_maxx, miny), (clip_maxx, maxy), (minx, maxy), (minx, miny)]
        elif clip_side == 'right':
            clip_minx = maxx - width * clip_percentage
            clip_coords = [(clip_minx, miny), (maxx, miny), (maxx, maxy), (clip_minx, maxy), (clip_minx, miny)]
        else:
            logging.warning(f"Invalid clip_side '{clip_side}'. Falling back to full geometry.")
            return geometry.representative_point()

        clip_poly = Polygon(clip_coords)
        clipped_geom = geometry.intersection(clip_poly)

        if not clipped_geom.is_empty and clipped_geom.is_valid:
            # Ensure the point is actually *within* the clipped geometry
            point = clipped_geom.representative_point()
            if not clipped_geom.contains(point):
                 # If representative point falls outside (can happen with complex shapes), use centroid
                 point = clipped_geom.centroid
            return point
        else:
            logging.warning(f"Clipped geometry for side '{clip_side}' at {clip_percentage*100}% is empty or invalid for geometry bounds {geometry.bounds}. Falling back to full geometry representative point.")
            return geometry.representative_point() # Fallback

    except Exception as e:
        logging.error(f"Error calculating clipped representative point: {e}. Falling back.", exc_info=True)
        return geometry.representative_point() # Fallback on any error


def plot_choropleth_from_config(
    config_path,
    level1_gdf,
    value_column_name,
    lakes_gdf=None,
    countries_gdf=None,
    neighbors_level1_gdf=None):
    """
    Generates a choropleth map based on a YAML configuration file and input GeoDataFrames.

    Args:
        config_path (str): Path to the YAML configuration file.
        level1_gdf (GeoDataFrame): GeoDataFrame containing the Level 1 administrative boundaries
                                   and the data to plot. Must include geometry, the
                                   value_column_name, the level1_code_column specified in
                                   the config, and the country_code_column specified in the config.
        value_column_name (str): The name of the column in level1_gdf containing the values to plot.
        lakes_gdf (GeoDataFrame, optional): GeoDataFrame for lakes. Defaults to None.
        countries_gdf (GeoDataFrame, optional): GeoDataFrame for country boundaries. Defaults to None.
        neighbors_level1_gdf (GeoDataFrame, optional): GeoDataFrame for neighboring Level 1 boundaries
                                                      (e.g., Canadian provinces). Defaults to None.
    """
    config = _load_yaml_config(config_path)

    # --- Extract Config Sections ---
    # data_sel_cfg = config.get('data_selection', {}) # Removed - keys are top-level now
    inset_cfg = config.get('inset_level1_regions', [])
    main_map_cfg = config.get('main_map_settings', {})
    style_cfg = config.get('styling', {})
    label_cfg = config.get('label_settings', {})
    fig_cfg = config.get('figure', {})
    data_hints = config.get('data_hints', {}) # For column names

    # --- Validate Input Data ---
    if level1_gdf is None or level1_gdf.empty:
        logging.error("Cannot plot map: level1_gdf is not provided or is empty.")
        return
    if value_column_name not in level1_gdf.columns:
        logging.error(f"Cannot plot map: Value column '{value_column_name}' not found in level1_gdf.")
        return

    # Get essential column names from hints or defaults
    l1_code_col = label_cfg.get('level1_code_column', data_hints.get('level1_code_column', 'postal')) # Use label setting first
    l1_name_col = data_hints.get('level1_name_column', 'NAME')
    country_code_col = data_hints.get('country_code_column', 'iso_a2')

    if l1_code_col not in level1_gdf.columns:
         logging.error(f"Cannot plot map: Level 1 code column '{l1_code_col}' (from config) not found in level1_gdf.")
         return
    if country_code_col not in level1_gdf.columns:
         logging.error(f"Cannot plot map: Country code column '{country_code_col}' (from config) not found in level1_gdf.")
         return
    if l1_name_col not in level1_gdf.columns:
         logging.warning(f"Level 1 name column '{l1_name_col}' (from config) not found in level1_gdf. Hover info might be limited.")
         # Allow plotting to continue, but names might be missing

    # --- Prepare Data Subsets ---
    target_country_codes = config.get('country_codes', []) # Get directly from config
    if not target_country_codes:
        logging.error("Configuration error: 'data_selection.country_codes' must be specified.")
        return

    # Filter main level 1 data for the target countries
    target_l1_gdf = level1_gdf[level1_gdf[country_code_col].isin(target_country_codes)].copy()
    if target_l1_gdf.empty:
        logging.error(f"No Level 1 regions found for the specified country codes: {target_country_codes}")
        return
    logging.info(f"Filtered {len(target_l1_gdf)} Level 1 regions for countries: {target_country_codes}")

    # Identify all L1 codes designated for insets
    all_inset_codes = set()
    for inset in inset_cfg:
        all_inset_codes.update(inset.get('codes', []))

    # Determine L1 codes for the main map view
    main_view_codes_config = config.get('main_level1_codes') # Get directly from config
    if main_view_codes_config is None:
        # If null, assume all target L1 codes *except* those in insets
        main_view_gdf = target_l1_gdf[~target_l1_gdf[l1_code_col].isin(all_inset_codes)].copy()
        logging.info(f"Dynamically determined {len(main_view_gdf)} regions for main view (excluding inset codes: {all_inset_codes})")
    elif isinstance(main_view_codes_config, list):
        # If a list is provided, use only those codes
        # +++ DEBUG: Check target_l1_gdf right before filtering +++
        logging.info(f"DEBUG: target_l1_gdf shape before filtering by main_level1_codes: {target_l1_gdf.shape}")
        logging.info(f"DEBUG: Unique '{l1_code_col}' codes in target_l1_gdf: {sorted(target_l1_gdf[l1_code_col].unique())}")
        logging.info(f"DEBUG: Config main_level1_codes: {main_view_codes_config}")
        # +++ END DEBUG +++
        main_view_gdf = target_l1_gdf[target_l1_gdf[l1_code_col].isin(main_view_codes_config)].copy()
        logging.info(f"Using explicitly defined {len(main_view_gdf)} regions for main view from config.")
    else:
        logging.error("Configuration error: 'data_selection.main_level1_codes' must be null or a list of codes.")
        return

    if main_view_gdf.empty:
        logging.error("No Level 1 regions determined for the main map view based on config.")
        return

    # --- Setup Plot ---
    fig, main_ax = plt.subplots(1, 1, figsize=fig_cfg.get('figsize', (15, 10)))
    target_crs = main_view_gdf.crs # Use CRS of the primary data as the target
    logging.info(f"Using target CRS: {target_crs}")

    # Set background (ocean) color for the main axes
    ocean_color = style_cfg.get('ocean_color', 'aliceblue') # Default to aliceblue if not specified
    main_ax.set_facecolor(ocean_color)
    logging.info(f"Setting main axes background color to: {ocean_color}")
    # --- Normalization for Color Mapping ---
    try:
        # Use the full target L1 GDF for normalization range to ensure consistency across main map and insets
        min_val = target_l1_gdf[value_column_name].min()
        max_val = target_l1_gdf[value_column_name].max()
        if pd.isna(min_val) or pd.isna(max_val):
             logging.warning(f"Min or Max value for column '{value_column_name}' is NaN. Check data. Using default normalization.")
             norm = plt.Normalize()
        else:
             norm = plt.Normalize(vmin=min_val, vmax=max_val)
    except TypeError:
        logging.warning(f"Cannot determine numeric range for column '{value_column_name}'. Using default normalization.")
        norm = plt.Normalize() # Default normalization

    # --- Plot Background Layers (Countries, Neighbor L1s) ---
    zorder_counter = 1 # Start zorder for background elements

    # Plot Neighboring Countries
    plot_neighbor_countries = main_map_cfg.get('include_neighboring_countries', False)
    if plot_neighbor_countries and countries_gdf is not None and not countries_gdf.empty:
        logging.info("Plotting neighboring countries...")
        neighbor_codes = data_hints.get('neighboring_country_codes', [])
        country_name_col_hint = data_hints.get('neighboring_country_name_column', 'ADMIN')
        # Find the actual name column
        name_col = None
        possible_names = [country_name_col_hint, 'NAME', 'SOVEREIGNT', 'name', 'name_en']
        for col in possible_names:
            if col in countries_gdf.columns:
                name_col = col
                break

        if name_col and neighbor_codes:
            neighbors = countries_gdf[countries_gdf[name_col].isin(neighbor_codes)]
            if not neighbors.empty:
                neighbors_repr = neighbors
                if neighbors.crs != target_crs:
                    logging.warning(f"Countries CRS ({neighbors.crs}) differs from target CRS ({target_crs}). Reprojecting...")
                    try:
                        neighbors_repr = neighbors.to_crs(target_crs)
                    except Exception as e:
                        logging.error(f"Failed to reproject neighboring countries: {e}. Skipping.", exc_info=True)
                        neighbors_repr = None
                if neighbors_repr is not None:
                    neighbors_repr.plot(ax=main_ax,
                                        color=style_cfg.get('country_color', '#EAEAEA'),
                                        edgecolor=style_cfg.get('country_edge_color', 'darkgrey'),
                                        linewidth=style_cfg.get('country_linewidth', 0.5),
                                        zorder=zorder_counter)
                    zorder_counter += 1
            else:
                logging.warning(f"Could not find any countries matching names {neighbor_codes} using column '{name_col}'.")
        elif not name_col:
             logging.warning(f"Could not find a suitable name column ({possible_names}) in countries_gdf.")
        elif not neighbor_codes:
             logging.warning("No 'neighboring_country_codes' defined in config data_hints.")
    elif plot_neighbor_countries:
        logging.warning("Neighboring countries requested but countries_gdf is missing or empty.")

    # Plot Neighboring Level 1 Regions
    plot_neighbor_l1 = main_map_cfg.get('include_neighboring_level1', False)
    if plot_neighbor_l1 and neighbors_level1_gdf is not None and not neighbors_level1_gdf.empty:
        logging.info("Plotting neighboring Level 1 regions...")
        neighbors_l1_repr = neighbors_level1_gdf
        if neighbors_level1_gdf.crs != target_crs:
            logging.warning(f"Neighbor L1 CRS ({neighbors_level1_gdf.crs}) differs from target CRS ({target_crs}). Reprojecting...")
            try:
                neighbors_l1_repr = neighbors_level1_gdf.to_crs(target_crs)
            except Exception as e:
                logging.error(f"Failed to reproject neighboring L1 regions: {e}. Skipping.", exc_info=True)
                neighbors_l1_repr = None
        if neighbors_l1_repr is not None:
            neighbor_fill = style_cfg.get('neighbor_l1_fill_color', 'lightgrey') # Get fill color from config
            neighbors_l1_repr.plot(
                ax=main_ax,
                color=neighbor_fill, # Use the specified fill color
                edgecolor=style_cfg.get('neighbor_l1_edgecolor', 'darkgrey'),
                linewidth=style_cfg.get('neighbor_l1_linewidth', 0.5),
                linestyle=style_cfg.get('neighbor_l1_linestyle', '--'),
                zorder=zorder_counter
            )
            zorder_counter += 1
    elif plot_neighbor_l1:
        logging.warning("Neighboring Level 1 regions requested but neighbors_level1_gdf is missing or empty.")

    # --- Plot Main Map View ---
    logging.info(f"Plotting main map view with {len(main_view_gdf)} regions.")

    # Layer 1: Plot ALL main regions with missing_color fill and standard edge
    # This ensures all outlines are drawn correctly.
    main_view_gdf.plot(ax=main_ax,
                       color=style_cfg.get('missing_color', 'lightgrey'), # Use missing color for base fill
                       edgecolor=style_cfg.get('level1_edge_color', 'black'),
                       linewidth=style_cfg.get('level1_linewidth', 0.5),
                       zorder=zorder_counter)
    base_layer_zorder = zorder_counter
    zorder_counter += 1

    # Layer 2: Plot regions WITH data on top, using the colormap
    main_view_with_data = main_view_gdf.dropna(subset=[value_column_name])
    if not main_view_with_data.empty:
        logging.info(f"Plotting {len(main_view_with_data)} regions with data using colormap.")
        main_view_with_data.plot(column=value_column_name,
                                 ax=main_ax,
                                 legend=False, # Add colorbar manually later
                                 cmap=style_cfg.get('cmap', 'viridis'),
                                 norm=norm,
                                 # Use the same edge/linewidth as the base layer
                                 edgecolor=style_cfg.get('level1_edge_color', 'black'),
                                 linewidth=style_cfg.get('level1_linewidth', 0.5),
                                 # No missing_kwds needed here as we've already dropped NaNs
                                 zorder=zorder_counter # Plot on top of the base layer
                                )
        zorder_counter += 1
    else:
        logging.info("No regions with data found in the main view to plot with colormap.")


    # --- Plot Lakes on Main Map ---
    plot_main_lakes = main_map_cfg.get('include_lakes', False)
    if plot_main_lakes and lakes_gdf is not None and not lakes_gdf.empty:
        logging.info("Plotting lakes on main map...")
        lakes_repr = lakes_gdf
        if lakes_gdf.crs != target_crs:
            logging.warning(f"Lakes CRS ({lakes_gdf.crs}) differs from target CRS ({target_crs}). Reprojecting...")
            try:
                lakes_repr = lakes_gdf.to_crs(target_crs)
            except Exception as e:
                logging.error(f"Failed to reproject lakes for main map: {e}. Skipping.", exc_info=True)
                lakes_repr = None

        if lakes_repr is not None:
            # Filter lakes based on the include_lake_names list in main_map_settings
            include_lake_names = main_map_cfg.get('include_lake_names', [])
            lake_name_col_hint = data_hints.get('lake_name_column', 'name') # Still need hint for column name
            lakes_to_plot = None # Initialize to None

            if include_lake_names: # Only proceed if specific lake names are provided
                lake_name_col = None
                possible_lake_names = [lake_name_col_hint, 'name_en', 'gn_name', 'NAME']
                for col in possible_lake_names:
                    if col in lakes_repr.columns:
                        lake_name_col = col
                        break

                if lake_name_col:
                    logging.info(f"Filtering lakes for names specified in 'include_lake_names': {include_lake_names} using column '{lake_name_col}'")
                    try:
                        # Ensure case-insensitivity if needed, though Natural Earth names seem consistent
                        # For robustness, could convert both column and list to same case before comparison
                        filtered_lakes = lakes_repr[lakes_repr[lake_name_col].isin(include_lake_names)]
                        if not filtered_lakes.empty:
                            lakes_to_plot = filtered_lakes
                            logging.info(f"Found {len(lakes_to_plot)} features matching specified lake names.")
                        else:
                            logging.warning(f"No lakes found matching names specified in 'include_lake_names': {include_lake_names}. No lakes will be plotted.")
                    except Exception as e:
                        logging.error(f"Error filtering lakes by name: {e}. No lakes will be plotted.", exc_info=True)
                else:
                    logging.warning(f"Could not find suitable name column ({possible_lake_names}) in lakes_gdf to filter by name. No lakes will be plotted.")
            else:
                logging.info("'include_lake_names' is empty or not provided in main_map_settings. No specific lakes will be plotted.")

            # Only plot if lakes_to_plot is a valid GeoDataFrame
            if lakes_to_plot is not None and not lakes_to_plot.empty:
                lakes_to_plot.plot(ax=main_ax,
                                   color=style_cfg.get('lake_color', 'aliceblue'),
                                   edgecolor=style_cfg.get('lake_edge_color', 'darkblue'),
                                   linewidth=style_cfg.get('lake_linewidth', 0.3),
                                   zorder=zorder_counter)
                zorder_counter += 1
    elif plot_main_lakes:
        logging.warning("Lakes requested for main map but lakes_gdf is missing or empty.")

    # --- Set Main Map Limits and Appearance ---
    main_xlim = main_map_cfg.get('xlim')
    main_ylim = main_map_cfg.get('ylim')
    if main_xlim: main_ax.set_xlim(main_xlim)
    if main_ylim: main_ax.set_ylim(main_ylim)
    main_ax.set_xticks([])
    main_ax.set_yticks([])
    main_ax.set_title(fig_cfg.get('title', 'Choropleth Map'))

    # --- Create Insets ---
    inset_axes_list = [] # To store inset axes for later use (e.g., labels)
    for i, inset in enumerate(inset_cfg):
        inset_codes = inset.get('codes', [])
        if not inset_codes:
            logging.warning(f"Skipping inset {i+1} because no 'codes' were specified.")
            continue

        inset_gdf = target_l1_gdf[target_l1_gdf[l1_code_col].isin(inset_codes)]
        if inset_gdf.empty:
            logging.warning(f"Skipping inset {i+1} because no matching L1 regions found for codes: {inset_codes}")
            continue

        logging.info(f"Creating inset {i+1} for codes: {inset_codes}")
        loc_params = inset.get('location', {})

        # Dynamically get the transform function if specified as string
        bbox_transform_str = loc_params.get('bbox_transform', 'ax.transAxes')
        bbox_transform_func = main_ax.transAxes # Default
        if isinstance(bbox_transform_str, str):
             try:
                 # Assumes format like 'ax.transAxes' or potentially 'fig.transFigure' etc.
                 parts = bbox_transform_str.split('.')
                 obj = {'ax': main_ax, 'fig': fig}.get(parts[0]) # Extend if other transforms needed
                 if obj and len(parts) > 1:
                     transform_attr = getattr(obj, parts[1], None)
                     if callable(getattr(transform_attr, 'transform', None)): # Check if it behaves like a transform
                          bbox_transform_func = transform_attr
                     else:
                          logging.warning(f"Could not resolve transform '{bbox_transform_str}' to a valid transform object. Using default ax.transAxes.")
                 else:
                      logging.warning(f"Could not parse transform string '{bbox_transform_str}'. Using default ax.transAxes.")
             except Exception as e:
                 logging.warning(f"Error processing transform string '{bbox_transform_str}': {e}. Using default ax.transAxes.")
        elif bbox_transform_str is not None: # If it's not a string but not None, maybe it's already a transform? (Less likely from YAML)
             logging.warning(f"Unexpected type for bbox_transform: {type(bbox_transform_str)}. Using default ax.transAxes.")


        try:
            ax_inset = inset_axes(main_ax,
                                  width=loc_params.get('width', "20%"),
                                  height=loc_params.get('height', "20%"),
                                  loc=loc_params.get('loc', 'lower left'),
                                  bbox_to_anchor=loc_params.get('bbox_to_anchor', (0, 0, 1, 1)),
                                  bbox_transform=bbox_transform_func,
                                  borderpad=loc_params.get('borderpad', 0))
        except Exception as e:
            logging.error(f"Error creating inset axes for codes {inset_codes}: {e}", exc_info=True)
            continue # Skip this inset if axes creation fails

        inset_zorder = zorder_counter # Plot inset content at current level

        # Plot L1 regions in inset
        inset_gdf.plot(column=value_column_name, cmap=style_cfg.get('cmap', 'viridis'), norm=norm, ax=ax_inset,
                       edgecolor=style_cfg.get('level1_edge_color', 'black'),
                       linewidth=style_cfg.get('level1_linewidth', 0.5),
                       missing_kwds={'color': style_cfg.get('missing_color', 'lightgrey')},
                       zorder=inset_zorder)

        # Plot lakes in inset (optional)
        plot_inset_lakes = inset.get('include_lakes', False)
        if plot_inset_lakes and lakes_gdf is not None and not lakes_gdf.empty:
            lakes_inset_repr = lakes_gdf
            if lakes_gdf.crs != target_crs:
                # Assuming reprojection was attempted for main map, reuse if successful or try again
                try:
                    lakes_inset_repr = lakes_gdf.to_crs(target_crs)
                except Exception as e:
                    logging.error(f"Failed to reproject lakes for inset {inset_codes}: {e}. Skipping lakes in inset.", exc_info=True)
                    lakes_inset_repr = None
            if lakes_inset_repr is not None:
                 lakes_inset_repr.plot(ax=ax_inset,
                                       color=style_cfg.get('lake_color', 'aliceblue'),
                                       edgecolor=style_cfg.get('lake_edge_color', 'darkblue'),
                                       linewidth=style_cfg.get('lake_linewidth', 0.3),
                                       zorder=inset_zorder + 0.1) # Slightly above L1 regions

        # Set inset limits
        inset_xlim = inset.get('xlim')
        inset_ylim = inset.get('ylim')
        if inset_xlim: ax_inset.set_xlim(inset_xlim)
        if inset_ylim: ax_inset.set_ylim(inset_ylim)
        ax_inset.set_xticks([])
        ax_inset.set_yticks([])
        # Set background (ocean) color for the inset axes
        ax_inset.set_facecolor(ocean_color) # Use the same ocean color as the main map

        inset_axes_list.append({'ax': ax_inset, 'codes': inset_codes, 'gdf': inset_gdf})
        # Don't increment zorder_counter here, insets live 'on top' conceptually

    # --- Add Colorbar ---
    sm = plt.cm.ScalarMappable(cmap=style_cfg.get('cmap', 'viridis'), norm=norm)
    sm._A = [] # Dummy data
    cbar = fig.colorbar(sm, ax=main_ax,
                        orientation=style_cfg.get('colorbar_orientation', 'vertical'),
                        fraction=style_cfg.get('colorbar_fraction', 0.03),
                        pad=style_cfg.get('colorbar_pad', 0.02))
    cbar.set_label(value_column_name.replace('_', ' ').title())

    # --- Add Labels ---
    if label_cfg.get('add_labels', False):
        logging.info("Adding labels...")
        label_format = label_cfg.get('label_format', "{code} - {value}")
        value_format = label_cfg.get('value_format', "{:.0f}")
        na_text = label_cfg.get('na_value_text', "N/A")
        label_fontsize = label_cfg.get('label_fontsize', 7)
        annotation_fontsize = label_cfg.get('annotation_fontsize', 6)
        small_regions = label_cfg.get('small_regions', [])
        offsets = label_cfg.get('offsets', {})
        clipped_regions_dict = label_cfg.get('clipped_regions', {}) # Dict: code -> [side, percentage]
        label_bbox_style = label_cfg.get('label_bbox_style', None)
        annotation_bbox_style = label_cfg.get('annotation_bbox_style', None)
        annotation_arrowprops = label_cfg.get('annotation_arrowprops', None)
        inset_label_handling = label_cfg.get('inset_label_handling', {})

        # Label Main Map Regions
        logging.info("Labeling main map regions...")
        for idx, region in main_view_gdf.iterrows():
            region_code = region[l1_code_col]
            value = region[value_column_name]
            geometry = region.geometry

            if pd.isna(value):
                value_str = na_text
            else:
                try:
                    value_str = value_format.format(value)
                except (ValueError, TypeError):
                    value_str = str(value) # Fallback

            label_text = label_format.format(code=region_code, value=value_str)

            # Calculate label position
            point = None
            if region_code in clipped_regions_dict:
                clip_info = clipped_regions_dict[region_code]
                if isinstance(clip_info, list) and len(clip_info) == 2:
                    clip_side, clip_percentage = clip_info
                    point = _get_clipped_representative_point(geometry, clip_side, clip_percentage)
                    logging.debug(f"Using clipped ({clip_side}, {clip_percentage*100}%) point for {region_code}")
                else:
                    logging.warning(f"Invalid format for clipped_regions entry for {region_code}: {clip_info}. Using default point.")

            if point is None: # Default if not clipped or clipping failed
                point = geometry.representative_point()
                # Ensure point is within polygon, otherwise use centroid (handles edge cases)
                if not geometry.contains(point):
                    point = geometry.centroid
                logging.debug(f"Using default representative/centroid point for {region_code}")

            x, y = point.x, point.y

            # Plot label (annotation or direct text)
            if region_code in small_regions and region_code in offsets:
                offset_lon, offset_lat = offsets[region_code]
                target_x = x + offset_lon
                target_y = y + offset_lat
                main_ax.annotate(label_text, xy=(x, y), xytext=(target_x, target_y),
                                 arrowprops=annotation_arrowprops,
                                 fontsize=annotation_fontsize, ha='left', va='center',
                                 bbox=annotation_bbox_style)
            else:
                main_ax.text(x, y, label_text, fontsize=label_fontsize, ha='center', va='center',
                             bbox=label_bbox_style)

        # Label Inset Regions
        logging.info("Labeling inset regions...")
        for inset_info in inset_axes_list:
            ax_inset = inset_info['ax']
            inset_gdf = inset_info['gdf']
            inset_codes = inset_info['codes'] # List of codes in this inset

            for idx, region in inset_gdf.iterrows():
                region_code = region[l1_code_col]
                value = region[value_column_name]
                geometry = region.geometry

                if pd.isna(value): value_str = na_text
                else:
                    try: value_str = value_format.format(value)
                    except (ValueError, TypeError): value_str = str(value)

                label_text = label_format.format(code=region_code, value=value_str)

                # --- Special Inset Label Handling ---
                handled_specially = False
                if region_code in inset_label_handling:
                    handling_cfg = inset_label_handling[region_code]
                    positioning = handling_cfg.get('positioning')
                    placement = handling_cfg.get('placement', {})
                    ha = placement.get('ha', 'center')
                    va = placement.get('va', 'center')
                    x_rel = placement.get('x_rel') # Relative position (0-1) in inset x-axis
                    y_rel = placement.get('y_rel') # Relative position (0-1) in inset y-axis or 'centroid_y'

                    anchor_point = None
                    if positioning == 'relative_to_largest_polygon':
                         # Find the largest polygon (useful for multi-part geometries like Hawaii)
                         if geometry.geom_type == 'MultiPolygon':
                             largest_poly = max(geometry.geoms, key=lambda p: p.area)
                         else:
                             largest_poly = geometry # Assume single polygon
                         anchor_point = largest_poly.centroid # Default anchor is centroid
                         if handling_cfg.get('anchor_point') == 'representative_point':
                              anchor_point = largest_poly.representative_point()
                    elif positioning == 'geometry_centroid':
                         anchor_point = geometry.centroid
                    elif positioning == 'geometry_representative_point':
                         anchor_point = geometry.representative_point()

                    if anchor_point:
                        # Calculate target coordinates based on relative placement
                        inset_xlim = ax_inset.get_xlim()
                        inset_ylim = ax_inset.get_ylim()
                        target_x = inset_xlim[0] + (inset_xlim[1] - inset_xlim[0]) * x_rel if x_rel is not None else anchor_point.x
                        target_y = inset_ylim[0] + (inset_ylim[1] - inset_ylim[0]) * y_rel if isinstance(y_rel, (int, float)) else anchor_point.y

                        # Use annotate for potential arrows and consistent styling
                        ax_inset.annotate(label_text, xy=(anchor_point.x, anchor_point.y), xytext=(target_x, target_y),
                                          arrowprops=annotation_arrowprops if placement.get('use_arrow', True) else None, # Optional arrow
                                          fontsize=annotation_fontsize, ha=ha, va=va,
                                          bbox=annotation_bbox_style)
                        handled_specially = True
                    else:
                        logging.warning(f"Could not determine anchor point for special handling of {region_code}. Falling back to default.")

                # --- Default Inset Label Placement ---
                if not handled_specially:
                    point = geometry.representative_point()
                    if not geometry.contains(point): point = geometry.centroid # Fallback
                    ax_inset.text(point.x, point.y, label_text, fontsize=label_fontsize-1, ha='center', va='center', # Slightly smaller
                                  bbox=label_bbox_style)

    # --- Final Adjustments ---
    tight_layout_rect = fig_cfg.get('tight_layout_rect', [0, 0.03, 1, 0.95])
    try:
        # Use plt.tight_layout first, then adjust subplots if needed
        plt.tight_layout(rect=tight_layout_rect)
    except ValueError:
         logging.warning("tight_layout failed, likely due to complex inset arrangement. Consider adjusting layout manually or inset parameters.")
         # Alternative: plt.subplots_adjust can sometimes help, but requires careful tuning
         # plt.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.9)

    plt.show()
    logging.info("Map plotting complete.")


# Example Usage (requires data to be loaded beforehand)
if __name__ == '__main__':
    print("Choropleth Plotter Module")
    print("This module provides the function 'plot_choropleth_from_config'.")
    print("To use it, load your GeoDataFrames (Level 1 regions, lakes, countries, etc.)")
    print("and call the function with the path to your YAML config and the data.")
    print("\nExample (conceptual):")
    print("import geopandas as gpd")
    print("from choropleth_plotter import plot_choropleth_from_config")
    print("\n# Load your data (replace with actual loading logic)")
    print("# level1_data = gpd.read_file(...) # Must contain geometry, value col, L1 code col, country code col")
    print("# lakes_data = gpd.read_file(...)")
    print("# countries_data = gpd.read_file(...)")
    print("# neighbors_data = gpd.read_file(...)")
    print("\n# plot_choropleth_from_config(")
    print("#     config_path='resources/usa_states.yaml',")
    print("#     level1_gdf=level1_data,")
    print("#     value_column_name='your_value_column',")
    print("#     lakes_gdf=lakes_data,")
    print("#     countries_gdf=countries_data,")
    print("#     neighbors_level1_gdf=neighbors_data")
    print("# )")

    # Minimal test to check YAML loading (no plotting)
    try:
        cfg_test = _load_yaml_config('resources/usa_states.yaml')
        print("\nYAML config 'resources/usa_states.yaml' loaded successfully for basic check.")
    except Exception as e:
        print(f"\nError loading 'resources/usa_states.yaml' for basic check: {e}")