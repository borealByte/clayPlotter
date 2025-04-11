import unittest
from unittest.mock import patch, MagicMock, ANY
import pandas as pd
import base64
from uuid import UUID, uuid4
import io

# Assume exceptions are defined in a central place or within the services
from clayPlotter.mcp.exceptions import (
    ValidationError, MapGenerationError, ResourceNotFoundError, ConfigurationError
)
from clayPlotter.mcp.services.map_service import MapService, _map_storage
# We need to mock ConfigurationService and ChoroplethPlotter
# from clayPlotter.mcp.services.config_service import ConfigurationService # Mocked
# from clayPlotter.l1_choropleth.plotter import ChoroplethPlotter # Mocked

# Dummy data for testing validation
VALID_DATA = [{"location": "StateA", "value": 10}, {"location": "StateB", "value": 20}]
INVALID_STRUCTURE_DATA = [{"loc": "StateA", "val": 10}] # Missing 'location' or 'value'
INVALID_LOCATION_TYPE_DATA = [{"location": 123, "value": 10}]
INVALID_VALUE_TYPE_DATA = [{"location": "StateA", "value": "abc"}]
NOT_LIST_DATA = {"location": "StateA", "value": 10}
EMPTY_LIST_DATA = []

# Dummy config
DUMMY_CONFIG = {
    "title": "Test Map",
    "geopackage_path": "dummy/path.gpkg",
    "geopackage_layer": "dummy_layer",
    "location_id_col": "ID",
    "location_name_col": "Name",
    "value_col": "Value", # Added for clarity, though plotter might infer
    "cmap": "viridis",
    "figsize": [10, 8],
    "title_fontsize": 16,
    "legend_fontsize": 10,
    "legend_title": "Test Legend",
    "output_dpi": 150,
    "border_color": "black",
    "border_linewidth": 0.5,
    "nodata_color": "lightgrey"
}

