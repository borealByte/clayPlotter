# src/clayPlotter/mcp/models/response_models.py
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

# Original models
class ErrorDetail(BaseModel):
    """Provides details about an error."""
    code: str = Field(..., description="An error code (e.g., 'VALIDATION_ERROR', 'PLOT_ERROR', 'FILE_NOT_FOUND').")
    message: str = Field(..., description="A human-readable description of the error.")
    field: Optional[str] = Field(None, description="The specific field related to the error, if applicable.")

class GenerateMapResponse(BaseModel):
    """Response model for the generate_map tool."""
    success: bool = Field(..., description="Indicates whether the map generation was successful.")
    message: str = Field(..., description="A summary message about the outcome (e.g., 'Map generated successfully.', 'Map generation failed.').")
    output_path: Optional[str] = Field(None, description="The absolute path to the saved map image file, if saving was requested and successful.")
    error: Optional[ErrorDetail] = Field(None, description="Details about the error, if success is false.")

class ListGeographiesResponse(BaseModel):
    """Response model for listing available geographies."""
    success: bool = Field(..., description="Indicates whether the listing was successful.")
    geographies: Optional[List[str]] = Field(None, description="A list of available geography keys (e.g., ['usa_states', 'brazil_states']).")
    message: str = Field(..., description="A summary message about the outcome.")
    error: Optional[ErrorDetail] = Field(None, description="Details about the error, if success is false.")

# Models for test compatibility
class MapCreatedResponse(BaseModel):
    """Response model for map creation (for test compatibility)."""
    map_id: UUID = Field(..., description="The UUID of the created map.")

class Base64MapResponse(BaseModel):
    """Response model for base64-encoded map image (for test compatibility)."""
    map_id: UUID = Field(..., description="The UUID of the map.")
    image_base64: str = Field(..., description="Base64-encoded image data.")

class ErrorResponse(BaseModel):
    """Response model for errors (for test compatibility)."""
    detail: str = Field(..., description="Error detail message.")

# Example Usage (for testing/documentation)
# success_resp = GenerateMapResponse(success=True, message="Map generated and saved.", output_path="/path/to/output/my_map.png")
# error_resp = GenerateMapResponse(success=False, message="Validation failed.", error=ErrorDetail(code="VALIDATION_ERROR", message="Invalid geography key.", field="geography_key"))
# list_resp = ListGeographiesResponse(success=True, geographies=["usa_states", "canada_provinces"], message="Available geographies listed.")