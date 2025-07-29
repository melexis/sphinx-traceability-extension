"""Test attribute content handling in parallel builds"""
import unittest
from docutils import nodes

from mlx.traceability.traceable_collection import TraceableCollection
from mlx.traceability.traceable_attribute import TraceableAttribute


class TestAttributeContentParallel(unittest.TestCase):
    """Test attribute content handling in parallel builds."""

    def test_real_definition_replaces_placeholder(self):
        """Test that a real attribute definition replaces a placeholder during merge"""
        main_collection = TraceableCollection()

        # Create placeholder attribute (from configuration - no document location)
        placeholder_attr = TraceableAttribute('status', '.*')
        placeholder_attr.name = 'Status'
        # No docname = placeholder
        main_collection.define_attribute(placeholder_attr)

        # Create worker collection with real definition (from directive)
        worker_collection = TraceableCollection()
        real_attr = TraceableAttribute('status', '.*')
        real_attr.name = 'Status'
        real_attr.caption = 'Status attribute'
        real_attr.docname = 'attributes.rst'  # This makes it a real definition
        real_attr.lineno = 42
        real_attr._content = 'This attribute defines the approval status'

        # Add content_node to make it clearly from a processed directive
        content_node = nodes.container()
        content_node['ids'].append('content-status')
        paragraph = nodes.paragraph()
        paragraph += nodes.Text('This attribute defines the approval status')
        content_node.append(paragraph)
        real_attr.content_node = content_node

        worker_collection.define_attribute(real_attr)

        # Before merge - main has placeholder (no docname)
        main_attr_before = main_collection.defined_attributes['status']
        assert main_attr_before.is_placeholder
        assert not main_attr_before.docname

        # After merge - placeholder should be replaced with real definition
        main_collection.merge_from(worker_collection)
        main_attr_after = main_collection.defined_attributes['status']
        assert not main_attr_after.is_placeholder  # No longer placeholder
        assert main_attr_after.docname == 'attributes.rst'
        assert main_attr_after.lineno == 42
        assert main_attr_after.caption == 'Status attribute'
        assert main_attr_after._content == 'This attribute defines the approval status'
        assert len(main_attr_after.content_node.children) > 0

    def test_placeholder_ignored_when_real_definition_exists(self):
        """Test that placeholders are ignored when a real definition already exists"""
        main_collection = TraceableCollection()

        # Create real definition in main collection (from directive)
        real_attr = TraceableAttribute('priority', '.*')
        real_attr.name = 'Priority'
        real_attr.caption = 'Priority attribute'
        real_attr.docname = 'attributes.rst'  # This makes it a real definition
        real_attr.lineno = 24
        real_attr._content = 'This attribute defines the priority level'
        main_collection.define_attribute(real_attr)

        # Create worker collection with placeholder (from configuration)
        worker_collection = TraceableCollection()
        placeholder_attr = TraceableAttribute('priority', '.*')
        placeholder_attr.name = 'Priority'
        # No docname = placeholder from configuration
        worker_collection.define_attribute(placeholder_attr)

        # Before merge - verify main has real definition
        main_attr_before = main_collection.defined_attributes['priority']
        assert not main_attr_before.is_placeholder
        assert main_attr_before.docname == 'attributes.rst'

        # After merge - real definition should be unchanged (placeholder ignored)
        main_collection.merge_from(worker_collection)
        main_attr_after = main_collection.defined_attributes['priority']
        assert not main_attr_after.is_placeholder
        assert main_attr_after.docname == 'attributes.rst'
        assert main_attr_after.lineno == 24
        assert main_attr_after.caption == 'Priority attribute'
        assert main_attr_after._content == 'This attribute defines the priority level'

    def test_is_placeholder_property(self):
        """Test the is_placeholder property on TraceableAttribute"""
        # Test placeholder attribute (from configuration - no location, directive, or content)
        placeholder = TraceableAttribute('test1', '.*')
        placeholder.name = 'Test1'
        assert placeholder.is_placeholder

        # Test real attribute (from directive - has document location)
        real_with_location = TraceableAttribute('test2', '.*')
        real_with_location.name = 'Test2'
        real_with_location.docname = 'test.rst'  # This makes it a real definition
        real_with_location.lineno = 10
        assert not real_with_location.is_placeholder

        # Test real attribute (has directive reference)
        from unittest.mock import Mock
        real_with_directive = TraceableAttribute('test3', '.*')
        real_with_directive.name = 'Test3'
        real_with_directive.directive = Mock()
        assert not real_with_directive.is_placeholder  # Has directive

        # Test real attribute (has content - processed somehow)
        real_with_content = TraceableAttribute('test4', '.*')
        real_with_content.name = 'Test4'
        real_with_content._content = 'Some content'
        assert not real_with_content.is_placeholder  # Has content

        # Test that combination works
        real_with_all = TraceableAttribute('test5', '.*')
        real_with_all.name = 'Test5'
        real_with_all.docname = 'test.rst'
        real_with_all.directive = Mock()
        real_with_all._content = 'Some content'
        assert not real_with_all.is_placeholder


if __name__ == '__main__':
    unittest.main()
