import pytest
from pydantic import ValidationError
from uuid import UUID, uuid4

# Import the models to test
from clayPlotter.mcp.models.response_models import MapCreatedResponse, Base64MapResponse, ErrorResponse

# --- Tests for MapCreatedResponse ---

def test_map_created_response_valid():
    """Test MapCreatedResponse with a valid UUID."""
    map_id = uuid4()
    data = {"map_id": map_id}
    model = MapCreatedResponse(**data)
    assert model.map_id == map_id
    # Check serialization includes string representation of UUID
    assert model.model_dump() == {"map_id": str(map_id)}

def test_map_created_response_missing_map_id():
    """Test MapCreatedResponse validation fails if 'map_id' is missing."""
    data = {}
    with pytest.raises(ValidationError) as excinfo:
        MapCreatedResponse(**data)
    assert "'map_id'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_map_created_response_invalid_map_id_type():
    """Test MapCreatedResponse validation fails if 'map_id' is not a UUID."""
    data = {"map_id": "not-a-uuid"}
    with pytest.raises(ValidationError) as excinfo:
        MapCreatedResponse(**data)
    assert "'map_id'" in str(excinfo.value)
    # Pydantic v2 error message might be different, check based on version
    assert "UUID input should be a valid UUID" in str(excinfo.value) or "value is not a valid uuid" in str(excinfo.value)


# --- Tests for Base64MapResponse ---

def test_base64_map_response_valid():
    """Test Base64MapResponse with valid UUID and base64 string."""
    map_id = uuid4()
    b64_string = "aGVsbG8gd29ybGQ=" # "hello world" in base64
    data = {"map_id": map_id, "image_base64": b64_string}
    model = Base64MapResponse(**data)
    assert model.map_id == map_id
    assert model.image_base64 == b64_string
    assert model.model_dump() == {"map_id": str(map_id), "image_base64": b64_string}

def test_base64_map_response_missing_map_id():
    """Test Base64MapResponse validation fails if 'map_id' is missing."""
    b64_string = "aGVsbG8gd29ybGQ="
    data = {"image_base64": b64_string}
    with pytest.raises(ValidationError) as excinfo:
        Base64MapResponse(**data)
    assert "'map_id'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_base64_map_response_missing_image_base64():
    """Test Base64MapResponse validation fails if 'image_base64' is missing."""
    map_id = uuid4()
    data = {"map_id": map_id}
    with pytest.raises(ValidationError) as excinfo:
        Base64MapResponse(**data)
    assert "'image_base64'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_base64_map_response_invalid_map_id_type():
    """Test Base64MapResponse validation fails if 'map_id' is not a UUID."""
    b64_string = "aGVsbG8gd29ybGQ="
    data = {"map_id": "not-a-uuid", "image_base64": b64_string}
    with pytest.raises(ValidationError) as excinfo:
        Base64MapResponse(**data)
    assert "'map_id'" in str(excinfo.value)
    assert "UUID input should be a valid UUID" in str(excinfo.value) or "value is not a valid uuid" in str(excinfo.value)

def test_base64_map_response_invalid_image_base64_type():
    """Test Base64MapResponse validation fails if 'image_base64' is not a string."""
    map_id = uuid4()
    data = {"map_id": map_id, "image_base64": 12345} # Should be string
    with pytest.raises(ValidationError) as excinfo:
        Base64MapResponse(**data)
    assert "'image_base64'" in str(excinfo.value)
    assert "Input should be a valid string" in str(excinfo.value)


# --- Tests for ErrorResponse ---
# These are often implicitly tested by checking the JSON output of failing API calls.
# Adding explicit tests here is optional but possible.

def test_error_response_valid():
    """Test ErrorResponse with a valid detail string."""
    detail_msg = "Something went wrong"
    data = {"detail": detail_msg}
    model = ErrorResponse(**data)
    assert model.detail == detail_msg
    assert model.model_dump() == {"detail": detail_msg}

def test_error_response_missing_detail():
    """Test ErrorResponse validation fails if 'detail' is missing."""
    data = {}
    with pytest.raises(ValidationError) as excinfo:
        ErrorResponse(**data)
    assert "'detail'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_error_response_invalid_detail_type():
    """Test ErrorResponse validation fails if 'detail' is not a string."""
    data = {"detail": ["list", "of", "errors"]} # Should be string
    with pytest.raises(ValidationError) as excinfo:
        ErrorResponse(**data)
    assert "'detail'" in str(excinfo.value)
    assert "Input should be a valid string" in str(excinfo.value)