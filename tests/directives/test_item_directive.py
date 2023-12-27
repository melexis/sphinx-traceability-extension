from unittest import TestCase
from unittest.mock import Mock, MagicMock
import logging

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.builders.latex import LaTeXBuilder
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment import BuildEnvironment
from sphinx.errors import NoUri

from mlx.traceability.directives.item_directive import Item as dut
from mlx.traceability.traceable_collection import TraceableCollection
from mlx.traceability.traceable_item import TraceableItem

from parameterized import parameterized

LOGGER = logging.getLogger()


def raise_no_uri(*args, **kwargs):
    raise NoUri


class TestItemDirective(TestCase):

    def setUp(self):
        self.app = MagicMock(autospec=Sphinx)
        self.node = dut('')
        self.node['document'] = 'some_doc'
        self.node['id'] = 'some_id'
        self.node['line'] = 1
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
        self.assertEqual(str(em_node), '<emphasis>some_id : caption text</emphasis>')
        self.assertEqual(ref_node.tagname, 'reference')
        self.assertEqual(em_node.rawsource, 'some_id : caption text')
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
