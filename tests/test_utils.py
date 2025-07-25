"""Tests for utility functions."""
from unittest import TestCase
from unittest.mock import patch

from mlx.traceability.traceability import get_sort_function


class TestGetSortFunction(TestCase):
    """Test the get_sort_function utility function"""

    def test_valid_string_specification(self):
        """Test that valid string specifications are converted to functions"""
        sort_func = get_sort_function('builtins.sorted')
        self.assertEqual(sort_func, sorted)

    def test_natsort_string_specification(self):
        """Test that natsort string specification works"""
        try:
            import natsort
            sort_func = get_sort_function('natsort.natsorted')
            self.assertEqual(sort_func, natsort.natsorted)
        except ImportError:
            self.skipTest("natsort not available")

    def test_callable_object_deprecated(self):
        """Test that callable objects still work but generate deprecation warning"""
        with patch('mlx.traceability.traceability.report_warning') as mock_warning:
            sort_func = get_sort_function(sorted)
            self.assertEqual(sort_func, sorted)
            mock_warning.assert_called_once()
            warning_message = mock_warning.call_args[0][0]
            self.assertIn("deprecated", warning_message)
            self.assertIn("string notation", warning_message)

    def test_invalid_module_string(self):
        """Test handling of invalid module in string specification"""
        with self.assertRaises(ValueError):
            get_sort_function('nonexistent_module.function')

    def test_invalid_function_string(self):
        """Test handling of invalid function in valid module"""
        with self.assertRaises(ValueError):
            get_sort_function('builtins.nonexistent_function')

    def test_malformed_string_specification(self):
        """Test handling of malformed string specifications"""
        with self.assertRaises(ValueError):
            get_sort_function('no_dot_in_string')

    def test_empty_string(self):
        """Test handling of empty string"""
        with self.assertRaises(ValueError):
            get_sort_function('')
