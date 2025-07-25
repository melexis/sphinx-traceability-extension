"""Tests for callback configuration utilities"""
import unittest
from unittest.mock import patch, MagicMock

from mlx.traceability.callback_utils import get_callback_function, call_callback_function


class TestCallbackConfiguration(unittest.TestCase):
    """Test callback configuration utilities"""

    def test_get_callback_function_with_valid_string(self):
        """Test that valid string specifications are converted to functions"""
        callback_func = get_callback_function('builtins.sorted')
        self.assertEqual(callback_func, sorted)

    def test_get_callback_function_with_callable(self):
        """Test that callable objects work (backward compatibility)"""
        callback_func = get_callback_function(sorted)
        self.assertEqual(callback_func, sorted)

    def test_get_callback_function_with_invalid_module(self):
        """Test handling of invalid module in string specification"""
        with self.assertRaises(ImportError) as cm:
            get_callback_function('nonexistent_module.function')
        self.assertIn("Cannot import module 'nonexistent_module'", str(cm.exception))

    def test_get_callback_function_with_invalid_function(self):
        """Test handling of invalid function in valid module"""
        with self.assertRaises(AttributeError) as cm:
            get_callback_function('builtins.nonexistent_function')
        self.assertIn("has no attribute 'nonexistent_function'", str(cm.exception))

    def test_get_callback_function_with_malformed_string(self):
        """Test handling of function names without module paths"""
        # This should find the sorted function in built-ins
        callback_func = get_callback_function('sorted')
        self.assertEqual(callback_func, sorted)

    def test_get_callback_function_with_invalid_type(self):
        """Test handling of invalid types"""
        with self.assertRaises(TypeError) as cm:
            get_callback_function(123)
        self.assertIn("Invalid callback specification type", str(cm.exception))

    def test_get_callback_function_with_none(self):
        """Test handling of None"""
        result = get_callback_function(None)
        self.assertIsNone(result)

    def test_get_callback_function_with_empty_string(self):
        """Test handling of empty string"""
        result = get_callback_function('')
        self.assertIsNone(result)

    def test_call_callback_function_with_valid_string(self):
        """Test calling callback function with string specification"""
        # Create a mock callback function
        def mock_callback(name, collection):
            return f"Called with {name} and {collection}"

        # Mock the module import
        with patch('mlx.traceability.callback_utils.importlib.import_module') as mock_import:
            mock_module = MagicMock()
            mock_module.callback_function = mock_callback
            mock_import.return_value = mock_module

            result = call_callback_function(
                'test_module.callback_function',
                'test_name',
                'test_collection'
            )

            self.assertEqual(result, "Called with test_name and test_collection")
            mock_import.assert_called_once_with('test_module')

    def test_call_callback_function_with_callable(self):
        """Test calling callback function with callable object (backward compatibility)"""
        def mock_callback(name, collection):
            return f"Called with {name} and {collection}"

        result = call_callback_function(
            mock_callback,
            'test_name',
            'test_collection'
        )

        self.assertEqual(result, "Called with test_name and test_collection")

    def test_call_callback_function_with_none(self):
        """Test calling callback function with None"""
        result = call_callback_function(None, 'test_name', 'test_collection')
        self.assertIsNone(result)

    def test_call_callback_function_with_invalid_spec(self):
        """Test that invalid callback specs raise appropriate exceptions"""
        with self.assertRaises(ImportError):
            call_callback_function(
                'invalid.callback',
                'test_name',
                'test_collection'
            )

    def test_call_callback_function_with_builtin(self):
        """Test calling a built-in function by name"""
        result = call_callback_function('sorted', [3, 1, 2])
        self.assertEqual(result, [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
