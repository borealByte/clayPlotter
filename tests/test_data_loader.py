import pytest
import os
from clayPlotter.data_loader import DataLoader, InvalidDataError, InvalidFormatError  # Import from installed package

# Define expected structure (adjust as needed)
EXPECTED_KEYS = {'name', 'value'}

# --- Test Fixtures ---

@pytest.fixture
def valid_yaml_path(tmp_path):
    """Creates a temporary valid YAML file."""
    content = """
- name: Item1
  value: 100
- name: Item2
  value: 200
"""
    file_path = tmp_path / "valid_data.yaml"
    file_path.write_text(content)
    return str(file_path)

@pytest.fixture
def invalid_yaml_path(tmp_path):
    """Creates a temporary invalid YAML file (syntax error)."""
    content = """
- name: Item1
  value: 100
- name: Item2
  value: 200: # Invalid syntax
"""
    file_path = tmp_path / "invalid_format.yaml"
    file_path.write_text(content)
    return str(file_path)

@pytest.fixture
def invalid_structure_yaml_path(tmp_path):
    """Creates a temporary YAML file with missing keys."""
    content = """
- name: Item1
  # Missing 'value'
- name: Item2
  value: 200
"""
    file_path = tmp_path / "invalid_structure.yaml"
    file_path.write_text(content)
    return str(file_path)

@pytest.fixture
def data_loader():
    """Provides a DataLoader instance."""
    # This assumes DataLoader doesn't need complex setup for now
    return DataLoader()

# --- Test Cases ---

def test_load_valid_yaml_success(data_loader, valid_yaml_path):
    """Tests successful loading and validation of a valid YAML file."""
    data = data_loader.load_data(valid_yaml_path)
    assert isinstance(data, list)
    assert len(data) == 2
    assert isinstance(data[0], dict)
    assert data[0]['name'] == 'Item1'
    assert data[0]['value'] == 100
    assert isinstance(data[1], dict)
    assert data[1]['name'] == 'Item2'
    assert data[1]['value'] == 200

def test_load_nonexistent_file_raises_error(data_loader):
    """Tests that loading a non-existent file raises FileNotFoundError."""
    non_existent_path = "path/to/non_existent_file.yaml"
    with pytest.raises(FileNotFoundError):
        data_loader.load_data(non_existent_path)

def test_load_invalid_yaml_format_raises_error(data_loader, invalid_yaml_path):
    """Tests that loading a file with invalid YAML syntax raises InvalidFormatError."""
    with pytest.raises(InvalidFormatError):
        data_loader.load_data(invalid_yaml_path)

def test_load_invalid_data_structure_raises_error(data_loader, invalid_structure_yaml_path):
    """Tests that loading data with missing required keys raises InvalidDataError."""
    with pytest.raises(InvalidDataError):
        data_loader.load_data(invalid_structure_yaml_path)

def test_validate_data_structure_success(data_loader):
    """Tests the internal validation logic with correct data."""
    valid_data = [
        {'name': 'A', 'value': 1},
        {'name': 'B', 'value': 2}
    ]
    # Assuming a separate validation method or internal call within load_data
    # If validation is internal, this test might need refactoring later
    # For now, let's assume a helper method exists for direct testing
    assert data_loader._validate_structure(valid_data) is True # Placeholder for assertion

def test_validate_data_structure_missing_key_raises_error(data_loader):
    """Tests validation failure when a required key is missing."""
    invalid_data = [
        {'name': 'A', 'value': 1},
        {'name': 'B'} # Missing 'value'
    ]
    with pytest.raises(InvalidDataError):
        data_loader._validate_structure(invalid_data)

def test_validate_data_structure_wrong_type_raises_error(data_loader):
    """Tests validation failure when a key has the wrong data type."""
    invalid_data = [
        {'name': 'A', 'value': 1},
        {'name': 'B', 'value': 'not_a_number'}
    ]
    # This assumes type checking is part of validation
    with pytest.raises(InvalidDataError):
        data_loader._validate_structure(invalid_data)

def test_validate_data_structure_not_a_list_raises_error(data_loader):
    """Tests validation failure when the top-level structure is not a list."""
    invalid_data = {'name': 'A', 'value': 1} # Should be a list of dicts
    with pytest.raises(InvalidDataError):
        data_loader._validate_structure(invalid_data)