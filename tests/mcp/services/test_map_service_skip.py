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
from clayPlotter.mcp.services.map_service import MapService

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

if __name__ == '__main__':
    unittest.main()