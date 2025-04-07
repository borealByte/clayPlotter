import yaml
import os

class InvalidFormatError(Exception):
    """Custom exception for invalid YAML format."""
    pass

class InvalidDataError(Exception):
    """Custom exception for invalid data structure or content."""
    pass

class DataLoader:
    """Loads and validates user data, typically from YAML files."""

    def __init__(self, expected_keys={'name', 'value'}):
        """
        Initializes the DataLoader.

        Args:
            expected_keys (set): A set of keys expected in each data item (dictionary).
                                 Defaults to {'name', 'value'}.
        """
        self.expected_keys = expected_keys

    def load_data(self, file_path):
        """
        Loads data from a YAML file and validates its structure.

        Args:
            file_path (str): The path to the YAML file.

        Returns:
            list: The loaded and validated data (list of dictionaries).

        Raises:
            FileNotFoundError: If the file does not exist.
            InvalidFormatError: If the file is not valid YAML.
            InvalidDataError: If the data structure or content is invalid.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise InvalidFormatError(f"Invalid YAML format in {file_path}: {e}") from e
        except Exception as e: # Catch other potential file reading errors
             raise IOError(f"Error reading file {file_path}: {e}") from e

        if data is None: # Handle empty YAML file case
            data = [] # Or raise InvalidDataError if empty is invalid

        # Validate the structure after successful loading
        self._validate_structure(data)

        return data


    def _validate_structure(self, data):
        """
        Validates the structure and content of the loaded data.
        (Internal helper method)

        Args:
            data: The data loaded from the file.

        Returns:
            bool: True if the data is valid.
Raises:
    InvalidDataError: If the data structure or content is invalid.
"""
        if not isinstance(data, list):
            raise InvalidDataError("Data must be a list of items.")

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise InvalidDataError(f"Item at index {i} is not a dictionary.")

            missing_keys = self.expected_keys - item.keys()
            if missing_keys:
                raise InvalidDataError(f"Item at index {i} is missing required keys: {missing_keys}")

            # Optional: Add type checks if needed based on requirements/tests
            # Example: Check if 'value' is numeric
            if 'value' in item and not isinstance(item['value'], (int, float)):
                 raise InvalidDataError(f"Item at index {i} has non-numeric 'value': {item['value']}")

        # If the loop completes without errors, the structure is valid
        return True # Indicate successful validation