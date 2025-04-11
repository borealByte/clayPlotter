import unittest
from unittest.mock import patch, MagicMock, mock_open
import yaml
import pytest
from importlib_resources import files  # Use importlib_resources for Python 3.9+

from clayPlotter.mcp.services.config_service import ConfigurationService
from clayPlotter.mcp.exceptions import ConfigurationError, ValidationError

# Define the path to the resources directory relative to the package
# This assumes your tests run in an environment where the package is installed or discoverable
# Adjust the package name if necessary
RESOURCE_PACKAGE = 'clayPlotter.l1_choropleth.resources'

class TestConfigurationService(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.service = ConfigurationService()

    def test_init_creates_empty_cache(self):
        """TDD Anchor: test_init_creates_empty_cache"""
        self.assertEqual(self.service._config_cache, {})

    @patch('importlib_resources.files') # Corrected mock path
    def test_get_available_configurations_returns_list_of_keys(self, mock_files):
        """TDD Anchor: test_get_available_configurations_returns_list_of_keys"""
        # Mock the resources directory and its contents
        mock_resource_dir = MagicMock()
        mock_resource_dir.is_dir.return_value = True
        mock_resource_dir.iterdir.return_value = [
            MagicMock(name='usa_states.yaml', is_file=lambda: True, stem='usa_states'),
            MagicMock(name='canada_provinces.yaml', is_file=lambda: True, stem='canada_provinces'),
            MagicMock(name='other_file.txt', is_file=lambda: True, stem='other_file'), # Should be ignored
            MagicMock(name='subdir', is_file=lambda: False, is_dir=lambda: True) # Should be ignored
        ]
        mock_files.return_value = mock_resource_dir

        expected_keys = ['usa_states', 'canada_provinces']
        available_configs = self.service.get_available_configurations()

        self.assertIsInstance(available_configs, list)
        self.assertCountEqual(available_configs, expected_keys) # Use assertCountEqual for order-independent comparison
        mock_files.assert_called_once_with(RESOURCE_PACKAGE)

    @patch('importlib_resources.files') # Corrected mock path
    def test_get_available_configurations_handles_errors(self, mock_files):
        """TDD Anchor: test_get_available_configurations_handles_errors"""
        mock_files.side_effect = OSError("Simulated OS Error")

        with self.assertRaises(ConfigurationError) as cm:
            self.service.get_available_configurations()
        self.assertIn("Error accessing configuration directory", str(cm.exception))
        mock_files.assert_called_once_with(RESOURCE_PACKAGE)

    @patch('importlib_resources.files') # Corrected mock path
    @patch('builtins.open', new_callable=mock_open, read_data="key: value")
    @patch('yaml.safe_load')
    def test_get_configuration_returns_dict(self, mock_safe_load, mock_open_file, mock_files):
        """TDD Anchor: test_get_configuration_returns_dict"""
        config_key = "test_config"
        expected_config = {"key": "value"}
        mock_safe_load.return_value = expected_config

        # Mock the file path resolution
        mock_config_file_path = MagicMock()
        mock_config_file_path.exists.return_value = True
        mock_resource_dir = MagicMock()
        mock_resource_dir.joinpath.return_value = mock_config_file_path
        mock_files.return_value = mock_resource_dir

        # First call - load from file
        config = self.service.get_configuration(config_key)
        self.assertEqual(config, expected_config)
        mock_files.assert_called_once_with(RESOURCE_PACKAGE)
        mock_resource_dir.joinpath.assert_called_once_with(f"{config_key}.yaml")
        mock_open_file.assert_called_once_with(mock_config_file_path, 'r', encoding='utf-8')
        mock_safe_load.assert_called_once()
        self.assertIn(config_key, self.service._config_cache) # Check cache population

        # Reset mocks for second call
        mock_open_file.reset_mock()
        mock_safe_load.reset_mock()

        # Second call - should hit cache
        config_cached = self.service.get_configuration(config_key)
        self.assertEqual(config_cached, expected_config)
        mock_open_file.assert_not_called() # Should not open file again
        mock_safe_load.assert_not_called() # Should not load yaml again

    @patch('importlib_resources.files') # Corrected mock path
    def test_get_configuration_validates_key(self, mock_files):
        """TDD Anchor: test_get_configuration_validates_key"""
        # Mock get_available_configurations to return a fixed list
        self.service.get_available_configurations = MagicMock(return_value=["valid_key"])

        invalid_key = "invalid_key"
        with self.assertRaises(ValidationError) as cm:
            self.service.get_configuration(invalid_key)
        self.assertIn(f"Invalid configuration key: {invalid_key}", str(cm.exception))
        self.service.get_available_configurations.assert_called_once() # Ensure validation happened

    @patch('importlib_resources.files') # Corrected mock path
    def test_get_configuration_handles_missing_file(self, mock_files):
        """TDD Anchor: test_get_configuration_handles_missing_file"""
        config_key = "missing_config"
        self.service.get_available_configurations = MagicMock(return_value=[config_key]) # Assume key is valid

        # Mock the file path resolution to indicate file doesn't exist
        mock_config_file_path = MagicMock()
        mock_config_file_path.exists.return_value = False
        mock_resource_dir = MagicMock()
        mock_resource_dir.joinpath.return_value = mock_config_file_path
        mock_files.return_value = mock_resource_dir

        with self.assertRaises(ConfigurationError) as cm:
            self.service.get_configuration(config_key)
        self.assertIn(f"Configuration file not found for key: {config_key}", str(cm.exception))
        mock_files.assert_called_once_with(RESOURCE_PACKAGE)
        mock_resource_dir.joinpath.assert_called_once_with(f"{config_key}.yaml")

    @patch('importlib_resources.files') # Corrected mock path
    @patch('builtins.open', new_callable=mock_open, read_data="key: value")
    @patch('yaml.safe_load')
    def test_get_configuration_handles_yaml_errors(self, mock_safe_load, mock_open_file, mock_files):
        """TDD Anchor: test_get_configuration_handles_yaml_errors (Combined with general errors)"""
        config_key = "bad_yaml_config"
        self.service.get_available_configurations = MagicMock(return_value=[config_key]) # Assume key is valid

        # Mock file path resolution
        mock_config_file_path = MagicMock()
        mock_config_file_path.exists.return_value = True
        mock_resource_dir = MagicMock()
        mock_resource_dir.joinpath.return_value = mock_config_file_path
        mock_files.return_value = mock_resource_dir

        # Simulate YAML parsing error
        mock_safe_load.side_effect = yaml.YAMLError("Simulated YAML Error")

        with self.assertRaises(ConfigurationError) as cm:
            self.service.get_configuration(config_key)
        self.assertIn(f"Error loading or parsing configuration file for key: {config_key}", str(cm.exception))
        mock_safe_load.assert_called_once()

    @patch('importlib_resources.files') # Corrected mock path
    @patch('builtins.open', new_callable=mock_open, read_data="key: value")
    def test_get_configuration_handles_io_errors(self, mock_open_file, mock_files):
        """TDD Anchor: test_get_configuration_handles_errors (IO specific)"""
        config_key = "io_error_config"
        self.service.get_available_configurations = MagicMock(return_value=[config_key]) # Assume key is valid

        # Mock file path resolution
        mock_config_file_path = MagicMock()
        mock_config_file_path.exists.return_value = True
        mock_resource_dir = MagicMock()
        mock_resource_dir.joinpath.return_value = mock_config_file_path
        mock_files.return_value = mock_resource_dir

        # Simulate an I/O error during open
        mock_open_file.side_effect = OSError("Simulated I/O Error")

        with self.assertRaises(ConfigurationError) as cm:
            self.service.get_configuration(config_key)
        self.assertIn(f"Error loading or parsing configuration file for key: {config_key}", str(cm.exception))
        mock_open_file.assert_called_once()

    # --- Tests for validate_custom_configuration ---

    def test_validate_custom_configuration_returns_dict(self):
        """TDD Anchor: test_validate_custom_configuration_returns_dict"""
        valid_config_str = """
        title: "Test Map"
        geopackage_path: "path/to/data.gpkg"
        geopackage_layer: "layer_name"
        location_id_col: "ID"
        location_name_col: "Name"
        """
        expected_dict = {
            "title": "Test Map",
            "geopackage_path": "path/to/data.gpkg",
            "geopackage_layer": "layer_name",
            "location_id_col": "ID",
            "location_name_col": "Name"
        }
        # Use pytest.raises for context management with potential exceptions
        result = self.service.validate_custom_configuration(valid_config_str)
        self.assertEqual(result, expected_dict)


    def test_validate_custom_configuration_checks_required_keys(self):
        """TDD Anchor: test_validate_custom_configuration_checks_required_keys"""
        missing_key_config_str = """
        title: "Test Map"
        # geopackage_path: "path/to/data.gpkg" # Missing
        geopackage_layer: "layer_name"
        location_id_col: "ID"
        location_name_col: "Name"
        """
        with self.assertRaises(ValidationError) as cm:
            self.service.validate_custom_configuration(missing_key_config_str)
        self.assertIn("Missing required configuration keys", str(cm.exception))
        self.assertIn("'geopackage_path'", str(cm.exception)) # Check specific missing key

    @patch('geopandas.read_file')
    def test_validate_custom_configuration_checks_geopackage_layer(self, mock_gpd_read_file):
        """TDD Anchor: test_validate_custom_configuration_checks_geopackage_layer"""
        valid_config_str = """
        title: "Test Map"
        geopackage_path: "path/to/data.gpkg"
        geopackage_layer: "valid_layer"
        location_id_col: "ID"
        location_name_col: "Name"
        """
        # Simulate geopandas successfully reading the layer
        mock_gpd_read_file.return_value = MagicMock() # Return a dummy GeoDataFrame

        # This should pass
        self.service.validate_custom_configuration(valid_config_str)
        mock_gpd_read_file.assert_called_once_with("path/to/data.gpkg", layer="valid_layer")

        # Simulate geopandas failing to read the layer
        mock_gpd_read_file.reset_mock()
        mock_gpd_read_file.side_effect = Exception("Layer not found or other GeoPandas error")

        invalid_layer_config_str = """
        title: "Test Map"
        geopackage_path: "path/to/data.gpkg"
        geopackage_layer: "invalid_layer"
        location_id_col: "ID"
        location_name_col: "Name"
        """
        with self.assertRaises(ValidationError) as cm:
            self.service.validate_custom_configuration(invalid_layer_config_str)
        self.assertIn("Error reading GeoPackage layer 'invalid_layer' from 'path/to/data.gpkg'", str(cm.exception))
        mock_gpd_read_file.assert_called_once_with("path/to/data.gpkg", layer="invalid_layer")


    def test_validate_custom_configuration_handles_yaml_errors(self):
        """TDD Anchor: test_validate_custom_configuration_handles_yaml_errors"""
        invalid_yaml_str = "title: Test Map\n  geopackage_path: 'path.gpkg'" # Indentation error
        with self.assertRaises(ValidationError) as cm:
            self.service.validate_custom_configuration(invalid_yaml_str)
        self.assertIn("Invalid YAML format in custom configuration", str(cm.exception))

    # TDD Anchor: test_validate_custom_configuration_handles_errors is implicitly covered
    # by the specific error handling tests above (missing keys, geopackage, yaml).
    # We can add a test for unexpected errors if needed, but often specific cases are better.


if __name__ == '__main__':
    unittest.main()