from unittest import TestCase
from unittest.mock import Mock, MagicMock

from sphinx.application import Sphinx
from sphinx.builders.latex import LaTeXBuilder
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment import BuildEnvironment
from sphinx.errors import NoUri

from mlx.directives.item_directive import Item as dut
from mlx.traceable_collection import TraceableCollection
from mlx.traceable_item import TraceableItem

from parameterized import parameterized


def raise_no_uri(*args, **kwargs):
    raise NoUri


class TestItemDirective(TestCase):

    def setUp(self):
        self.app = Mock(spec=Sphinx)
        self.node = dut('')
        self.node['document'] = 'some_doc'
        self.node['id'] = 'some_id'
        self.node['line'] = 1
        self.item = TraceableItem(self.node['id'])
        self.item.set_location(self.node['document'], self.node['line'])
        self.item.node = self.node
        self.app.config = Mock()
        self.app.config.traceability_hyperlink_colors = {}

    def test_make_internal_item_ref_no_caption(self):
        mock_builder = MagicMock(spec=StandaloneHTMLBuilder)
        mock_builder.link_suffix = '.html'
        mock_builder.env = BuildEnvironment()
        self.app.builder = mock_builder
        self.app.builder.env.traceability_collection = TraceableCollection()
        self.app.builder.env.traceability_ref_nodes = {}
        self.app.builder.env.traceability_collection.add_item(self.item)
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
        mock_builder = MagicMock(spec=StandaloneHTMLBuilder)
        mock_builder.link_suffix = '.html'
        mock_builder.env = BuildEnvironment()
        self.app.builder = mock_builder
        self.app.builder.env.traceability_collection = TraceableCollection()
        self.app.builder.env.traceability_ref_nodes = {}
        self.app.builder.env.traceability_collection.add_item(self.item)
        self.item.caption = 'caption text'
        p_node = self.node.make_internal_item_ref(self.app, self.node['id'])
        ref_node = p_node.children[0]
        em_node = ref_node.children[0]

        self.assertEqual(len(em_node.children), 1)
        self.assertEqual(len(em_node.children), 1)
        self.assertEqual(str(em_node), '<emphasis>some_id : caption text</emphasis>')
        self.assertEqual(ref_node.tagname, 'reference')
        self.assertEqual(em_node.rawsource, 'some_id : caption text')
        cache = self.app.builder.env.traceability_ref_nodes[self.node['id']]
        self.assertEqual(p_node, cache['default'][f'{self.node["document"]}.html'])

    def test_make_internal_item_ref_only_caption(self):
        mock_builder = MagicMock(spec=StandaloneHTMLBuilder)
        mock_builder.link_suffix = '.html'
        mock_builder.env = BuildEnvironment()
        self.app.builder = mock_builder
        self.app.builder.env.traceability_collection = TraceableCollection()
        self.app.builder.env.traceability_ref_nodes = {}
        self.app.builder.env.traceability_collection.add_item(self.item)
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
        mock_builder = MagicMock(spec=StandaloneHTMLBuilder)
        mock_builder.link_suffix = '.html'
        mock_builder.env = BuildEnvironment()
        self.app.builder = mock_builder
        self.app.builder.env.traceability_collection = TraceableCollection()
        self.app.builder.env.traceability_ref_nodes = {}
        self.app.builder.env.traceability_collection.add_item(self.item)
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
        mock_builder = MagicMock(spec=LaTeXBuilder)
        mock_builder.get_relative_uri = Mock(side_effect=raise_no_uri)
        mock_builder.env = BuildEnvironment()
        self.app.builder = mock_builder
        self.app.builder.env.traceability_collection = TraceableCollection()
        self.app.builder.env.traceability_ref_nodes = {}
        self.app.builder.env.traceability_collection.add_item(self.item)
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
