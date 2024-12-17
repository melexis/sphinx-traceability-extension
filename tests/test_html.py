import shutil
import tempfile
import textwrap
import unittest
import sphinx.cmd.build
import sphinx.cmd.quickstart
from pathlib import Path


class TestSphinx(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc_dir = Path(tempfile.mkdtemp())
        cls.build_dir = cls.doc_dir / "_build"
        cls.index_rst_path = cls.doc_dir / "index.rst"
        cls.html_file = cls.build_dir / "index.html"
        sphinx.cmd.quickstart.generate({
            "path": cls.doc_dir,
            "sep": False,
            "project": "testdoc",
            "author": "mlx.traceability contributors",
            "version": "a",
            "release": "a",
            "language": "en",
            "dot": "_",
            "suffix": ".rst",
            "master": "index",
            "makefile": True,
            "batchfile": False,
            "extensions": ["mlx.traceability"],
        }, silent=True)

        cfg = r"""
            traceability_render_relationship_per_item = True
            traceability_relationships = {'my_relation': 'my_reverse_relation'}
            traceability_relationship_to_string = {'my_relation': 'My relation',
                                                   'my_reverse_relation': 'My reverse relation'}
            traceability_attributes = {}
            traceability_attributes_sort = {}
            """

        with open(cls.doc_dir / 'conf.py', 'a') as f:
            f.write(textwrap.dedent(cfg))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.doc_dir)

    def build(self, builder="html"):
        retcode = sphinx.cmd.build.main([
            "-q",
            "-b",
            builder,
            str(self.doc_dir),
            str(self.build_dir),
        ])
        self.assertEqual(retcode, 0)

    def make_doc_with_rst(self, rst_content, **build_options):
        with open(self.index_rst_path, "w") as f:
            f.write(textwrap.dedent(rst_content))
        self.build(**build_options)
        with open(self.html_file, "r") as f:
            return f.read()

    def test_item_relation(self):
        rst_content = r"""
        .. item:: ITEM-A Description of item-a

        .. item:: ITEM-B Description of item-b
            :my_relation: ITEM-A
        """
        content = self.make_doc_with_rst(rst_content)
        assert 'My relation' in content
        assert 'My reverse relation' in content

    def test_item_relation_hide_forward(self):
        rst_content = r"""
        .. item:: ITEM-A Description of item-a

        .. item:: ITEM-B Description of item-b
            :my_relation: ITEM-A
            :hidetype: my_relation
        """
        content = self.make_doc_with_rst(rst_content)
        assert 'My relation' not in content
        assert 'My reverse relation' in content

    def test_item_relation_hide_reverse(self):
        rst_content = r"""
        .. item:: ITEM-A Description of item-a
            :hidetype: my_reverse_relation

        .. item:: ITEM-B Description of item-b
            :my_relation: ITEM-A
        """
        content = self.make_doc_with_rst(rst_content)
        assert 'My relation' in content
        assert 'My reverse relation' not in content

    def test_item_relation_hide_both(self):
        rst_content = r"""
        .. item:: ITEM-A Description of item-a
            :hidetype: my_reverse_relation

        .. item:: ITEM-B Description of item-b
            :my_relation: ITEM-A
            :hidetype: my_relation
        """
        content = self.make_doc_with_rst(rst_content)
        assert 'My relation' not in content
        assert 'My reverse relation' not in content
