import os
import shutil
import tempfile
import textwrap
import unittest
import sphinx.cmd.build
import sphinx.cmd.quickstart

class TestSphinx(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.docs_folder = tempfile.mkdtemp()
        cls.rst_file = os.path.join(cls.docs_folder, "index.rst")
        cls.html_file = os.path.join(cls.docs_folder, "_build", "index.html")
        sphinx.cmd.quickstart.generate({
            "path": cls.docs_folder,
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

        with open(f'{cls.docs_folder}/conf.py', 'a') as cfg:
            cfg.write("traceability_render_relationship_per_item = True\n")
            cfg.write("traceability_relationships = {'my_relation': 'my_reverse_relation'}\n")
            cfg.write("traceability_relationship_to_string = {'my_relation': 'My relation', 'my_reverse_relation': 'My reverse relation'}\n")
            cfg.write("traceability_attributes = {}\n")
            cfg.write("traceability_attributes_sort = {}\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.docs_folder)

    def build(self, builder="html"):
        retcode = sphinx.cmd.build.main([
            "-q",
            "-b",
            builder,
            self.docs_folder,
            os.path.join(self.docs_folder, "_build"),
        ])
        self.assertEqual(retcode, 0)

    def test_item_relation(self):
        with open(os.path.join(self.docs_folder, self.rst_file), "w") as f:
            f.write(textwrap.dedent(r"""
            .. item:: ITEM-A Description of item-a

            .. item:: ITEM-B Description of item-b
                :my_relation: ITEM-A
            """))

        self.build(builder="html")
        with open(self.html_file, "r") as f:
            content = f.read()
            assert 'My relation' in content
            assert 'My reverse relation' in content

    def test_item_relation_hide_forward(self):
        with open(os.path.join(self.docs_folder, self.rst_file), "w") as f:
            f.write(textwrap.dedent(r"""
            .. item:: ITEM-A Description of item-a

            .. item:: ITEM-B Description of item-b
                :my_relation: ITEM-A
                :hidetype: my_relation
            """))

        self.build(builder="html")
        with open(self.html_file, "r") as f:
            content = f.read()
            assert 'My relation' not in content
            assert 'My reverse relation' in content

    def test_item_relation_hide_reverse(self):
        with open(os.path.join(self.docs_folder, self.rst_file), "w") as f:
            f.write(textwrap.dedent(r"""
            .. item:: ITEM-A Description of item-a
                :hidetype: my_reverse_relation

            .. item:: ITEM-B Description of item-b
                :my_relation: ITEM-A
            """))

        self.build(builder="html")
        with open(self.html_file, "r") as f:
            content = f.read()
            assert 'My relation' in content
            assert 'My reverse relation' not in content

    def test_item_relation_hide_both(self):
        with open(os.path.join(self.docs_folder, self.rst_file), "w") as f:
            f.write(textwrap.dedent(r"""
            .. item:: ITEM-A Description of item-a
                :hidetype: my_reverse_relation

            .. item:: ITEM-B Description of item-b
                :my_relation: ITEM-A
                :hidetype: my_relation
            """))

        self.build(builder="html")
        with open(self.html_file, "r") as f:
            content = f.read()
            assert 'My relation' not in content
            assert 'My reverse relation' not in content

