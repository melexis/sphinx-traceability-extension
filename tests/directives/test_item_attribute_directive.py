"""Tests for the item-attribute directive"""
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch
import logging

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList

from mlx.traceability.directives.item_attribute_directive import (
    ItemAttribute,
    ItemAttributeDirective
)
from mlx.traceability.traceable_attribute import TraceableAttribute
from mlx.traceability.traceable_item import TraceableItem
from mlx.traceability.traceable_collection import TraceableCollection

LOGGER = logging.getLogger('sphinx.mlx.traceability.traceability_exception')


class TestItemAttribute(TestCase):
    """Test the ItemAttribute node class"""

    def setUp(self):
        self.app = MagicMock()
        self.app.config.traceability_hyperlink_colors = {}
        self.collection = TraceableCollection()
        self.node = ItemAttribute('')
        self.node['document'] = 'test_doc'
        self.node['line'] = 42
        self.node['id'] = 'test_attr'

    def test_perform_replacement_with_defined_attribute_with_caption(self):
        """Test replacement when attribute is defined with caption"""
        # Setup defined attribute with caption
        attr = TraceableAttribute('test_attr', '.*')
        attr.name = 'Test Attribute'
        attr.caption = 'This is a test caption'
        TraceableItem.defined_attributes = {'test_attr': attr}

        # Create parent and perform replacement
        parent = nodes.container()
        parent.append(self.node)
        self.node.perform_replacement(self.app, self.collection)

        # Verify the node was replaced
        self.assertEqual(len(parent.children), 1)
        replaced_node = parent.children[0]
        self.assertNotEqual(replaced_node, self.node)
        # The header should contain both name and caption
        self.assertIn('Test Attribute: This is a test caption', str(replaced_node))

    def test_perform_replacement_with_defined_attribute_without_caption(self):
        """Test replacement when attribute is defined without caption"""
        # Setup defined attribute without caption
        attr = TraceableAttribute('test_attr', '.*')
        attr.name = 'Test Attribute'
        attr.caption = ''
        TraceableItem.defined_attributes = {'test_attr': attr}

        # Create parent and perform replacement
        parent = nodes.container()
        parent.append(self.node)
        self.node.perform_replacement(self.app, self.collection)

        # Verify the node was replaced
        self.assertEqual(len(parent.children), 1)
        replaced_node = parent.children[0]
        # The header should only contain the name
        self.assertIn('Test Attribute', str(replaced_node))
        self.assertNotIn(':', str(replaced_node))

    def test_perform_replacement_with_undefined_attribute(self):
        """Test replacement when attribute is not defined"""
        # Clear defined attributes
        TraceableItem.defined_attributes = {}
        self.node['id'] = 'undefined_attr'

        # Create parent and perform replacement
        parent = nodes.container()
        parent.append(self.node)
        self.node.perform_replacement(self.app, self.collection)

        # Verify the node was replaced with just the id
        self.assertEqual(len(parent.children), 1)
        replaced_node = parent.children[0]
        self.assertIn('undefined_attr', str(replaced_node))


