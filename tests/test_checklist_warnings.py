"""Tests for checklist warning functionality."""

import unittest
from unittest.mock import Mock, patch

from mlx.traceability.traceability import warn_missing_checklist_items
from mlx.traceability.traceable_item import TraceableItem
from mlx.traceability.traceable_collection import TraceableCollection


class TestChecklistWarnings(unittest.TestCase):
    """Test cases for warn_missing_checklist_items function."""

    def setUp(self):
        """Set up test fixtures."""
        self.collection = TraceableCollection()
        self.query_results = {}

        # Create mock items for testing
        self.create_test_items()

    def create_test_items(self):
        """Create test items with different directive types."""
        # Items that should be checklist-items (are defined as checklist-item directives)
        checklist_items = ['QUE-UNIT_TESTS', 'QUE-PACKAGE_TEST', 'CL-SOME_ITEM']
        for item_id in checklist_items:
            # Create a proper mock directive that supports dictionary-like access
            mock_directive = Mock()
            mock_directive.state.document.ids = {}
            item = TraceableItem(item_id, directive=mock_directive)
            item.directive_type = 'ChecklistItemDirective'
            self.collection.add_item(item)

        # Items that should NOT be checklist-items (are defined as regular item directives)
        regular_items = ['CL-UNDEFINED_CL_ITEM', 'DESIGN-TRACEABILITY']
        for item_id in regular_items:
            # Create a proper mock directive that supports dictionary-like access
            mock_directive = Mock()
            mock_directive.state.document.ids = {}
            item = TraceableItem(item_id, directive=mock_directive)
            item.directive_type = 'ItemDirective'
            self.collection.add_item(item)

        # Items that don't match the regex pattern
        non_matching_items = ['OTHER_ITEM', 'UNRELATED_ITEM']
        for item_id in non_matching_items:
            # Create a proper mock directive that supports dictionary-like access
            mock_directive = Mock()
            mock_directive.state.document.ids = {}
            item = TraceableItem(item_id, directive=mock_directive)
            item.directive_type = 'ItemDirective'
            self.collection.add_item(item)

    def create_query_results(self, item_ids):
        """Create mock query results for given item IDs."""
        self.query_results = {}
        for item_id in item_ids:
            mock_item_info = Mock()
            mock_item_info.mr_id = 138
            self.query_results[item_id] = mock_item_info

    @patch('mlx.traceability.traceability.report_warning')
    def test_warn_for_regular_item_matching_regex(self, mock_report_warning):
        """Test that warnings are generated for regular items that match the regex."""
        # Setup: CL-UNDEFINED_CL_ITEM is in query_results and matches regex
        self.create_query_results(['CL-UNDEFINED_CL_ITEM'])
        regex = r'CL-.*'

        # Execute
        warn_missing_checklist_items(regex, self.collection, self.query_results)

        # Verify: Warning should be generated
        mock_report_warning.assert_called_once()
        call_args = mock_report_warning.call_args[0][0]
        assert "CL-UNDEFINED_CL_ITEM" in call_args
        assert "merge/pull request 138" in call_args

    @patch('mlx.traceability.traceability.report_warning')
    def test_no_warn_for_checklist_item_matching_regex(self, mock_report_warning):
        """Test that no warnings are generated for checklist-items that match the regex."""
        # Setup: CL-SOME_ITEM is in query_results and matches regex, but is defined as checklist-item
        self.create_query_results(['CL-SOME_ITEM'])
        regex = r'CL-.*'

        # Execute
        warn_missing_checklist_items(regex, self.collection, self.query_results)

        # Verify: No warning should be generated
        mock_report_warning.assert_not_called()

    @patch('mlx.traceability.traceability.report_warning')
    def test_no_warn_for_items_not_matching_regex(self, mock_report_warning):
        """Test that no warnings are generated for items that don't match the regex."""
        # Setup: OTHER_ITEM is in query_results but doesn't match regex
        self.create_query_results(['OTHER_ITEM'])
        regex = r'CL-.*'

        # Execute
        warn_missing_checklist_items(regex, self.collection, self.query_results)

        # Verify: No warning should be generated
        mock_report_warning.assert_not_called()

    @patch('mlx.traceability.traceability.report_warning')
    def test_multiple_warnings_for_multiple_violations(self, mock_report_warning):
        """Test that multiple warnings are generated for multiple violations."""
        # Setup: Multiple items that should trigger warnings
        self.create_query_results(['CL-UNDEFINED_CL_ITEM', 'DESIGN-TRACEABILITY'])
        regex = r'(CL-|DESIGN-).*'

        # Execute
        warn_missing_checklist_items(regex, self.collection, self.query_results)

        # Verify: Two warnings should be generated
        assert mock_report_warning.call_count == 2

        # Check that both items are mentioned in warnings
        calls = mock_report_warning.call_args_list
        warning_texts = [call[0][0] for call in calls]
        assert any("CL-UNDEFINED_CL_ITEM" in text for text in warning_texts)
        assert any("DESIGN-TRACEABILITY" in text for text in warning_texts)

    @patch('mlx.traceability.traceability.report_warning')
    def test_mixed_scenario(self, mock_report_warning):
        """Test a mixed scenario with items that should and shouldn't trigger warnings."""
        # Setup: Mix of items that should and shouldn't trigger warnings
        self.create_query_results([
            'CL-UNDEFINED_CL_ITEM',  # Should warn (regular item matching regex)
            'CL-SOME_ITEM',          # Should NOT warn (checklist-item matching regex)
            'OTHER_ITEM',            # Should NOT warn (doesn't match regex)
            'QUE-UNIT_TESTS'         # Should NOT warn (checklist-item matching regex)
        ])
        regex = r'(CL-|QUE-).*'

        # Execute
        warn_missing_checklist_items(regex, self.collection, self.query_results)

        # Verify: Only one warning should be generated (for CL-UNDEFINED_CL_ITEM)
        assert mock_report_warning.call_count == 1
        call_args = mock_report_warning.call_args[0][0]
        assert "CL-UNDEFINED_CL_ITEM" in call_args

    @patch('mlx.traceability.traceability.report_warning')
    def test_empty_query_results(self, mock_report_warning):
        """Test behavior with empty query results."""
        # Setup: Empty query results
        self.create_query_results([])
        regex = r'CL-.*'

        # Execute
        warn_missing_checklist_items(regex, self.collection, self.query_results)

        # Verify: No warnings should be generated
        mock_report_warning.assert_not_called()

    @patch('mlx.traceability.traceability.report_warning')
    def test_empty_collection(self, mock_report_warning):
        """Test behavior with empty collection."""
        # Setup: Empty collection but items in query results
        empty_collection = TraceableCollection()
        self.create_query_results(['CL-UNDEFINED_CL_ITEM'])
        regex = r'CL-.*'

        # Execute
        warn_missing_checklist_items(regex, empty_collection, self.query_results)

        # Verify: Warning should be generated (no checklist-items in collection)
        mock_report_warning.assert_called_once()
        call_args = mock_report_warning.call_args[0][0]
        assert "CL-UNDEFINED_CL_ITEM" in call_args

    @patch('mlx.traceability.traceability.report_warning')
    def test_complex_regex_pattern(self, mock_report_warning):
        """Test with complex regex patterns."""
        # Setup: Items with different patterns
        self.create_query_results(['QUE-UNIT_TESTS', 'CL-UNDEFINED_CL_ITEM', 'DESIGN-TRACEABILITY'])
        regex = r'(QUE-|CL-).*'  # Matches QUE- and CL- prefixes

        # Execute
        warn_missing_checklist_items(regex, self.collection, self.query_results)

        # Verify: Only CL-UNDEFINED_CL_ITEM should trigger warning
        # (QUE-UNIT_TESTS is a checklist-item, DESIGN-TRACEABILITY doesn't match regex)
        assert mock_report_warning.call_count == 1
        call_args = mock_report_warning.call_args[0][0]
        assert "CL-UNDEFINED_CL_ITEM" in call_args


if __name__ == '__main__':
    unittest.main()