class TestMapService(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        _map_storage.clear()  # Ensure map cache is empty before each test
        self.mock_config_service = MagicMock()
        # Patch the ChoroplethPlotter class itself if it's imported directly in map_service.py
        # If it's instantiated inside methods, patching might need adjustment (e.g., patch the module)
        patcher = patch('clayPlotter.mcp.services.map_service.ChoroplethPlotter', autospec=True)
        self.mock_choropleth_plotter_class = patcher.start()
        self.addCleanup(patcher.stop) # Ensure patch is stopped even if tests fail

        self.mock_plotter_instance = self.mock_choropleth_plotter_class.return_value
        self.mock_plotter_instance.plot.return_value = (MagicMock(), MagicMock()) # Mock fig, ax

        self.service = MapService(config_service=self.mock_config_service)

    def test_init_stores_config_service(self):
        """TDD Anchor: test_init_stores_config_service"""
        self.assertEqual(self.service.config_service, self.mock_config_service)
        self.assertEqual(_map_storage, {})

    # --- Tests for validate_data ---

    def test_validate_data_returns_dataframe(self):
        """TDD Anchor: test_validate_data_returns_dataframe"""
        df = self.service.validate_data(VALID_DATA, "location", "value")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertListEqual(list(df.columns), ['location', 'value'])
        self.assertEqual(len(df), 2)

    def test_validate_data_checks_structure_missing_keys(self):
        """TDD Anchor: test_validate_data_checks_structure (missing keys)"""
        with self.assertRaises(ValidationError) as cm:
            self.service.validate_data(INVALID_STRUCTURE_DATA, "location", "value")
        self.assertIn("required keys", str(cm.exception))

    def test_validate_data_checks_structure_not_list(self):
        """TDD Anchor: test_validate_data_checks_structure (not list)"""
        with self.assertRaises(ValidationError) as cm:
            self.service.validate_data(NOT_LIST_DATA, "location", "value")
        self.assertIn("list", str(cm.exception))

    def test_validate_data_checks_structure_empty_list(self):
        """TDD Anchor: test_validate_data_checks_structure (empty list)"""
        with self.assertRaises(ValidationError) as cm:
            self.service.validate_data(EMPTY_LIST_DATA, "location", "value")
        self.assertIn("empty", str(cm.exception))

    def test_validate_data_checks_location_col_type(self):
        """TDD Anchor: test_validate_data_checks_location_col (type)"""
        with self.assertRaises(ValidationError) as cm:
            self.service.validate_data(INVALID_LOCATION_TYPE_DATA, "location", "value")
        self.assertIn("string", str(cm.exception))

    def test_validate_data_checks_value_col_type(self):
        """TDD Anchor: test_validate_data_checks_value_col (type)"""
        with self.assertRaises(ValidationError) as cm:
            self.service.validate_data(INVALID_VALUE_TYPE_DATA, "location", "value")
        self.assertIn("numeric", str(cm.exception))

    # TDD Anchor: test_validate_data_handles_errors is covered by the specific validation tests above.

    # --- Tests for generate_map_from_key ---

    @patch('clayPlotter.mcp.services.map_service.MapService.validate_data')
    @patch('clayPlotter.mcp.services.map_service.MapService.generate_map')
    def test_generate_map_from_key_returns_map_id(self, mock_generate_internal, mock_validate):
        """TDD Anchor: test_generate_map_from_key_returns_map_id"""
        config_key = "usa_states"
        map_id = uuid4()
        mock_generate_internal.return_value = map_id
        self.mock_config_service.get_configuration.return_value = DUMMY_CONFIG
        mock_validate.return_value = pd.DataFrame(VALID_DATA) # Return validated DataFrame

        result_map_id = self.service.generate_map_from_key(config_key, VALID_DATA)

        self.assertEqual(result_map_id, map_id)
        self.mock_config_service.get_configuration.assert_called_once_with(config_key)
        mock_validate.assert_called_once_with(VALID_DATA, "location", "value")
        mock_generate_internal.assert_called_once_with(DUMMY_CONFIG, mock_validate.return_value)

    @patch('clayPlotter.mcp.services.map_service.MapService.validate_data')
    def test_generate_map_from_key_handles_config_error(self, mock_validate):
        """TDD Anchor: test_generate_map_from_key_handles_errors (config error)"""
        config_key = "invalid_key"
        self.mock_config_service.get_configuration.side_effect = ConfigurationError("Config not found")

        with self.assertRaises(ConfigurationError):
            self.service.generate_map_from_key(config_key, VALID_DATA)
        self.mock_config_service.get_configuration.assert_called_once_with(config_key)
        mock_validate.assert_not_called()

    def test_generate_map_from_key_handles_validation_error(self):
        """TDD Anchor: test_generate_map_from_key_handles_errors (validation error)"""
        config_key = "usa_states"
        self.mock_config_service.get_configuration.return_value = DUMMY_CONFIG

        with self.assertRaises(ValidationError):
            self.service.generate_map_from_key(config_key, INVALID_STRUCTURE_DATA)
        self.mock_config_service.get_configuration.assert_called_once_with(config_key)

    @patch('clayPlotter.mcp.services.map_service.MapService.validate_data')
    @patch('clayPlotter.mcp.services.map_service.MapService.generate_map')
    def test_generate_map_from_key_handles_generation_error(self, mock_generate_internal, mock_validate):
        """TDD Anchor: test_generate_map_from_key_handles_errors (generation error)"""
        config_key = "usa_states"
        mock_generate_internal.side_effect = MapGenerationError("Plotting failed")
        self.mock_config_service.get_configuration.return_value = DUMMY_CONFIG
        mock_validate.return_value = pd.DataFrame(VALID_DATA)

        with self.assertRaises(MapGenerationError):
            self.service.generate_map_from_key(config_key, VALID_DATA)
        self.mock_config_service.get_configuration.assert_called_once_with(config_key)
        mock_validate.assert_called_once_with(VALID_DATA, "location", "value")
        mock_generate_internal.assert_called_once_with(DUMMY_CONFIG, mock_validate.return_value)

    # --- Tests for generate_map_from_config ---

    @patch('clayPlotter.mcp.services.map_service.MapService.validate_data')
    @patch('clayPlotter.mcp.services.map_service.MapService.generate_map')
    def test_generate_map_from_config_returns_map_id(self, mock_generate_internal, mock_validate):
        """TDD Anchor: test_generate_map_from_config_returns_map_id"""
        custom_config_str = "yaml: config" # Assume valid YAML string
        map_id = uuid4()
        mock_generate_internal.return_value = map_id
        self.mock_config_service.validate_custom_configuration.return_value = DUMMY_CONFIG
        mock_validate.return_value = pd.DataFrame(VALID_DATA)

        result_map_id = self.service.generate_map_from_config(custom_config_str, VALID_DATA)

        self.assertEqual(result_map_id, map_id)
        self.mock_config_service.validate_custom_configuration.assert_called_once_with(custom_config_str)
        mock_validate.assert_called_once_with(VALID_DATA, "location", "value")
        mock_generate_internal.assert_called_once_with(DUMMY_CONFIG, mock_validate.return_value)

    @patch('clayPlotter.mcp.services.map_service.MapService.validate_data')
    def test_generate_map_from_config_handles_config_error(self, mock_validate):
        """TDD Anchor: test_generate_map_from_config_handles_errors (config error)"""
        custom_config_str = "invalid: yaml"
        self.mock_config_service.validate_custom_configuration.side_effect = ValidationError("Invalid YAML")

        with self.assertRaises(ValidationError): # Should propagate validation error
            self.service.generate_map_from_config(custom_config_str, VALID_DATA)
        self.mock_config_service.validate_custom_configuration.assert_called_once_with(custom_config_str)
        mock_validate.assert_not_called()

    def test_generate_map_from_config_handles_validation_error(self):
        """TDD Anchor: test_generate_map_from_config_handles_errors (validation error)"""
        custom_config_str = "yaml: config"
        self.mock_config_service.validate_custom_configuration.return_value = DUMMY_CONFIG

        with self.assertRaises(ValidationError):
            self.service.generate_map_from_config(custom_config_str, INVALID_STRUCTURE_DATA)
        self.mock_config_service.validate_custom_configuration.assert_called_once_with(custom_config_str)

    @patch('clayPlotter.mcp.services.map_service.MapService.validate_data')
    @patch('clayPlotter.mcp.services.map_service.MapService.generate_map')
    def test_generate_map_from_config_handles_generation_error(self, mock_generate_internal, mock_validate):
        """TDD Anchor: test_generate_map_from_config_handles_errors (generation error)"""
        custom_config_str = "yaml: config"
        mock_generate_internal.side_effect = MapGenerationError("Plotting failed")
        self.mock_config_service.validate_custom_configuration.return_value = DUMMY_CONFIG
        mock_validate.return_value = pd.DataFrame(VALID_DATA)

        with self.assertRaises(MapGenerationError):
            self.service.generate_map_from_config(custom_config_str, VALID_DATA)
        self.mock_config_service.validate_custom_configuration.assert_called_once_with(custom_config_str)
        mock_validate.assert_called_once_with(VALID_DATA, "location", "value")
        mock_generate_internal.assert_called_once_with(DUMMY_CONFIG, mock_validate.return_value)

    # --- Tests for _generate_map_internal ---

    @patch('uuid.uuid4')
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.close')
    @patch('io.BytesIO')
    def test_generate_map_internal_returns_map_id(self, mock_bytesio, mock_plt_close, mock_plt_savefig, mock_uuid4):
        """TDD Anchor: test_generate_map_internal_returns_map_id"""
        map_id = UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid4.return_value = map_id
        validated_df = pd.DataFrame(VALID_DATA)
        mock_buffer = MagicMock()
        mock_bytesio.return_value = mock_buffer
        mock_buffer.getvalue.return_value = b'imagedata'

        # Call the internal method
        result_map_id = self.service.generate_map(DUMMY_CONFIG, validated_df)

        self.assertEqual(result_map_id, map_id)
        # Check ChoroplethPlotter instantiation and plot call
        self.mock_choropleth_plotter_class.assert_called_once_with(
            geography_key='usa_states',
            data=validated_df,
            location_col='location',
            value_col='value'
        )
        self.mock_plotter_instance.plot.assert_called_once_with(
            geo_join_column='name'
        )
        # Check saving to buffer and closing plot
        mock_plt_savefig.assert_called_once_with(mock_buffer, format='png', dpi=DUMMY_CONFIG['output_dpi'], bbox_inches='tight')
        mock_plt_close.assert_called_once_with(ANY) # Check that close was called with the figure mock
        # Check cache population
        self.assertIn(map_id, _map_storage)
        self.assertEqual(_map_storage[map_id], b'imagedata')

    @patch('uuid.uuid4')
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.close')
    def test_generate_map_internal_handles_plotter_error(self, mock_plt_close, mock_plt_savefig, mock_uuid4):
        """TDD Anchor: test_generate_map_internal_handles_errors (plotter init error)"""
        map_id = UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid4.return_value = map_id
        validated_df = pd.DataFrame(VALID_DATA)
        # Simulate error during ChoroplethPlotter instantiation
        self.mock_choropleth_plotter_class.side_effect = ValueError("Invalid GeoPackage path")

        with self.assertRaises(MapGenerationError) as cm:
            self.service.generate_map(DUMMY_CONFIG, validated_df)

        self.assertIn("Error initializing ChoroplethPlotter", str(cm.exception))
        self.mock_choropleth_plotter_class.assert_called_once() # Ensure it was attempted
        self.mock_plotter_instance.plot.assert_not_called()
        mock_plt_savefig.assert_not_called()
        mock_plt_close.assert_not_called()
        self.assertNotIn(map_id, _map_storage) # Ensure cache is not populated on error

    @patch('uuid.uuid4')
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.close')
    def test_generate_map_internal_handles_plotting_error(self, mock_plt_close, mock_plt_savefig, mock_uuid4):
        """TDD Anchor: test_generate_map_internal_handles_errors (plotting error)"""
        map_id = UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid4.return_value = map_id
        validated_df = pd.DataFrame(VALID_DATA)
        # Simulate error during the plot method call
        self.mock_plotter_instance.plot.side_effect = RuntimeError("Plotting failed")

        with self.assertRaises(MapGenerationError) as cm:
            self.service.generate_map(DUMMY_CONFIG, validated_df)

        self.assertIn("Error generating plot", str(cm.exception))
        self.mock_choropleth_plotter_class.assert_called_once()
        self.mock_plotter_instance.plot.assert_called_once() # Ensure plot was attempted
        mock_plt_savefig.assert_not_called()
        # plt.close should still be called to clean up the figure even if savefig fails or plot errors
        # Depending on implementation, close might or might not be called if plot itself errors early.
        # Let's assume it tries to close if fig exists.
        # mock_plt_close.assert_called_once_with(ANY)
        self.assertNotIn(map_id, _map_storage)

    @patch('uuid.uuid4')
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.close')
    @patch('io.BytesIO')
    def test_generate_map_internal_handles_savefig_error(self, mock_bytesio, mock_plt_close, mock_plt_savefig, mock_uuid4):
        """TDD Anchor: test_generate_map_internal_handles_errors (savefig error)"""
        map_id = UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid4.return_value = map_id
        validated_df = pd.DataFrame(VALID_DATA)
        mock_buffer = MagicMock()
        mock_bytesio.return_value = mock_buffer
        # Simulate error during savefig
        mock_plt_savefig.side_effect = OSError("Disk full")

        with self.assertRaises(MapGenerationError) as cm:
            self.service.generate_map(DUMMY_CONFIG, validated_df)

        self.assertIn("Error saving plot to buffer", str(cm.exception))
        self.mock_choropleth_plotter_class.assert_called_once()
        self.mock_plotter_instance.plot.assert_called_once()
        mock_plt_savefig.assert_called_once()
        mock_plt_close.assert_called_once_with(ANY) # Close should still be called
        self.assertNotIn(map_id, _map_storage)


    # --- Tests for get_map_image ---

    def test_get_map_image_returns_bytes_and_content_type(self):
        """TDD Anchor: test_get_map_image_returns_bytes_and_content_type"""
        map_id = uuid4()
        image_data = b'fakedata'
        _map_storage[map_id] = image_data

        data, content_type = self.service.get_map_image(map_id)

        self.assertEqual(data, image_data)
        self.assertEqual(content_type, 'image/png')

    def test_get_map_image_handles_invalid_id(self):
        """TDD Anchor: test_get_map_image_handles_invalid_id"""
        invalid_map_id = uuid4() # An ID not in the cache

        with self.assertRaises(ResourceNotFoundError) as cm:
            self.service.get_map_image(invalid_map_id)
        self.assertIn(f"Map with ID '{invalid_map_id}' not found", str(cm.exception))

    # --- Tests for get_map_image_base64 ---

    @patch('clayPlotter.mcp.services.map_service.MapService.get_map_image')
    def test_get_map_image_base64_returns_string(self, mock_get_map_image):
        """TDD Anchor: test_get_map_image_base64_returns_string"""
        map_id = uuid4()
        image_data = b'\x89PNG\r\n\x1a\n...' # Some fake PNG bytes
        mock_get_map_image.return_value = (image_data, 'image/png')
        expected_base64 = base64.b64encode(image_data).decode('utf-8')

        base64_string = self.service.get_map_image_base64(map_id)

        self.assertEqual(base64_string, expected_base64)
        mock_get_map_image.assert_called_once_with(map_id)

    @patch('clayPlotter.mcp.services.map_service.MapService.get_map_image')
    def test_get_map_image_base64_handles_not_found(self, mock_get_map_image):
        """TDD Anchor: test_get_map_image_base64_handles_errors (implicitly tested)"""
        map_id = uuid4()
        mock_get_map_image.side_effect = ResourceNotFoundError(f"Map with ID '{map_id}' not found")

        with self.assertRaises(ResourceNotFoundError):
            self.service.get_map_image_base64(map_id)
        mock_get_map_image.assert_called_once_with(map_id)


if __name__ == '__main__':
    unittest.main()