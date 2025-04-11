import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from uuid import uuid4, UUID

# Import the FastAPI app instance
# Assuming 'app' is the instance in src/clayPlotter/mcp/main.py
from clayPlotter.mcp.main import app

# Import services to mock and exceptions they might raise
from clayPlotter.mcp.services.config_service import ConfigurationService
from clayPlotter.mcp.services.map_service import MapService
from clayPlotter.mcp.exceptions import (
    ConfigurationError, ValidationError, MapGenerationError, ResourceNotFoundError
)
# Import request/response models if needed for assertions (optional here as we check raw JSON)
# from clayPlotter.mcp.models.request_models import MapDataRequest, CustomMapRequest
# from clayPlotter.mcp.models.response_models import MapCreatedResponse, Base64MapResponse, ErrorResponse

# --- Fixtures ---

@pytest.fixture(scope="function") # Use function scope to reset mocks for each test
def mock_config_service():
    """Provides a mocked ConfigurationService instance."""
    return MagicMock(spec=ConfigurationService)

@pytest.fixture(scope="function")
def mock_map_service():
    """Provides a mocked MapService instance."""
    return MagicMock(spec=MapService)

@pytest.fixture(scope="function")
def test_client(mock_config_service, mock_map_service):
    """Provides a TestClient with mocked service dependencies."""
    # Override dependencies in the FastAPI app
    app.dependency_overrides[ConfigurationService] = lambda: mock_config_service
    app.dependency_overrides[MapService] = lambda: mock_map_service

    with TestClient(app) as client:
        yield client

    # Clean up overrides after tests
    app.dependency_overrides = {}


# --- Test Cases ---

# Test GET /api/v1/configurations
def test_get_configurations_success(test_client, mock_config_service):
    """Test GET /configurations successfully returns list of keys."""
    expected_keys = ["usa_states", "canada_provinces"]
    mock_config_service.get_available_configurations.return_value = expected_keys

    response = test_client.get("/api/v1/configurations")

    assert response.status_code == 200
    assert response.json() == expected_keys
    mock_config_service.get_available_configurations.assert_called_once()

def test_get_configurations_error(test_client, mock_config_service):
    """Test GET /configurations handles ConfigurationError."""
    error_message = "Cannot access config directory"
    mock_config_service.get_available_configurations.side_effect = ConfigurationError(error_message)

    response = test_client.get("/api/v1/configurations")

    assert response.status_code == 500
    assert response.json() == {"detail": f"Failed to retrieve configurations: {error_message}"}
    mock_config_service.get_available_configurations.assert_called_once()


# Test POST /api/v1/maps/from-key
def test_create_map_from_key_success(test_client, mock_map_service):
    """Test POST /maps/from-key successfully creates a map."""
    config_key = "usa_states"
    request_data = {"data": [{"location": "CA", "value": 10}]}
    map_id = uuid4()
    mock_map_service.generate_map_from_key.return_value = map_id

    response = test_client.post(f"/api/v1/maps/from-key?config_key={config_key}", json=request_data)

    assert response.status_code == 201 # Created
    assert response.json() == {"map_id": str(map_id)}
    # Check that the service method was called with the correct arguments
    # Note: Pydantic models handle the request body parsing before it hits the service
    mock_map_service.generate_map_from_key.assert_called_once_with(config_key, request_data["data"])

def test_create_map_from_key_validation_error_pydantic(test_client, mock_map_service):
    """Test POST /maps/from-key handles Pydantic validation errors (e.g., bad data format)."""
    config_key = "usa_states"
    # Invalid data structure (missing 'value')
    request_data = {"data": [{"location": "CA"}]}

    response = test_client.post(f"/api/v1/maps/from-key?config_key={config_key}", json=request_data)

    assert response.status_code == 422 # Unprocessable Entity
    # Pydantic's error structure can be complex, check for key details
    assert "detail" in response.json()
    assert response.json()["detail"][0]["msg"] == "Field required" # Example check
    mock_map_service.generate_map_from_key.assert_not_called()

