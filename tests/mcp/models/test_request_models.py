import pytest
from pydantic import ValidationError

# Import the models to test
from clayPlotter.mcp.models.request_models import MapData, MapDataRequest, CustomMapRequest

# --- Tests for MapData ---

def test_map_data_valid():
    """Test MapData with valid string location and numeric value."""
    data = {"location": "StateA", "value": 123.45}
    model = MapData(**data)
    assert model.location == "StateA"
    assert model.value == 123.45

def test_map_data_valid_int_value():
    """Test MapData with valid integer value."""
    data = {"location": "StateB", "value": 100}
    model = MapData(**data)
    assert model.location == "StateB"
    assert model.value == 100 # Pydantic converts int to float if type hint is float

def test_map_data_missing_location():
    """Test MapData validation fails if 'location' is missing."""
    data = {"value": 123.45}
    with pytest.raises(ValidationError) as excinfo:
        MapData(**data)
    assert "'location'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_map_data_missing_value():
    """Test MapData validation fails if 'value' is missing."""
    data = {"location": "StateA"}
    with pytest.raises(ValidationError) as excinfo:
        MapData(**data)
    assert "'value'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_map_data_invalid_location_type():
    """Test MapData validation fails if 'location' is not a string."""
    data = {"location": 123, "value": 123.45}
    with pytest.raises(ValidationError) as excinfo:
        MapData(**data)
    assert "'location'" in str(excinfo.value)
    assert "Input should be a valid string" in str(excinfo.value)

def test_map_data_invalid_value_type():
    """Test MapData validation fails if 'value' is not numeric."""
    data = {"location": "StateA", "value": "not-a-number"}
    with pytest.raises(ValidationError) as excinfo:
        MapData(**data)
    assert "'value'" in str(excinfo.value)
    assert "Input should be a valid number" in str(excinfo.value)

# --- Tests for MapDataRequest ---

def test_map_data_request_valid():
    """Test MapDataRequest with a valid list of MapData."""
    data = {"data": [{"location": "StateA", "value": 10}, {"location": "StateB", "value": 20.5}]}
    model = MapDataRequest(**data)
    assert len(model.data) == 2
    assert isinstance(model.data[0], MapData)
    assert model.data[0].location == "StateA"
    assert model.data[1].value == 20.5

def test_map_data_request_empty_list():
    """Test MapDataRequest validation fails with an empty list."""
    data = {"data": []}
    with pytest.raises(ValidationError) as excinfo:
        MapDataRequest(**data)
    assert "'data'" in str(excinfo.value)
    assert "List should have at least 1 item" in str(excinfo.value) # Based on min_length=1

def test_map_data_request_missing_data():
    """Test MapDataRequest validation fails if 'data' field is missing."""
    data = {}
    with pytest.raises(ValidationError) as excinfo:
        MapDataRequest(**data)
    assert "'data'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_map_data_request_invalid_item_in_list():
    """Test MapDataRequest validation fails if list contains invalid items."""
    data = {"data": [{"location": "StateA", "value": 10}, {"location": "StateB"}]} # Missing value in second item
    with pytest.raises(ValidationError) as excinfo:
        MapDataRequest(**data)
    # Error message might point to the specific item and field
    assert "'data.1.value'" in str(excinfo.value) or "'data[1].value'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_map_data_request_data_not_list():
    """Test MapDataRequest validation fails if 'data' is not a list."""
    data = {"data": {"location": "StateA", "value": 10}} # Should be a list
    with pytest.raises(ValidationError) as excinfo:
        MapDataRequest(**data)
    assert "'data'" in str(excinfo.value)
    assert "Input should be a valid list" in str(excinfo.value)


# --- Tests for CustomMapRequest ---

def test_custom_map_request_valid():
    """Test CustomMapRequest with valid config string and data list."""
    config_str = "title: My Map\ngeopackage_path: path/to.gpkg\n..."
    map_data = [{"location": "RegionX", "value": 100}]
    data = {"config": config_str, "data": map_data}
    model = CustomMapRequest(**data)
    assert model.config == config_str
    assert len(model.data) == 1
    assert isinstance(model.data[0], MapData)
    assert model.data[0].location == "RegionX"

def test_custom_map_request_missing_config():
    """Test CustomMapRequest validation fails if 'config' is missing."""
    map_data = [{"location": "RegionX", "value": 100}]
    data = {"data": map_data}
    with pytest.raises(ValidationError) as excinfo:
        CustomMapRequest(**data)
    assert "'config'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_custom_map_request_missing_data():
    """Test CustomMapRequest validation fails if 'data' is missing."""
    config_str = "title: My Map\n..."
    data = {"config": config_str}
    with pytest.raises(ValidationError) as excinfo:
        CustomMapRequest(**data)
    assert "'data'" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)

def test_custom_map_request_invalid_config_type():
    """Test CustomMapRequest validation fails if 'config' is not a string."""
    map_data = [{"location": "RegionX", "value": 100}]
    data = {"config": {"title": "My Map"}, "data": map_data} # Config should be string
    with pytest.raises(ValidationError) as excinfo:
        CustomMapRequest(**data)
    assert "'config'" in str(excinfo.value)
    assert "Input should be a valid string" in str(excinfo.value)

def test_custom_map_request_invalid_data():
    """Test CustomMapRequest validation fails if 'data' is invalid (e.g., empty list)."""
    config_str = "title: My Map\n..."
    data = {"config": config_str, "data": []} # Empty list
    with pytest.raises(ValidationError) as excinfo:
        CustomMapRequest(**data)
    assert "'data'" in str(excinfo.value)
    assert "List should have at least 1 item" in str(excinfo.value)