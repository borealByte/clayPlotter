# src/clayPlotter/mcp/services/map_service.py
import pandas as pd
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import traceback # For detailed error logging
import io
import base64
import os # Added os for path joining
from typing import List, Dict, Any, Optional, Tuple, Union # Added Tuple, Union
from uuid import UUID, uuid4

# Import core plotter and MCP components
from clayPlotter.l1_choropleth.plotter import ChoroplethPlotter # Corrected import path
from ..config import settings
from ..models.request_models import GenerateMapRequest, DataPoint, PlottingOptions # Use specific models
from ..models.response_models import GenerateMapResponse, ErrorDetail
from ..exceptions import ConfigurationError, ValidationError, MapGenerationError, ResourceNotFoundError # Added exceptions
from .config_service import ConfigService # Added ConfigService import


logger = logging.getLogger(__name__)

# Define a base output directory relative to the project root
# Assuming the script runs from the project root or MCP server manages paths correctly
OUTPUT_DIR = Path("output_maps")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # Ensure the directory exists

class MapService:
    """Service responsible for generating choropleth maps."""

    def __init__(self, config_service: ConfigService = ConfigService()):
        """Initializes the MapService."""
        # The tests expect a config_service dependency, though it's not used in the current methods
        self.config_service = config_service
        logger.info("MapService initialized.")

    def generate_map(self, config: Dict[str, Any], data_df: pd.DataFrame, options: Optional[PlottingOptions] = None) -> Optional[Path]:
        """
        Generates a choropleth map based on the provided configuration and data.
        Saves the map to a file if output options are provided.

        Args:
            config: Geography configuration dictionary.
            data_df: DataFrame containing the data to plot.
            options: Optional plotting options (title, output filename/format).

        Returns:
            Path to the saved map file if options specify output, otherwise None.
            Raises MapGenerationError on failure.
        """
        fig = None
        try:
            # Extract relevant info from config and options
            geography_key = config.get('geography_key', 'unknown_geo') # Get key from config if available
            data_hints = config.get('data_hints', {})
            # Use overrides from request if available, else use config hints, else default
            location_col = options.location_col_override if options and options.location_col_override else data_hints.get('location_column', 'location')
            value_col = options.value_col_override if options and options.value_col_override else data_hints.get('value_column', 'value')
            geo_join_col = data_hints.get('geo_join_column', 'name') # Default join column
            plot_title = options.title if options and options.title else config.get('figure', {}).get('title', f"Map: {geography_key}")
            output_filename_base = options.output_filename if options and options.output_filename else None
            output_format = options.output_format if options and options.output_format else 'png'
            output_dpi = config.get('figure', {}).get('output_dpi', 150) # Get DPI from config or default

            logger.info(f"Plotter params: geo_key='{geography_key}', loc_col='{location_col}', val_col='{value_col}', join_col='{geo_join_col}'")
            
            # Instantiate the ChoroplethPlotter with the parameters matching the actual implementation
            # Instantiate the ChoroplethPlotter with dynamic parameters
            plotter = ChoroplethPlotter(
                geography_key=geography_key,
                data=data_df,
                location_col=location_col,
                value_col=value_col
                # cache_dir can be added if needed from config/settings
            )
            
            # Generate the plot
            # Generate the plot using the determined join column and title
            fig, ax = plotter.plot(geo_join_column=geo_join_col, title=plot_title)

            # Save the plot to a file if output filename is provided
            output_path = None
            if output_filename_base:
                # Basic sanitization: remove potential path separators and invalid chars
                safe_filename_base = "".join(c for c in output_filename_base if c.isalnum() or c in ('_', '-')).rstrip()
                if not safe_filename_base:
                    raise MapGenerationError("Output filename is invalid after sanitization.")

                output_filename = f"{safe_filename_base}.{output_format}"
                output_path = OUTPUT_DIR / output_filename
                logger.info(f"Saving map to: {output_path}")
                try:
                    plt.savefig(output_path, format=output_format, dpi=output_dpi, bbox_inches='tight')
                except Exception as save_err:
                     logger.error(f"Error saving plot to file '{output_path}': {save_err}", exc_info=True)
                     raise MapGenerationError(f"Error saving plot to file: {save_err}") from save_err
            else:
                logger.info("No output filename provided, map not saved to file.")
                # Optionally, could return image bytes here if needed
                # buffer = io.BytesIO()
                # plt.savefig(buffer, format=output_format, dpi=output_dpi, bbox_inches='tight')
                # buffer.seek(0)
                # return buffer.getvalue() # Example if returning bytes

            return output_path # Return the path where the file was saved, or None
        except ValueError as e:
            # Handle errors during ChoroplethPlotter instantiation
            logger.error(f"Error initializing ChoroplethPlotter: {e}", exc_info=True)
            raise MapGenerationError(f"Error initializing ChoroplethPlotter: {e}")
        except RuntimeError as e:
            # Handle errors during plot generation
            logger.error(f"Error generating plot: {e}", exc_info=True)
            raise MapGenerationError(f"Error generating plot: {e}")
        except OSError as e:
            # Handle errors during plot saving
            logger.error(f"Error saving plot to buffer: {e}", exc_info=True)
            raise MapGenerationError(f"Error saving plot to buffer: {e}")
        except Exception as e:
            # Handle other unexpected errors
            logger.error(f"Unexpected error during map generation: {e}", exc_info=True)
            raise MapGenerationError(f"Unexpected error during map generation: {e}")
        finally:
            # Ensure the plot is closed to free memory, even if errors occurred
            if fig:
                plt.close(fig)
        
    def generate_map_from_request(self, request: GenerateMapRequest) -> GenerateMapResponse:
        """
        Generates a choropleth map based on the request data and configuration.
        Handles request parsing, calls internal generation, and formats response.
        """
        fig = None # Initialize fig to ensure it can be closed in finally block
        try:
            logger.info(f"Received map generation request for geography: {request.geography_key}")
            logger.debug(f"Request details: {request.model_dump(exclude={'data'})}") # Exclude potentially large data from log

            # 1. Prepare DataFrame from request data
            data_dict = [dp.model_dump() for dp in request.data]
            user_df = pd.DataFrame(data_dict)
            # Use the value column name specified in the request (defaults to 'value')
            # Value column override is handled inside generate_map now via options
            # logger.debug(f"Using value column: '{value_col_name}'") # No longer needed here
            
            # 2. Get configuration for the geography
            # 2. Get configuration for the geography (add geography_key to config dict)
            # TODO: Handle custom_config if needed - current logic assumes geography_key
            if not request.geography_key:
                 raise ValidationError("`geography_key` is required in the request.") # Or handle custom_config
            try:
                config = self.config_service.get_configuration(request.geography_key)
                config['geography_key'] = request.geography_key # Ensure key is in config dict
            except ResourceNotFoundError as e:
                 logger.error(f"Configuration not found for key '{request.geography_key}': {e}")
                 raise ConfigurationError(f"Configuration not found for key '{request.geography_key}'") from e

            # 3. Generate the map using the config, DataFrame, and options
            saved_path = self.generate_map(config, user_df, request.options)
            
            # 4. Return the response
            # 4. Return the response
            if saved_path:
                 message = f"Map generated successfully and saved to server path: {saved_path.name}" # Return only filename
            else:
                 message = "Map generated successfully (but not saved to file)."

            return GenerateMapResponse(
                map_id=None, # No longer using map_id for retrieval
                status="success",
                message=message,
                file_path=str(saved_path.name) if saved_path else None # Return relative path/filename
            )
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return GenerateMapResponse(
                status="error",
                error=ErrorDetail(
                    type="validation_error",
                    message=str(e)
                )
            )
        except ConfigurationError as e:
            logger.error(f"Config error: {e}")
            return GenerateMapResponse(
                status="error",
                error=ErrorDetail(
                    type="configuration_error",
                    message=str(e)
                )
            )
        except MapGenerationError as e:
            logger.error(f"Map generation error: {e}")
            return GenerateMapResponse(
                status="error",
                error=ErrorDetail(
                    type="map_generation_error",
                    message=str(e)
                )
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return GenerateMapResponse(
                status="error",
                error=ErrorDetail(
                    type="unexpected_error",
                    message=f"An unexpected error occurred: {e}"
                )
            )
        finally:
            if fig is not None:
                plt.close(fig)

    # --- Methods expected by tests (Dummy Implementations) ---

    # --- Removed Dummy/Test Methods ---
    # Removed generate_map_from_key, generate_map_from_config,
    # get_map_image, get_map_image_base64, validate_data, generate_map_internal
    # as they are not directly used by the MCP tool flow and rely on the old _map_storage.
    # If these are needed for other purposes (e.g., direct API), they would need refactoring.