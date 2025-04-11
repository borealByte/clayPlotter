# src/clayPlotter/mcp/models/request_models.py
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import os  # Missing import for os.path.sep and os.path.altsep

from ..config import settings # Import settings for validation limits

logger = logging.getLogger(__name__)

# Original models
class DataPoint(BaseModel):
    """Represents a single data point for plotting."""
    location: str = Field(..., description="Location identifier (e.g., state name, province code) matching the geography's join column.")
    value: float | int = Field(..., description="The numerical value associated with the location.")

# Models for test compatibility
class MapData(BaseModel):
    """Represents a single data point for plotting (for test compatibility)."""
    location: str = Field(..., description="Location identifier (e.g., state name, province code) matching the geography's join column.")
    value: float | int = Field(..., description="The numerical value associated with the location.")

class MapDataRequest(BaseModel):
    """Request model for map data (for test compatibility)."""
    data: List[MapData] = Field(..., min_length=1, description="List of data points to plot.")

class CustomMapRequest(BaseModel):
    """Request model for custom map configuration (for test compatibility)."""
    config: str = Field(..., description="YAML configuration string for the map.")
    data: List[MapData] = Field(..., min_length=1, description="List of data points to plot.")

    # Optional: Add more specific validation if needed
    # @validator('location')
    # def location_must_be_non_empty(cls, v):
    #     if not v or not v.strip():
    #         raise ValueError('Location must not be empty')
    #     return v

class PlottingOptions(BaseModel):
    """Optional parameters to customize the plot appearance."""
    title: Optional[str] = Field(None, description="Custom title for the plot.")
    output_filename: Optional[str] = Field(None, description="Filename (without extension) for the saved map image (e.g., 'my_map'). If provided, the map is saved.")
    output_format: str = Field("png", description="Format for the saved map ('png', 'jpg', 'svg', 'pdf').", pattern="^(png|jpg|jpeg|svg|pdf)$")
    # Add other potential options from ChoroplethPlotter or its config if needed
    # e.g., cmap: Optional[str] = None

class GenerateMapRequest(BaseModel):
    """Request model for the generate_map tool."""
    geography_key: str = Field(..., description="Identifier for the geographic dataset and configuration (e.g., 'usa_states', 'brazil_states').")
    data: List[DataPoint] = Field(..., description="List of data points to plot.")
    location_col_override: Optional[str] = Field(None, description="Optional: Override the default location column name specified in the geography config's data_hints.")
    value_col_override: Optional[str] = Field("value", description="Optional: Override the default value column name ('value') used internally.") # Default matches DataPoint
    options: Optional[PlottingOptions] = Field(None, description="Optional plotting customization options.")

    @validator('data')
    def check_data_size(cls, v):
        """Validates that the input data does not exceed the configured limit."""
        max_points = settings.MAX_DATA_POINTS
        if len(v) > max_points:
            raise ValueError(f"Input data exceeds maximum allowed size ({len(v)} > {max_points} points).")
        if not v:
            raise ValueError("Input data list cannot be empty.")
        logger.debug(f"Data size validation passed: {len(v)} points.")
        return v

    @validator('options')
    def validate_output_filename(cls, v, values):
        """
        Validates the output filename if provided.
        - Prevents path traversal.
        - Ensures it's just a filename, not a path (unless allowed by config).
        """
        if v and v.output_filename:
            filename = v.output_filename
            # Basic sanitization: remove leading/trailing whitespace
            filename = filename.strip()
            if not filename:
                 raise ValueError("Output filename cannot be empty or just whitespace.")

            # Security: Prevent path traversal and absolute paths
            path_part = Path(filename)
            if path_part.is_absolute() or '..' in path_part.parts:
                raise ValueError("Output filename cannot be an absolute path or contain '..'.")

            # Security: Check if filename contains path separators if arbitrary paths are disallowed
            if not settings.ALLOW_ARBITRARY_OUTPUT_PATH and (os.path.sep in filename or (os.path.altsep and os.path.altsep in filename)):
                 raise ValueError(f"Output filename '{filename}' cannot contain path separators ('/' or '\\') when arbitrary paths are disallowed.")

            # Optional: Check for potentially problematic characters (more strict)
            # import re
            # if not re.match(r"^[a-zA-Z0-9_.-]+$", filename):
            #     raise ValueError("Output filename contains invalid characters. Use letters, numbers, underscore, dot, or hyphen.")

            # Update the filename in the options object after validation/sanitization
            v.output_filename = filename
            logger.debug(f"Output filename validation passed: '{filename}'")
        return v

# Example Usage (for testing/documentation)
# req = GenerateMapRequest(
#     geography_key="usa_states",
#     data=[DataPoint(location="California", value=100), DataPoint(location="Texas", value=85)],
#     options=PlottingOptions(title="My US Map", output_filename="us_map_test")
# )