def test_create_map_from_key_validation_error_service(test_client, mock_map_service):
    """Test POST /maps/from-key handles custom validation errors from the service."""
    config_key = "usa_states"
    request_data = {"data": [{"location": "CA", "value": "invalid"}]} # Value should be numeric
    error_message = "'value' column must contain numeric data"
    mock_map_service.generate_map_from_key.side_effect = ValidationError(error_message)

    response = test_client.post(f"/api/v1/maps/from-key?config_key={config_key}", json=request_data)

    assert response.status_code == 400 # Bad Request
    assert response.json() == {"detail": error_message}
    mock_map_service.generate_map_from_key.assert_called_once_with(config_key, request_data["data"])

def test_create_map_from_key_config_error(test_client, mock_map_service):
    """Test POST /maps/from-key handles ConfigurationError from the service."""
    config_key = "invalid_key"
    request_data = {"data": [{"location": "CA", "value": 10}]}
    error_message = f"Configuration file not found for key: {config_key}"
    mock_map_service.generate_map_from_key.side_effect = ConfigurationError(error_message)

    response = test_client.post(f"/api/v1/maps/from-key?config_key={config_key}", json=request_data)

    # ConfigurationError could be 404 (if key invalid) or 500 (if file read fails)
    # Let's assume the service raises ConfigurationError for file issues, leading to 500
    # If it raises ValidationError for invalid key, it would be 400/404. Adjust based on service impl.
    assert response.status_code == 500 # Internal Server Error (or potentially 404/400)
    assert response.json() == {"detail": f"Error processing configuration '{config_key}': {error_message}"}
    mock_map_service.generate_map_from_key.assert_called_once_with(config_key, request_data["data"])

def test_create_map_from_key_generation_error(test_client, mock_map_service):
    """Test POST /maps/from-key handles MapGenerationError from the service."""
    config_key = "usa_states"
    request_data = {"data": [{"location": "CA", "value": 10}]}
    error_message = "Error during plotting"
    mock_map_service.generate_map_from_key.side_effect = MapGenerationError(error_message)

    response = test_client.post(f"/api/v1/maps/from-key?config_key={config_key}", json=request_data)

    assert response.status_code == 500 # Internal Server Error
    assert response.json() == {"detail": f"Failed to generate map: {error_message}"}
    mock_map_service.generate_map_from_key.assert_called_once_with(config_key, request_data["data"])


# Test POST /api/v1/maps/from-config
def test_create_map_from_config_success(test_client, mock_map_service):
    """Test POST /maps/from-config successfully creates a map."""
    request_data = {
        "config": "title: Custom Map\ngeopackage_path: path/to.gpkg\n...", # Valid YAML string
        "data": [{"location": "Region1", "value": 55}]
    }
    map_id = uuid4()
    mock_map_service.generate_map_from_config.return_value = map_id

    response = test_client.post("/api/v1/maps/from-config", json=request_data)

    assert response.status_code == 201 # Created
    assert response.json() == {"map_id": str(map_id)}
    mock_map_service.generate_map_from_config.assert_called_once_with(request_data["config"], request_data["data"])

def test_create_map_from_config_validation_error_pydantic(test_client, mock_map_service):
    """Test POST /maps/from-config handles Pydantic validation errors."""
    # Missing 'data' field
    request_data = {"config": "title: Custom Map\n..."}

    response = test_client.post("/api/v1/maps/from-config", json=request_data)

    assert response.status_code == 422 # Unprocessable Entity
    assert "detail" in response.json()
    assert response.json()["detail"][0]["loc"] == ["body", "data"] # Example check
    mock_map_service.generate_map_from_config.assert_not_called()

def test_create_map_from_config_validation_error_service(test_client, mock_map_service):
    """Test POST /maps/from-config handles custom validation errors from the service."""
    request_data = {
        "config": "title: Custom Map\n...",
        "data": [{"location": 123, "value": 55}] # Invalid location type
    }
    error_message = "'location' values must be strings"
    mock_map_service.generate_map_from_config.side_effect = ValidationError(error_message)

    response = test_client.post("/api/v1/maps/from-config", json=request_data)

    assert response.status_code == 400 # Bad Request
    assert response.json() == {"detail": error_message}
    mock_map_service.generate_map_from_config.assert_called_once_with(request_data["config"], request_data["data"])

