from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch
import logging

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.builders.latex import LaTeXBuilder
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment import BuildEnvironment
from sphinx.errors import NoUri

from mlx.traceability.directives.item_directive import Item as dut, ItemDirective
from mlx.traceability.traceable_collection import TraceableCollection
from mlx.traceability.traceable_item import TraceableItem
from mlx.traceability.traceable_attribute import TraceableAttribute

from parameterized import parameterized

LOGGER = logging.getLogger('sphinx.mlx.traceability.traceability_exception')


def raise_no_uri(*args, **kwargs):
    raise NoUri


class TestItemDirective(TestCase):

    def setUp(self):
        self.app = MagicMock(autospec=Sphinx)
        self.app.srcdir = '/mock/srcdir'  # Mock the source directory
        self.node = dut('')
        self.node['document'] = 'some_doc'
        self.node['id'] = 'some_id'
        self.node['line'] = 1
        self.node['hidetype'] = []
        self.item = TraceableItem(self.node['id'])
        self.item.set_location(self.node['document'], self.node['line'])
        self.item.node = self.node
        self.app.config = Mock()
        self.app.config.traceability_hyperlink_colors = {}
        self.collection = TraceableCollection()
        self.collection.add_item(self.item)

    def init_builder(self, spec=StandaloneHTMLBuilder):
        mock_builder = MagicMock(spec=spec)
        if spec == StandaloneHTMLBuilder:
            mock_builder.link_suffix = '.html'
        else:
            mock_builder.get_relative_uri = Mock(side_effect=raise_no_uri)
        mock_builder.env = BuildEnvironment(self.app)
        self.app.builder = mock_builder
        self.app.builder.env.traceability_collection = self.collection
        self.app.builder.env.traceability_ref_nodes = {}

    def test_make_internal_item_ref_no_caption(self):
        self.init_builder()
        p_node = self.node.make_internal_item_ref(self.app, self.node['id'])
        ref_node = p_node.children[0]
        em_node = ref_node.children[0]
        self.assertEqual(len(em_node.children), 1)
        self.assertEqual(str(em_node), '<emphasis>some_id</emphasis>')
        self.assertEqual(ref_node.tagname, 'reference')
        self.assertEqual(em_node.rawsource, 'some_id')
        self.assertEqual(str(em_node.children[0]), 'some_id')
        cache = self.app.builder.env.traceability_ref_nodes[self.node['id']]
        self.assertEqual(p_node, cache['default'][f'{self.node["document"]}.html'])
        self.assertNotIn('nocaptions', cache)
        self.assertNotIn('onlycaptions', cache)

    def test_make_internal_item_ref_show_caption(self):
        self.init_builder()
        self.item.caption = 'caption text'
        p_node = self.node.make_internal_item_ref(self.app, self.node['id'])
        ref_node = p_node.children[0]
        em_node = ref_node.children[0]

        self.assertEqual(len(em_node.children), 1)
        self.assertEqual(len(em_node.children), 1)
        self.assertEqual(str(em_node), '<emphasis>some_id: caption text</emphasis>')
        self.assertEqual(ref_node.tagname, 'reference')
        self.assertEqual(em_node.rawsource, 'some_id: caption text')
        cache = self.app.builder.env.traceability_ref_nodes[self.node['id']]
        self.assertEqual(p_node, cache['default'][f'{self.node["document"]}.html'])

    def test_make_internal_item_ref_only_caption(self):
        self.init_builder()
        self.item.caption = 'caption text'
        self.node['nocaptions'] = True
        self.node['onlycaptions'] = True
        p_node = self.node.make_internal_item_ref(self.app, self.node['id'])
        ref_node = p_node.children[0]
        em_node = ref_node.children[0]

        self.assertEqual(len(em_node.children), 2)
        self.assertEqual(
            str(em_node),
            '<emphasis classes="has_hidden_caption">caption text<inline classes="popup_caption">some_id</inline>'
            '</emphasis>')
        self.assertEqual(ref_node.tagname, 'reference')
        self.assertEqual(em_node.rawsource, 'caption text')
        cache = self.app.builder.env.traceability_ref_nodes[self.node['id']]
        self.assertEqual(p_node, cache['onlycaptions'][f'{self.node["document"]}.html'])

    def test_make_internal_item_ref_hide_caption_html(self):
        self.init_builder()
        self.item.caption = 'caption text'
        self.node['nocaptions'] = True
        p_node = self.node.make_internal_item_ref(self.app, self.node['id'])
        ref_node = p_node.children[0]
        em_node = ref_node.children[0]

        self.assertEqual(len(em_node.children), 2)
        self.assertEqual(str(em_node),
                         '<emphasis classes="has_hidden_caption">some_id'
                         '<inline classes="popup_caption">caption text</inline>'
                         '</emphasis>')
        self.assertEqual(ref_node.tagname, 'reference')
        self.assertEqual(em_node.rawsource, 'some_id')
        cache = self.app.builder.env.traceability_ref_nodes[self.node['id']]
        self.assertEqual(p_node, cache['nocaptions'][f'{self.node["document"]}.html'])

    def test_make_internal_item_ref_hide_caption_latex(self):
        self.init_builder(spec=LaTeXBuilder)
        self.item.caption = 'caption text'
        self.node['nocaptions'] = True
        p_node = self.node.make_internal_item_ref(self.app, self.node['id'])
        ref_node = p_node.children[0]
        em_node = ref_node.children[0]

        self.assertEqual(len(em_node.children), 1)
        self.assertEqual(str(em_node), '<emphasis>some_id</emphasis>')
        self.assertEqual(ref_node.tagname, 'reference')
        self.assertEqual(em_node.rawsource, 'some_id')
        cache = self.app.builder.env.traceability_ref_nodes[self.node['id']]
        self.assertEqual(p_node, cache['nocaptions'][''])

    @parameterized.expand([
        ("ext_toolname", True),
        ("verifies", False),
        ("is verified by", False),
        ("prefix_ext_", False),
        ("", False),
    ])
    def test_is_relation_external(self, relation_name, expected):
        external = self.node.is_relation_external(relation_name)
        self.assertEqual(external, expected)

    def test_item_node_replacement(self):
        self.collection.add_relation_pair('depends_on', 'impacts_on')
        # leaving out depends_on to test warning
        self.app.config.traceability_relationship_to_string = {'impacts_on': 'Impacts on'}

        target_item = TraceableItem('target_id')
        self.collection.add_item(target_item)
        self.collection.add_relation(self.item.identifier, 'depends_on', target_item.identifier)

        with self.assertLogs(LOGGER, logging.DEBUG) as c_m:
            self.node.parent = nodes.container()
            self.node.parent.append(self.node)
            self.node.perform_replacement(self.app, self.collection)

        warning = "WARNING:sphinx.mlx.traceability.traceability_exception:Traceability: relation depends_on cannot be "\
            "translated to string"
        self.assertEqual(c_m.output, [warning])


