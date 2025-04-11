"""
FastAPI implementation for the clayPlotter MCP server.
This file provides a REST API interface for the same functionality
that the MCP server provides.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import logging

from .services.map_service import MapService
from .services.config_service import ConfigService
from .models.request_models import DataPoint, GenerateMapRequest, PlottingOptions
from .models.response_models import GenerateMapResponse, ListGeographiesResponse, ErrorDetail
from .exceptions import ConfigurationError, ValidationError, MapGenerationError, ResourceNotFoundError

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ClayPlotter API",
    description="API for generating choropleth maps using the clayPlotter library.",
    version="0.1.0"
)

# Dependency injection for services
def get_map_service():
    return MapService()

def get_config_service():
    return ConfigService()

# API Routes

@app.get("/api/v1/configurations", response_model=List[str])
async def get_configurations(config_service: ConfigService = Depends(get_config_service)):
    """Get a list of available geography configurations."""
    try:
        response = config_service.list_available_geographies()
        if not response.success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve configurations: {response.error.message if response.error else 'Unknown error'}"
            )
        return response.geographies
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve configurations: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_configurations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/v1/maps/from-key", status_code=201, response_model=Dict[str, str])
async def create_map_from_key(
    config_key: str = Query(..., description="The geography configuration key to use"),
    request_data: Dict[str, List[Dict[str, Any]]] = None,
    map_service: MapService = Depends(get_map_service)
):
    """Create a map using a predefined geography configuration."""
    try:
        # Convert the request data to the expected format
        data = [DataPoint(**item) for item in request_data.get("data", [])]
        
        # Generate a UUID for the map
        map_id = uuid4()
        
        # Return the map ID (in a real implementation, this would be stored)
        return {"map_id": str(map_id)}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing configuration '{config_key}': {str(e)}"
        )
    except MapGenerationError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate map: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_map_from_key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/v1/maps/from-config", status_code=201, response_model=Dict[str, str])
async def create_map_from_config(
    request_data: Dict[str, Any],
    map_service: MapService = Depends(get_map_service)
):
    """Create a map using a custom YAML configuration."""
    try:
        # In a real implementation, this would process the custom config
        # and generate a map
        map_id = uuid4()
        return {"map_id": str(map_id)}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MapGenerationError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate map: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in create_map_from_config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/maps/{map_id}")
async def get_map_image(
    map_id: UUID = Path(..., description="The UUID of the map to retrieve"),
    map_service: MapService = Depends(get_map_service)
):
    """Get a map image by its ID."""
    try:
        # In a real implementation, this would retrieve the map image
        # For now, just return a dummy response
        return {"map_id": str(map_id)}
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_map_image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/maps/{map_id}/base64", response_model=Dict[str, str])
async def get_map_base64(
    map_id: UUID = Path(..., description="The UUID of the map to retrieve"),
    map_service: MapService = Depends(get_map_service)
):
    """Get a map image as a base64-encoded string."""
    try:
        # In a real implementation, this would retrieve the map image as base64
        # For now, just return a dummy response
        return {
            "map_id": str(map_id),
            "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        }
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in get_map_base64: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")