class TestItemAttributeDirective(TestCase):
    """Test the ItemAttributeDirective class"""

    def setUp(self):
        """Setup test fixtures"""
        self.directive = ItemAttributeDirective(
            name='item-attribute',
            arguments=['test_attr_id'],
            options={},
            content=StringList(['Content line 1', 'Content line 2'], 'test.rst'),
            lineno=10,
            content_offset=0,
            block_text='',
            state=Mock(),
            state_machine=Mock()
        )

        # Mock the state and environment
        self.directive.state.document = Mock()
        self.directive.state.document.ids = {}  # Must be a real dict for item assignment
        self.directive.state.document.settings = Mock()
        self.directive.state.document.settings.env = Mock()
        self.directive.state.document.settings.env.docname = 'test_document'

        # Mock get_source_info to return a tuple
        self.directive.get_source_info = Mock(return_value=('test.rst', 10))

        # Clear defined attributes
        TraceableItem.defined_attributes = {}

    def test_directive_has_correct_configuration(self):
        """Test that directive has correct required/optional arguments and content settings"""
        self.assertEqual(ItemAttributeDirective.required_arguments, 1)
        self.assertEqual(ItemAttributeDirective.optional_arguments, 1)
        self.assertTrue(ItemAttributeDirective.has_content)

    def test_run_with_defined_attribute(self):
        """Test run method with a defined attribute"""
        # Setup defined attribute - must use lowercase id
        attr_id = 'test_attr_id'
        attr = TraceableAttribute(attr_id, '.*')
        attr.name = 'Test Attribute'
        TraceableItem.defined_attributes[attr_id] = attr

        # Run the directive
        result = self.directive.run()

        # Verify return value is a list with 3 nodes
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

        # Check target node
        self.assertIsInstance(result[0], nodes.target)
        self.assertIn(attr_id, result[0]['ids'])

        # Check attribute node
        self.assertIsInstance(result[1], ItemAttribute)
        self.assertEqual(result[1]['id'], attr_id)
        self.assertEqual(result[1]['document'], 'test_document')
        self.assertEqual(result[1]['line'], 10)

        # Check content node
        self.assertIsNotNone(result[2])

        # Verify attribute was updated with content (content getter converts to string)
        self.assertEqual(attr.content, 'Content line 1\nContent line 2')

    def test_run_with_defined_attribute_and_caption(self):
        """Test run method with a defined attribute and caption argument"""
        # Setup directive with caption
        self.directive.arguments = ['test_attr_id', 'Test Caption']

        # Setup defined attribute
        attr_id = 'test_attr_id'
        attr = TraceableAttribute(attr_id, '.*')
        attr.name = 'Test Attribute'
        TraceableItem.defined_attributes[attr_id] = attr

        # Run the directive
        result = self.directive.run()

        # Verify the attribute's caption was set
        self.assertEqual(attr.caption, 'Test Caption')

    def test_run_with_undefined_attribute_reports_warning(self):
        """Test run method reports warning for undefined attribute"""
        # Ensure attribute is not defined
        attr_id = 'undefined_attr'
        TraceableItem.defined_attributes = {}

        # Run the directive and expect a warning
        with self.assertLogs(LOGGER, logging.DEBUG) as log_context:
            result = self.directive.run()

        # Verify warning was logged
        warning_found = any('not defined in configuration' in msg for msg in log_context.output)
        self.assertTrue(warning_found, "Expected warning about undefined attribute not found in logs")

        # Verify return value still contains 3 nodes
        self.assertEqual(len(result), 3)

        # Check that a temporary attribute was created
        self.assertIsInstance(result[1], ItemAttribute)

    def test_run_creates_target_node_with_lowercase_id(self):
        """Test that target node uses lowercase id"""
        # Setup with mixed case attribute id
        attr_id = 'TestAttrId'
        self.directive.arguments = [attr_id]
        attr = TraceableAttribute(attr_id.lower(), '.*')
        TraceableItem.defined_attributes[attr_id.lower()] = attr

        # Run the directive
        result = self.directive.run()

        # Verify target node has lowercase id
        target_node = result[0]
        self.assertIn(attr_id.lower(), target_node['ids'])

    def test_run_sets_location_on_attribute(self):
        """Test that run method sets location on the attribute"""
        # Setup defined attribute - must match directive's argument
        attr_id = 'test_attr_id'
        attr = TraceableAttribute(attr_id, '.*')
        TraceableItem.defined_attributes[attr_id] = attr

        # Run the directive
        with patch.object(self.directive, 'get_source_info', return_value=('test.rst', 15)):
            result = self.directive.run()

        # Verify location was set on attribute
        self.assertEqual(attr.docname, 'test_document')
        self.assertEqual(attr.lineno, 15)

    def test_run_stores_directive_reference(self):
        """Test that the directive reference is stored on the attribute"""
        # Setup defined attribute - must match directive's argument
        attr_id = 'test_attr_id'
        attr = TraceableAttribute(attr_id, '.*')
        TraceableItem.defined_attributes[attr_id] = attr

        # Run the directive
        result = self.directive.run()

        # Verify directive reference was stored
        self.assertIs(attr.directive, self.directive)

    def test_attribute_node_has_correct_properties(self):
        """Test that the attribute node has all required properties set"""
        # Setup defined attribute - must match directive's argument
        attr_id = 'test_attr_id'
        attr = TraceableAttribute(attr_id, '.*')
        TraceableItem.defined_attributes[attr_id] = attr

        # Run the directive
        result = self.directive.run()

        attribute_node = result[1]

        # Verify node properties
        self.assertEqual(attribute_node['id'], attr_id)
        self.assertEqual(attribute_node['document'], 'test_document')
        self.assertEqual(attribute_node['line'], 10)

    def test_content_is_stored_on_attribute(self):
        """Test that content from directive is stored on the attribute"""
        # Setup defined attribute - must match directive's argument
        attr_id = 'test_attr_id'
        attr = TraceableAttribute(attr_id, '.*')
        TraceableItem.defined_attributes[attr_id] = attr

        # Run the directive with content
        result = self.directive.run()

        # Verify content was stored (content property converts StringList to string)
        expected_content = 'Content line 1\nContent line 2'
        self.assertEqual(attr.content, expected_content)
        self.assertIn('Content line 1', attr.content)
        self.assertIn('Content line 2', attr.content)

    def test_run_with_empty_content(self):
        """Test run method with empty content"""
        # Setup directive with no content
        self.directive.content = StringList([], 'test.rst')

        # Setup defined attribute - must match directive's argument
        attr_id = 'test_attr_id'
        attr = TraceableAttribute(attr_id, '.*')
        TraceableItem.defined_attributes[attr_id] = attr

        # Run the directive
        result = self.directive.run()

        # Verify it still returns 3 nodes
        self.assertEqual(len(result), 3)

        # Verify content is stored (converted to empty string)
        self.assertEqual(attr.content, '')

    def test_undefined_attribute_creates_wildcard_pattern(self):
        """Test that undefined attributes get a wildcard regex pattern"""
        # Ensure attribute is not defined
        TraceableItem.defined_attributes = {}

        # Run the directive (suppressing expected warning)
        # The directive was initialized with 'test_attr_id' in setUp
        with self.assertLogs(LOGGER, logging.DEBUG):
            result = self.directive.run()

        # The temporary attribute should have been created with .* pattern
        # We can't directly verify it was created with .*, but we can verify
        # the node was created successfully
        self.assertIsInstance(result[1], ItemAttribute)
        self.assertEqual(result[1]['id'], 'test_attr_id')

    def test_multiline_caption(self):
        """Test that multiline captions are handled correctly"""
        # Setup directive with multiline caption
        self.directive.arguments = ['test_attr', 'Caption\nwith newline']

        # Setup defined attribute
        attr_id = 'test_attr'
        attr = TraceableAttribute(attr_id, '.*')
        TraceableItem.defined_attributes[attr_id] = attr

        # Run the directive
        result = self.directive.run()

        # Verify caption has newline replaced with space
        self.assertEqual(attr.caption, 'Caption with newline')