class TestItemDirectiveClass(TestCase):
    """Test the ItemDirective class"""

    def setUp(self):
        """Setup test fixtures for directive testing"""
        self._original_defined_attributes = TraceableItem.defined_attributes.copy()
        self.directive = ItemDirective(
            name='item',
            arguments=['TEST_ITEM_ID'],
            options={},
            content=StringList(['Item content line'], 'test.rst'),
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
        self.env = self.directive.state.document.settings.env
        self.env.docname = 'test_document'
        self.env.app = MagicMock(autospec=Sphinx)
        self.env.app.config = Mock()
        self.env.app.config.traceability_collapse_links = False
        self.env.app.config.traceability_item_no_captions = []
        self.env.app.config.traceability_callback_per_item = None

        # Mock get_source_info to return a tuple
        self.directive.get_source_info = Mock(return_value=('test.rst', 10))

        # Initialize collection
        self.collection = TraceableCollection()
        self.env.traceability_collection = self.collection

        # Clear defined attributes
        TraceableItem.defined_attributes = {}

    def tearDown(self):
        TraceableItem.defined_attributes = self._original_defined_attributes

    def test_directive_configuration(self):
        """Test that directive has correct configuration"""
        self.assertEqual(ItemDirective.required_arguments, 1)
        self.assertEqual(ItemDirective.optional_arguments, 1)
        self.assertTrue(ItemDirective.has_content)
        self.assertIn('class', ItemDirective.option_spec)
        self.assertIn('nocaptions', ItemDirective.option_spec)
        self.assertIn('hidetype', ItemDirective.option_spec)

    def test_run_creates_three_nodes(self):
        """Test that run method creates three nodes"""
        result = self.directive.run()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        # First node is target node
        self.assertIsInstance(result[0], nodes.target)
        # Second node is Item node
        self.assertIsInstance(result[1], dut)
        # Third node is content node
        self.assertIsNotNone(result[2])

    def test_run_stores_item_in_collection(self):
        """Test that run method stores item in collection"""
        self.directive.run()

        # Verify item was added to collection
        self.assertTrue(self.collection.has_item('TEST_ITEM_ID'))
        item = self.collection.get_item('TEST_ITEM_ID')
        self.assertEqual(item.identifier, 'TEST_ITEM_ID')

    def test_run_with_caption(self):
        """Test run method with caption argument"""
        self.directive.arguments = ['TEST_ITEM_ID', 'Test Caption']

        self.directive.run()

        item = self.collection.get_item('TEST_ITEM_ID')
        self.assertEqual(item.caption, 'Test Caption')

    def test_run_with_multiline_caption(self):
        """Test that multiline captions have newlines replaced with spaces"""
        self.directive.arguments = ['TEST_ITEM_ID', 'Caption\nwith newline']

        self.directive.run()

        item = self.collection.get_item('TEST_ITEM_ID')
        self.assertEqual(item.caption, 'Caption with newline')

    def test_run_sets_item_location(self):
        """Test that item location is properly set"""
        with patch.object(self.directive, 'get_source_info', return_value=('test.rst', 25)):
            self.directive.run()

        item = self.collection.get_item('TEST_ITEM_ID')
        self.assertEqual(item.docname, 'test_document')
        self.assertEqual(item.lineno, 25)

    def test_run_with_duplicate_item_id_reports_warning(self):
        """Test that duplicate item IDs trigger a warning"""
        # Add item to collection first
        existing_item = TraceableItem('TEST_ITEM_ID')
        self.collection.add_item(existing_item)

        # Try to add duplicate
        with self.assertLogs(LOGGER, logging.DEBUG):
            result = self.directive.run()

        # Should return empty list when duplicate detected
        self.assertEqual(result, [])

    def test_run_with_relationship_option(self):
        """Test run method with relationship options"""
        # Setup relationship
        self.collection.add_relation_pair('depends_on', 'impacts_on')
        self.directive.options['depends_on'] = 'OTHER_ITEM'

        self.directive.run()

        # Verify relationship was added
        item = self.collection.get_item('TEST_ITEM_ID')
        relations = list(item.iter_targets('depends_on'))
        self.assertIn('OTHER_ITEM', relations)

    def test_run_with_multiple_relationships(self):
        """Test run method with multiple related items"""
        # Setup relationship
        self.collection.add_relation_pair('depends_on', 'impacts_on')
        self.directive.options['depends_on'] = 'ITEM_1 ITEM_2 ITEM_3'

        self.directive.run()

        # Verify all relationships were added
        item = self.collection.get_item('TEST_ITEM_ID')
        relations = list(item.iter_targets('depends_on'))
        self.assertIn('ITEM_1', relations)
        self.assertIn('ITEM_2', relations)
        self.assertIn('ITEM_3', relations)

    def test_run_with_attributes(self):
        """Test run method with attribute options"""
        # Setup attribute
        attr = TraceableAttribute('status', '.*')
        TraceableItem.defined_attributes = {'status': attr}
        self.directive.options['status'] = 'completed'

        self.directive.run()

        # Verify attribute was added
        item = self.collection.get_item('TEST_ITEM_ID')
        self.assertEqual(item.get_attribute('status'), 'completed')

    def test_run_with_invalid_attribute_value(self):
        """Test that invalid attribute values trigger a warning"""
        # Setup attribute with strict pattern
        attr = TraceableAttribute('status', '^(open|closed)$')
        TraceableItem.defined_attributes = {'status': attr}
        self.directive.options['status'] = 'invalid_value'

        with self.assertLogs(LOGGER, logging.DEBUG) as log_context:
            self.directive.run()

        # Should have logged a warning
        warning_found = any('status' in msg.lower() for msg in log_context.output)
        self.assertTrue(warning_found)

    def test_run_with_class_option(self):
        """Test run method with class option"""
        self.directive.options['class'] = ['custom-class', 'another-class']

        result = self.directive.run()

        item_node = result[1]
        self.assertIn('custom-class', item_node['classes'])
        self.assertIn('another-class', item_node['classes'])

    def test_run_with_nocaptions_option(self):
        """Test run method with nocaptions flag"""
        self.directive.options['nocaptions'] = None  # Flag options are None when present

        result = self.directive.run()

        # The directive should process nocaptions flag
        # We're just verifying it doesn't crash
        self.assertEqual(len(result), 3)

    def test_run_with_hidetype_option(self):
        """Test run method with hidetype option"""
        self.directive.options['hidetype'] = 'depends_on impacts_on'

        result = self.directive.run()

        item_node = result[1]
        self.assertIn('depends_on', item_node['hidetype'])
        self.assertIn('impacts_on', item_node['hidetype'])

    def test_run_with_collapse_links_config(self):
        """Test that collapse links config is respected"""
        self.env.app.config.traceability_collapse_links = True

        result = self.directive.run()

        item_node = result[1]
        self.assertIn('collapse', item_node['classes'])

    def test_run_without_collapse_links_config(self):
        """Test that collapse class is not added when config is False"""
        self.env.app.config.traceability_collapse_links = False

        result = self.directive.run()

        item_node = result[1]
        self.assertNotIn('collapse', item_node['classes'])

    def test_run_always_adds_collapsible_links_class(self):
        """Test that collapsible_links class is always added"""
        result = self.directive.run()

        item_node = result[1]
        self.assertIn('collapsible_links', item_node['classes'])

    def test_run_sets_item_node_properties(self):
        """Test that item node has correct properties"""
        result = self.directive.run()

        item_node = result[1]
        self.assertEqual(item_node['document'], 'test_document')
        self.assertEqual(item_node['line'], 10)
        self.assertEqual(item_node['id'], 'TEST_ITEM_ID')

    def test_run_stores_content_on_item(self):
        """Test that content is stored on the item"""
        self.directive.run()

        item = self.collection.get_item('TEST_ITEM_ID')
        # Content property converts StringList to string
        self.assertEqual(item.content, 'Item content line')

    def test_run_with_callback(self):
        """Test that callback is called when configured"""
        callback_mock = Mock()
        self.env.app.config.traceability_callback_per_item = callback_mock

        self.directive.run()

        # Verify callback was called
        callback_mock.assert_called_once()

    def test_add_relation_with_invalid_relation_reports_warning(self):
        """Test that adding invalid relations triggers warnings"""
        # Don't add the relation to the collection
        self.directive.options['unknown_relation'] = 'OTHER_ITEM'

        with self.assertLogs(LOGGER, logging.DEBUG) as log_context:
            self.directive.run()

        warning_found = any('unknown_relation' in msg.lower() for msg in log_context.output)
        self.assertTrue(warning_found, "Expected warning about invalid relation not found in logs")
        # Item should still be created
        self.assertTrue(self.collection.has_item('TEST_ITEM_ID'))

    def test_item_node_has_correct_id(self):
        """Test that the item node contains correct id"""
        result = self.directive.run()

        item_node = result[1]
        self.assertEqual(item_node['id'], 'TEST_ITEM_ID')

    def test_target_node_has_item_id(self):
        """Test that target node includes the item ID"""
        result = self.directive.run()

        target_node = result[0]
        self.assertIn('TEST_ITEM_ID', target_node['ids'])

    def test_check_relationships_with_valid_relationships(self):
        """Test check_relationships with valid relationship names"""
        # Setup valid relationships
        self.collection.add_relation_pair('depends_on', 'impacts_on')

        # This should not raise any warnings
        self.directive.check_relationships(['depends_on'], self.env)

    def test_item_clears_state_after_processing(self):
        """Test that item state is cleared after processing"""
        self.directive.run()

        item = self.collection.get_item('TEST_ITEM_ID')
        # State should be cleared - verify by checking that directive is None
        self.assertIsNone(item.directive)
