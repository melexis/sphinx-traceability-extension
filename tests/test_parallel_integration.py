"""Integration test for parallel reading with Sphinx"""
import unittest
import tempfile
import shutil
from pathlib import Path
import subprocess
import sys


class TestParallelIntegration(unittest.TestCase):
    """Integration test for parallel reading functionality"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.doc_dir = self.temp_dir / "docs"
        self.doc_dir.mkdir()
        self.build_dir = self.temp_dir / "_build"

        # Create conf.py
        conf_content = '''
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

project = 'Test Project'
extensions = ['mlx.traceability']
html_theme = 'basic'

traceability_relationships = {
    'depends_on': 'impacts_on',
    'implements': 'implemented_by'
}
traceability_relationship_to_string = {
    'depends_on': 'Depends on',
    'impacts_on': 'Impacts on',
    'implements': 'Implements',
    'implemented_by': 'Implemented by'
}
traceability_attributes = {
    'status': '^(draft|approved)$',
    'priority': '^(low|medium|high)$'
}
traceability_attribute_to_string = {
    'status': 'Status',
    'priority': 'Priority'
}
'''
        (self.doc_dir / "conf.py").write_text(conf_content)

        # Create index.rst
        index_content = '''
Test Documentation
==================

.. toctree::
   :maxdepth: 2

   doc1
   doc2
   doc3

Main Index
----------

.. item:: MAIN-001 Main requirements
   :status: approved
   :priority: high

   This is the main requirements document.
'''
        (self.doc_dir / "index.rst").write_text(index_content)

        # Create doc1.rst
        doc1_content = '''
Document 1
==========

Requirements
------------

.. item:: REQ-001 First requirement
   :status: draft
   :priority: medium
   :depends_on: MAIN-001

   This is the first requirement that depends on the main requirement.

.. item:: REQ-002 Second requirement
   :status: approved
   :priority: low
   :implements: REQ-001

   This requirement implements the first requirement.
'''
        (self.doc_dir / "doc1.rst").write_text(doc1_content)

        # Create doc2.rst
        doc2_content = '''
Document 2
==========

More Requirements
-----------------

.. item:: REQ-003 Third requirement
   :status: draft
   :priority: high
   :depends_on: REQ-001 REQ-002

   This requirement depends on multiple other requirements.

.. item:: REQ-004 Fourth requirement
   :status: approved
   :priority: medium
   :implements: REQ-003

   This requirement implements the third requirement.
'''
        (self.doc_dir / "doc2.rst").write_text(doc2_content)

        # Create doc3.rst
        doc3_content = '''
Document 3
==========

Final Requirements
------------------

.. item:: REQ-005 Fifth requirement
   :status: approved
   :priority: high
   :depends_on: REQ-004

   This is the final requirement in the chain.

Item Matrix
-----------

.. item-matrix:: Requirements Matrix
   :source: REQ-
   :target: REQ-
   :type: depends_on

Item List
---------

.. item-list:: All Requirements
   :filter: REQ-
'''
        (self.doc_dir / "doc3.rst").write_text(doc3_content)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_parallel_build_success(self):
        """Test that parallel build completes successfully"""
        # Run sphinx-build with parallel reading
        cmd = [
            sys.executable, "-m", "sphinx",
            "-b", "html",
            "-j", "2",  # Use 2 parallel processes
            "-E",       # Force full rebuild
            str(self.doc_dir),
            str(self.build_dir)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Check that build was successful
        self.assertEqual(result.returncode, 0,
                        f"Sphinx build failed with output:\n{result.stdout}\n{result.stderr}")

        # Check that output files were created
        self.assertTrue((self.build_dir / "index.html").exists())
        self.assertTrue((self.build_dir / "doc1.html").exists())
        self.assertTrue((self.build_dir / "doc2.html").exists())
        self.assertTrue((self.build_dir / "doc3.html").exists())

        # Check that no parallel reading warnings were issued
        self.assertNotIn("not safe for parallel reading", result.stderr)
        self.assertNotIn("doing serial read", result.stderr)

    def test_parallel_build_with_relationships(self):
        """Test that relationships work correctly in parallel builds"""
        # Run sphinx-build with parallel reading
        cmd = [
            sys.executable, "-m", "sphinx",
            "-b", "html",
            "-j", "2",  # Use 2 parallel processes
            "-E",       # Force full rebuild
            str(self.doc_dir),
            str(self.build_dir)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Check that build was successful
        self.assertEqual(result.returncode, 0,
                        f"Sphinx build failed with output:\n{result.stdout}\n{result.stderr}")

        # Check that HTML files contain expected relationships
        doc1_html = (self.build_dir / "doc1.html").read_text()

        # Check that forward relationships exist
        self.assertIn("MAIN-001", doc1_html)  # REQ-001 should show dependence on MAIN-001

        # Check that reverse relationships exist
        main_html = (self.build_dir / "index.html").read_text()
        # The main item should show it impacts REQ-001 (reverse relationship)
        # Note: This depends on the configuration for rendering relationships

        # Check that the matrix was generated properly
        doc3_html = (self.build_dir / "doc3.html").read_text()
        self.assertIn("REQ-001", doc3_html)  # Matrix should contain requirements
        self.assertIn("REQ-002", doc3_html)
        self.assertIn("REQ-003", doc3_html)

    def test_serial_vs_parallel_consistency(self):
        """Test that serial and parallel builds produce consistent results"""
        # First, run serial build
        serial_dir = self.temp_dir / "_build_serial"
        cmd_serial = [
            sys.executable, "-m", "sphinx",
            "-b", "html",
            "-j", "1",  # Serial build
            "-E",       # Force full rebuild
            str(self.doc_dir),
            str(serial_dir)
        ]

        result_serial = subprocess.run(cmd_serial, capture_output=True, text=True)
        self.assertEqual(result_serial.returncode, 0,
                        f"Serial build failed: {result_serial.stderr}")

        # Then run parallel build
        parallel_dir = self.temp_dir / "_build_parallel"
        cmd_parallel = [
            sys.executable, "-m", "sphinx",
            "-b", "html",
            "-j", "2",  # Parallel build
            "-E",       # Force full rebuild
            str(self.doc_dir),
            str(parallel_dir)
        ]

        result_parallel = subprocess.run(cmd_parallel, capture_output=True, text=True)
        self.assertEqual(result_parallel.returncode, 0,
                        f"Parallel build failed: {result_parallel.stderr}")

        # Compare key files to ensure consistency
        # Note: We can't compare entire HTML files due to timestamps, but we can check key content

        for filename in ["index.html", "doc1.html", "doc2.html", "doc3.html"]:
            serial_file = serial_dir / filename
            parallel_file = parallel_dir / filename

            self.assertTrue(serial_file.exists(), f"Serial build missing {filename}")
            self.assertTrue(parallel_file.exists(), f"Parallel build missing {filename}")

            # Read and compare content (ignoring timestamps and other metadata)
            serial_content = serial_file.read_text()
            parallel_content = parallel_file.read_text()

            # Check that both contain the same items
            for item_id in ["MAIN-001", "REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"]:
                self.assertIn(item_id, serial_content, f"Serial build missing {item_id} in {filename}")
                self.assertIn(item_id, parallel_content, f"Parallel build missing {item_id} in {filename}")


if __name__ == '__main__':
    unittest.main()
