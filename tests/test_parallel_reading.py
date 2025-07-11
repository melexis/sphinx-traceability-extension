"""Tests for parallel reading functionality"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from pathlib import Path

from mlx.traceability.traceable_collection import TraceableCollection, ParallelSafeTraceableCollection
from mlx.traceability.traceable_item import TraceableItem
from mlx.traceability.traceability import initialize_environment, merge_traceability_info, begin_parallel_read
from mlx.traceability.traceability_exception import TraceabilityException


class TestParallelReading(unittest.TestCase):
    """Test parallel reading functionality"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.doc_dir = self.temp_dir / "docs"
        self.doc_dir.mkdir()

        # Create mock app with necessary config
        self.app = Mock()
        self.app.config = Mock()
        self.app.config.traceability_attributes = {
            'status': '^(draft|approved)$',
            'priority': '^(low|medium|high)$'
        }
        self.app.config.traceability_attribute_to_string = {
            'status': 'Status',
            'priority': 'Priority'
        }
        self.app.config.traceability_attributes_sort = {}
        self.app.config.traceability_relationships = {
            'depends_on': 'impacts_on',
            'implements': 'implemented_by'
        }
        self.app.config.traceability_relationship_to_string = {
            'depends_on': 'Depends on',
            'impacts_on': 'Impacts on',
            'implements': 'Implements',
            'implemented_by': 'Implemented by'
        }
        self.app.config.traceability_checklist = {}
        self.app.config.traceability_notifications = {}
        self.app.config.latex_elements = {}
        self.app.srcdir = str(self.doc_dir)

        # Create mock environment
        self.env = Mock()
        self.env.docname = 'test_doc'
        self.env.srcdir = str(self.doc_dir)
        self.env.all_docs = ['doc1.rst', 'doc2.rst', 'doc3.rst']

        # Create mock builder
        self.builder = Mock()
        self.builder.env = self.env
        self.app.builder = self.builder

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_parallel_safe_collection_initialization(self):
        """Test that ParallelSafeTraceableCollection initializes correctly"""
        collection = ParallelSafeTraceableCollection()

        # Should have a main collection
        self.assertIsInstance(collection._collection, TraceableCollection)
        self.assertFalse(collection._is_worker_process)

        # Should delegate methods correctly
        self.assertEqual(collection.relations, {})
        self.assertEqual(collection.items, {})

    def test_worker_process_detection(self):
        """Test that worker process is correctly detected"""
        # Initialize environment
        initialize_environment(self.app)

        # Test main process (processing all documents)
        begin_parallel_read(self.app, self.env, ['doc1.rst', 'doc2.rst', 'doc3.rst'])
        self.assertFalse(self.env.traceability_collection._is_worker_process)

        # Test worker process (processing subset of documents)
        begin_parallel_read(self.app, self.env, ['doc1.rst'])
        self.assertTrue(self.env.traceability_collection._is_worker_process)

        # Worker should have cleared items
        self.assertEqual(len(self.env.traceability_collection.items), 0)

    def test_parallel_safe_collection_methods(self):
        """Test that ParallelSafeTraceableCollection methods work correctly"""
        collection = ParallelSafeTraceableCollection()

        # Add relation pair
        collection.add_relation_pair('depends_on', 'impacts_on')
        self.assertEqual(collection.get_reverse_relation('depends_on'), 'impacts_on')

        # Add item
        item = TraceableItem('TEST-001')
        item.set_location('test.rst', 1)
        collection.add_item(item)

        self.assertTrue(collection.has_item('TEST-001'))
        retrieved_item = collection.get_item('TEST-001')
        self.assertEqual(retrieved_item.identifier, 'TEST-001')

        # Add relation
        item2 = TraceableItem('TEST-002')
        item2.set_location('test.rst', 2)
        collection.add_item(item2)

        collection.add_relation('TEST-001', 'depends_on', 'TEST-002')
        relations = list(collection.get_item('TEST-001').iter_targets('depends_on'))
        self.assertIn('TEST-002', relations)

    def test_collection_merge(self):
        """Test that collections merge correctly"""
        # Create main collection
        main_collection = ParallelSafeTraceableCollection()
        main_collection.add_relation_pair('depends_on', 'impacts_on')

        # Add item to main collection
        item1 = TraceableItem('MAIN-001')
        item1.set_location('main.rst', 1)
        main_collection.add_item(item1)

        # Create worker collection
        worker_collection = ParallelSafeTraceableCollection()
        worker_collection.add_relation_pair('depends_on', 'impacts_on')

        # Add item to worker collection
        item2 = TraceableItem('WORKER-001')
        item2.set_location('worker.rst', 1)
        worker_collection.add_item(item2)

        # Add relation between items
        worker_collection.add_relation('WORKER-001', 'depends_on', 'MAIN-001')

        # Merge collections
        main_collection.merge_from(worker_collection)

        # Check that both items are present
        self.assertTrue(main_collection.has_item('MAIN-001'))
        self.assertTrue(main_collection.has_item('WORKER-001'))

        # Check that relations are correctly merged
        worker_item = main_collection.get_item('WORKER-001')
        relations = list(worker_item.iter_targets('depends_on'))
        self.assertIn('MAIN-001', relations)

    def test_merge_traceability_info_handler(self):
        """Test the merge_traceability_info event handler"""
        # Create main environment
        main_env = Mock()
        main_env.traceability_collection = ParallelSafeTraceableCollection()
        main_env.traceability_collection.add_relation_pair('depends_on', 'impacts_on')
        main_env.traceability_ref_nodes = {}

        # Create worker environment
        worker_env = Mock()
        worker_env.traceability_collection = ParallelSafeTraceableCollection()
        worker_env.traceability_collection.add_relation_pair('depends_on', 'impacts_on')
        worker_env.traceability_ref_nodes = {'ref1': 'node1'}

        # Add item to worker
        item = TraceableItem('WORKER-001')
        item.set_location('worker.rst', 1)
        worker_env.traceability_collection.add_item(item)

        # Merge
        merge_traceability_info(self.app, main_env, ['worker.rst'], worker_env)

        # Check that item was merged
        self.assertTrue(main_env.traceability_collection.has_item('WORKER-001'))

        # Check that ref_nodes were merged
        self.assertEqual(main_env.traceability_ref_nodes['ref1'], 'node1')

    def test_pickling_support(self):
        """Test that ParallelSafeTraceableCollection can be pickled/unpickled"""
        import pickle

        # Create collection with some data
        collection = ParallelSafeTraceableCollection()
        collection.add_relation_pair('depends_on', 'impacts_on')
        collection.mark_as_worker_process()

        item = TraceableItem('TEST-001')
        item.set_location('test.rst', 1)
        collection.add_item(item)

        # Pickle and unpickle
        pickled_data = pickle.dumps(collection)
        unpickled_collection = pickle.loads(pickled_data)

        # Check that data is preserved
        self.assertTrue(unpickled_collection._is_worker_process)
        self.assertTrue(unpickled_collection.has_item('TEST-001'))
        self.assertEqual(unpickled_collection.get_reverse_relation('depends_on'), 'impacts_on')

    def test_cross_reference_handling(self):
        """Test that cross-references between worker processes are handled correctly"""
        # Create two worker collections
        worker1 = ParallelSafeTraceableCollection()
        worker1.add_relation_pair('depends_on', 'impacts_on')
        worker1.mark_as_worker_process()

        worker2 = ParallelSafeTraceableCollection()
        worker2.add_relation_pair('depends_on', 'impacts_on')
        worker2.mark_as_worker_process()

        # Add items to different workers
        item1 = TraceableItem('ITEM-001')
        item1.set_location('doc1.rst', 1)
        worker1.add_item(item1)

        item2 = TraceableItem('ITEM-002')
        item2.set_location('doc2.rst', 1)
        worker2.add_item(item2)

        # Create cross-reference: item1 depends on item2
        worker1.add_relation('ITEM-001', 'depends_on', 'ITEM-002')

        # Merge into main collection
        main_collection = ParallelSafeTraceableCollection()
        main_collection.add_relation_pair('depends_on', 'impacts_on')

        main_collection.merge_from(worker1)
        main_collection.merge_from(worker2)

        # Check that both items exist
        self.assertTrue(main_collection.has_item('ITEM-001'))
        self.assertTrue(main_collection.has_item('ITEM-002'))

        # Check that forward relation exists
        item1_merged = main_collection.get_item('ITEM-001')
        forward_targets = list(item1_merged.iter_targets('depends_on', explicit=True, implicit=False))
        self.assertIn('ITEM-002', forward_targets)

        # Check that reverse relation exists
        item2_merged = main_collection.get_item('ITEM-002')
        reverse_targets = list(item2_merged.iter_targets('impacts_on', explicit=False, implicit=True))
        self.assertIn('ITEM-001', reverse_targets)

    def test_duplicate_item_handling(self):
        """Test that duplicate items are handled correctly during merge"""
        # Create main collection with an item
        main_collection = ParallelSafeTraceableCollection()
        main_collection.add_relation_pair('depends_on', 'impacts_on')

        item1 = TraceableItem('DUPLICATE-001')
        item1.set_location('main.rst', 1)
        item1.caption = 'Original item'
        main_collection.add_item(item1)

        # Create worker collection with same item ID but different location
        worker_collection = ParallelSafeTraceableCollection()
        worker_collection.add_relation_pair('depends_on', 'impacts_on')

        # This should raise an exception during merge
        item2 = TraceableItem('DUPLICATE-001')
        item2.set_location('worker.rst', 1)
        item2.caption = 'Duplicate item'
        worker_collection.add_item(item2)

        # Merge should handle duplicates gracefully
        # The current implementation merges relationships but doesn't raise exceptions for duplicates
        # Instead, it merges them based on the logic in merge_from
        main_collection.merge_from(worker_collection)

        # Check that the item exists (it should keep the first one)
        self.assertTrue(main_collection.has_item('DUPLICATE-001'))
        merged_item = main_collection.get_item('DUPLICATE-001')
        # The caption should be from the original item
        self.assertEqual(merged_item.caption, 'Original item')

if __name__ == '__main__':
    unittest.main()
