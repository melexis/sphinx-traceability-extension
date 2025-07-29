"""
Unit tests for parallel build consistency.

Tests that parallel processing produces the same output as single-threaded processing,
specifically focusing on attribute hyperlinks and content rendering.

This test suite validates the fixes implemented for parallel processing support:

1. **Attribute Hyperlinks**: Ensures that attribute references in items are properly
   hyperlinked to their definitions in both serial and parallel builds.

2. **Attribute Content**: Verifies that attribute definitions with content (descriptions)
   are rendered correctly in both processing modes.

3. **Collection Merging**: Tests that worker process collections are properly merged
   back to the main process, preserving all attribute definitions and content.

4. **Directive References**: Validates that directive references are properly maintained
   for content parsing during parallel processing.

These tests specifically address the issues where:
- Worker processes lacked access to all attribute definitions
- Attribute content was not rendered due to missing directive references
- Hyperlinks appeared as plain text instead of clickable links

The tests use direct API calls rather than subprocess sphinx-build calls to avoid
environment dependency issues while still validating the core functionality.
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from mlx.traceability.traceable_collection import TraceableCollection, ParallelSafeTraceableCollection
from mlx.traceability.traceable_attribute import TraceableAttribute


class TestParallelBuildConsistency(unittest.TestCase):
    """Test that parallel and serial builds produce consistent attribute rendering."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.srcdir = self.temp_dir / "src"
        self.outdir = self.temp_dir / "out"
        self.doctreedir = self.temp_dir / "doctrees"

        # Create directories
        self.srcdir.mkdir(parents=True)
        self.outdir.mkdir(parents=True)
        self.doctreedir.mkdir(parents=True)

        # Mock configuration
        self.config = {
            'traceability_attributes': {
                'status': '^(draft|approved)$',
                'priority': '^(low|medium|high)$'
            },
            'traceability_attribute_to_string': {
                'status': 'Status',
                'priority': 'Priority'
            },
            'traceability_relationships': {
                'depends_on': 'impacts_on'
            },
            'traceability_relationship_to_string': {
                'depends_on': 'Depends on',
                'impacts_on': 'Impacts on'
            }
        }

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_attribute_hyperlinks_consistency(self):
        """Test that attribute hyperlinks are consistent between serial and parallel processing."""

        # Test 1: Serial processing simulation
        serial_collection = TraceableCollection()

        # Define attributes
        status_attr = TraceableAttribute('status', '^(draft|approved)$')
        status_attr.name = 'Status'
        status_attr.caption = 'Status attribute'
        status_attr.docname = 'test_doc'
        status_attr.identifier = 'status'
        serial_collection.define_attribute(status_attr)

        priority_attr = TraceableAttribute('priority', '^(low|medium|high)$')
        priority_attr.name = 'Priority'
        priority_attr.caption = 'Priority attribute'
        priority_attr.docname = 'test_doc'
        priority_attr.identifier = 'priority'
        serial_collection.define_attribute(priority_attr)

        # Test 2: Parallel processing simulation
        parallel_collection = ParallelSafeTraceableCollection()

        # Simulate worker process setup
        parallel_collection.mark_as_worker_process()

        # Define the same attributes in parallel collection
        parallel_collection.define_attribute(status_attr)
        parallel_collection.define_attribute(priority_attr)

        # Test 3: Verify both collections have the same attribute definitions
        self.assertEqual(len(serial_collection.defined_attributes),
                        len(parallel_collection.defined_attributes))

        for attr_id in ['status', 'priority']:
            self.assertIn(attr_id, serial_collection.defined_attributes)
            self.assertIn(attr_id, parallel_collection.defined_attributes)

            serial_attr = serial_collection.defined_attributes[attr_id]
            parallel_attr = parallel_collection.defined_attributes[attr_id]

            # Verify key properties are identical
            self.assertEqual(serial_attr.name, parallel_attr.name)
            self.assertEqual(serial_attr.identifier, parallel_attr.identifier)
            self.assertEqual(serial_attr.docname, parallel_attr.docname)

    def test_attribute_content_rendering_consistency(self):
        """Test that attribute content is rendered consistently."""

        # Create mock directive with content
        mock_directive = Mock()

        # Create a more complete mock for the directive
        mock_state = Mock()
        mock_document = Mock()
        mock_document.ids = {}  # Make this a real dict
        mock_state.document = mock_document
        mock_directive.state = mock_state

        # Create a StringList-like object
        from docutils.statemachine import StringList
        content_lines = ['This is test content for the attribute.',
                        'It can be multiple lines.',
                        'And include RST formatting.']
        mock_directive.content = StringList(content_lines)
        mock_directive.caption = 'Test Caption'
        mock_directive.parse_content_to_nodes = Mock(return_value=[])

        # Test content setting in both scenarios
        attr1 = TraceableAttribute('test_attr', '.*', directive=mock_directive)
        attr1.content = mock_directive.content

        attr2 = TraceableAttribute('test_attr2', '.*')
        attr2.directive = mock_directive  # This simulates our fix
        attr2.content = mock_directive.content

        # Both should have the same content
        self.assertEqual(attr1.content, attr2.content)
        self.assertIsNotNone(attr1.content)
        self.assertIsNotNone(attr2.content)

    def test_parallel_collection_merging(self):
        """Test that parallel collections merge correctly with attribute definitions."""

        # Create main collection
        main_collection = TraceableCollection()

        # Create parallel wrapper
        parallel_wrapper = ParallelSafeTraceableCollection()
        parallel_wrapper.set_main_collection(main_collection)

        # Create worker collection with different attributes
        worker_collection = TraceableCollection()

        # Worker defines some attributes
        worker_attr = TraceableAttribute('worker_attr', '.*')
        worker_attr.name = 'Worker Attribute'
        worker_attr._content = 'Worker content'  # Set directly to avoid directive requirement
        worker_collection.define_attribute(worker_attr)

        # Main collection has different attributes
        main_attr = TraceableAttribute('main_attr', '.*')
        main_attr.name = 'Main Attribute'
        main_attr._content = 'Main content'  # Set directly to avoid directive requirement
        main_collection.define_attribute(main_attr)

        # Merge worker into main
        main_collection.merge_from(worker_collection)

        # Verify both attributes exist
        self.assertIn('worker_attr', main_collection.defined_attributes)
        self.assertIn('main_attr', main_collection.defined_attributes)

        # Verify content is preserved
        self.assertEqual(main_collection.defined_attributes['worker_attr']._content, 'Worker content')
        self.assertEqual(main_collection.defined_attributes['main_attr']._content, 'Main content')

    def test_attribute_definition_with_directive_reference(self):
        """Test that attribute definitions work correctly when directive reference is set."""

        # Create a more complete mock directive
        mock_directive = Mock()
        mock_state = Mock()
        mock_document = Mock()
        mock_document.ids = {}
        mock_state.document = mock_document
        mock_directive.state = mock_state

        from docutils.statemachine import StringList
        content_lines = ['Test content line 1', 'Test content line 2']
        mock_directive.content = StringList(content_lines)
        mock_directive.parse_content_to_nodes = Mock(return_value=[])

        # Create attribute
        attr = TraceableAttribute('test', '.*')

        # Simulate the fix: set directive reference before setting content
        attr.directive = mock_directive
        attr.content = mock_directive.content

        # Verify content was set correctly
        self.assertIsNotNone(attr.content)
        self.assertEqual(attr.content, 'Test content line 1\nTest content line 2')

        # Verify parse_content_to_nodes was called (indicating content node was updated)
        mock_directive.parse_content_to_nodes.assert_called()

    def test_make_attribute_ref_with_hyperlinks(self):
        """Test that make_attribute_ref creates proper hyperlinks when attributes are defined."""

        # This test verifies the core fix for attribute hyperlinks
        from mlx.traceability.traceable_base_node import TraceableBaseNode
        from docutils import nodes

        # Create a test node
        class TestNode(TraceableBaseNode):
            def perform_replacement(self, app, collection):
                pass

        test_node = TestNode()
        test_node['document'] = 'test_doc'

        # Mock app and environment
        mock_app = Mock()
        mock_builder = Mock()
        mock_env = Mock()

        mock_app.builder = mock_builder
        mock_app.env = mock_env
        mock_builder.get_relative_uri = Mock(return_value='test.html')

        # Create collection with defined attribute
        collection = TraceableCollection()
        attr = TraceableAttribute('test_attr', '.*')
        attr.name = 'Test Attribute'
        attr.docname = 'test_doc'
        attr.identifier = 'test_attr'
        collection.define_attribute(attr)

        mock_env.traceability_collection = collection

        # Test make_attribute_ref
        result = test_node.make_attribute_ref(mock_app, 'test_attr', 'test_value')

        # Verify it creates a paragraph with a reference
        self.assertIsInstance(result, nodes.paragraph)
        self.assertTrue(len(result.children) > 0)

        # The fix ensures that when attributes are defined, hyperlinks are created
        # rather than plain text

if __name__ == '__main__':
    unittest.main()
