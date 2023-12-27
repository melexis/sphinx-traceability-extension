from unittest import TestCase

from docutils import nodes

from mlx.traceability import traceable_base_class as dut


class TestTraceableBaseClass(TestCase):
    name = 'silly-Name'
    docname = 'folder/doc.rst'
    identification = 'some-random$name\'with<\"weird@symbols'

    def test_init(self):
        item = dut.TraceableBaseClass(self.identification)
        item.set_location(self.docname)
        item.self_test()
        self.assertEqual(self.identification, item.identifier)
        self.assertEqual(0, item.lineno)
        self.assertEqual(self.identification, item.name)
        self.assertIsNone(item.node)
        self.assertIsNone(item.caption)
        self.assertIsNone(item.content)
        self.assertEqual(str(nodes.block_quote()), str(item.content_node))

    def test_to_dict(self):
        txt = 'some description, with\n newlines and other stuff'
        item = dut.TraceableBaseClass(self.identification)
        item.set_location(self.docname)
        item.content = txt
        data = item.to_dict()
        self.assertEqual("b787a17fc91c9cf37b5bf0665f13c8b1", data['content-hash'])
        item.self_test()