def test_create_map_from_config_config_validation_error(test_client, mock_map_service):
    """Test POST /maps/from-config handles config validation errors from the service."""
    request_data = {
        "config": "invalid: yaml:", # Invalid YAML
        "data": [{"location": "Region1", "value": 55}]
    }
    error_message = "Invalid YAML format in custom configuration"
    mock_map_service.generate_map_from_config.side_effect = ValidationError(error_message)

    response = test_client.post("/api/v1/maps/from-config", json=request_data)

    assert response.status_code == 400 # Bad Request (as it's a validation issue)
    assert response.json() == {"detail": error_message}
    mock_map_service.generate_map_from_config.assert_called_once_with(request_data["config"], request_data["data"])

def test_create_map_from_config_generation_error(test_client, mock_map_service):
    """Test POST /maps/from-config handles MapGenerationError from the service."""
    request_data = {
        "config": "title: Custom Map\n...",
        "data": [{"location": "Region1", "value": 55}]
    }
    error_message = "Error reading GeoPackage"
    mock_map_service.generate_map_from_config.side_effect = MapGenerationError(error_message)

    response = test_client.post("/api/v1/maps/from-config", json=request_data)

    assert response.status_code == 500 # Internal Server Error
    assert response.json() == {"detail": f"Failed to generate map: {error_message}"}
    mock_map_service.generate_map_from_config.assert_called_once_with(request_data["config"], request_data["data"])


# Test GET /api/v1/maps/{map_id}
def test_get_map_image_success(test_client, mock_map_service):
    """Test GET /maps/{map_id} successfully returns image data."""
    map_id = uuid4()
    image_data = b'\x89PNG\r\n\x1a\nFake PNG Data'
    content_type = "image/png"
    mock_map_service.get_map_image.return_value = (image_data, content_type)

    response = test_client.get(f"/api/v1/maps/{map_id}")

    assert response.status_code == 200
    assert response.content == image_data
    assert response.headers["content-type"] == content_type
    mock_map_service.get_map_image.assert_called_once_with(map_id)

def test_get_map_image_not_found(test_client, mock_map_service):
    """Test GET /maps/{map_id} handles ResourceNotFoundError."""
    map_id = uuid4()
    error_message = f"Map with ID '{map_id}' not found"
    mock_map_service.get_map_image.side_effect = ResourceNotFoundError(error_message)

    response = test_client.get(f"/api/v1/maps/{map_id}")

    assert response.status_code == 404 # Not Found
    assert response.json() == {"detail": error_message}
    mock_map_service.get_map_image.assert_called_once_with(map_id)

def test_get_map_image_invalid_uuid(test_client, mock_map_service):
    """Test GET /maps/{map_id} handles invalid UUID format."""
    invalid_map_id = "not-a-uuid"

    response = test_client.get(f"/api/v1/maps/{invalid_map_id}")

    assert response.status_code == 422 # Unprocessable Entity (FastAPI handles path param validation)
    mock_map_service.get_map_image.assert_not_called()


# Test GET /api/v1/maps/{map_id}/base64
def test_get_map_base64_success(test_client, mock_map_service):
    """Test GET /maps/{map_id}/base64 successfully returns base64 string."""
    map_id = uuid4()
    base64_string = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=" # Example base64
    mock_map_service.get_map_image_base64.return_value = base64_string

    response = test_client.get(f"/api/v1/maps/{map_id}/base64")

    assert response.status_code == 200
    assert response.json() == {"map_id": str(map_id), "image_base64": base64_string}
    mock_map_service.get_map_image_base64.assert_called_once_with(map_id)

def test_get_map_base64_not_found(test_client, mock_map_service):
    """Test GET /maps/{map_id}/base64 handles ResourceNotFoundError."""
    map_id = uuid4()
    error_message = f"Map with ID '{map_id}' not found"
    mock_map_service.get_map_image_base64.side_effect = ResourceNotFoundError(error_message)

    response = test_client.get(f"/api/v1/maps/{map_id}/base64")

    assert response.status_code == 404 # Not Found
    assert response.json() == {"detail": error_message}
    mock_map_service.get_map_image_base64.assert_called_once_with(map_id)

def test_get_map_base64_invalid_uuid(test_client, mock_map_service):
    """Test GET /maps/{map_id}/base64 handles invalid UUID format."""
    invalid_map_id = "not-a-uuid"

    response = test_client.get(f"/api/v1/maps/{invalid_map_id}/base64")

    assert response.status_code == 422 # Unprocessable Entity
    mock_map_service.get_map_image_base64.assert_not_called()