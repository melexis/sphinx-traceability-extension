"""
Comprehensive tests for parallel reading functionality in mlx.traceability extension.

Tests verify that the plugin works correctly when Sphinx uses parallel reading
to process multiple documents simultaneously.
"""

import pickle
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import pytest

from mlx.traceability.traceable_collection import TraceableCollection, ParallelSafeTraceableCollection
from mlx.traceability.traceable_item import TraceableItem
from mlx.traceability.traceability import initialize_environment, merge_traceability_info, begin_parallel_read
from mlx.traceability.traceability_exception import TraceabilityException


class TestParallelSafeTraceableCollection:
    """Test the ParallelSafeTraceableCollection class."""

    def test_initialization(self):
        """Test that ParallelSafeTraceableCollection initializes properly."""
        collection = ParallelSafeTraceableCollection()
        assert hasattr(collection, '_collection')
        assert isinstance(collection._collection, TraceableCollection)
        assert collection._is_worker_process is False

    def test_delegation_to_underlying_collection(self):
        """Test that method calls are properly delegated to the underlying collection."""
        collection = ParallelSafeTraceableCollection()

        # Set up main collection with relations
        main_collection = TraceableCollection()
        main_collection.add_relation_pair('implements', 'implemented_by')
        collection.set_main_collection(main_collection)

        # Test delegation works
        assert collection.get_reverse_relation('implements') == 'implemented_by'
        assert collection.get_reverse_relation('implemented_by') == 'implements'

        # Test adding items
        item = TraceableItem('TEST_ITEM')
        item.docname = 'test.rst'
        collection.add_item(item)

        assert collection.has_item('TEST_ITEM')
        assert collection.get_item('TEST_ITEM') is item

    def test_worker_process_mode(self):
        """Test the worker process mode functionality."""
        collection = ParallelSafeTraceableCollection()

        # Set up main collection with an item
        main_collection = TraceableCollection()
        main_collection.add_relation_pair('implements', 'implemented_by')

        main_item = TraceableItem('MAIN_ITEM')
        main_item.docname = 'main.rst'
        main_collection.add_item(main_item)

        collection.set_main_collection(main_collection)

        # Initially should have the main item
        assert collection.has_item('MAIN_ITEM')

        # Mark as worker process
        collection.mark_as_worker_process()

        # Should still have relations but not the main items
        assert collection.get_reverse_relation('implements') == 'implemented_by'
        assert not collection.has_item('MAIN_ITEM')
        assert collection._is_worker_process is True

    def test_pickling_support(self):
        """Test that the collection can be pickled and unpickled."""
        collection = ParallelSafeTraceableCollection()

        # Set up with some data
        main_collection = TraceableCollection()
        main_collection.add_relation_pair('implements', 'implemented_by')
        collection.set_main_collection(main_collection)

        item = TraceableItem('PICKLE_TEST')
        item.docname = 'test.rst'
        collection.add_item(item)

        # Pickle and unpickle
        pickled = pickle.dumps(collection)
        unpickled = pickle.loads(pickled)

        # Verify data is preserved
        assert unpickled.has_item('PICKLE_TEST')
        assert unpickled.get_reverse_relation('implements') == 'implemented_by'
        assert unpickled._is_worker_process is False


class TestWorkerProcessDetection:
    """Test worker process detection logic."""

    def setup_method(self):
        """Set up test environment for each test."""
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

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_worker_process_detection(self):
        """Test that worker process is correctly detected."""
        # Initialize environment
        initialize_environment(self.app)

        # Test main process (processing all documents)
        begin_parallel_read(self.app, self.env, ['doc1.rst', 'doc2.rst', 'doc3.rst'])
        assert not self.env.traceability_collection._is_worker_process

        # Test worker process (processing subset of documents)
        begin_parallel_read(self.app, self.env, ['doc1.rst'])
        assert self.env.traceability_collection._is_worker_process

        # Worker should have cleared items
        assert len(self.env.traceability_collection.items) == 0


class TestTraceableCollectionMerging:
    """Test the merge functionality for combining collections."""

    def test_basic_item_merging(self):
        """Test merging items from different collections."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Add items to different collections
        item1 = TraceableItem('ITEM_1')
        item1.docname = 'doc1.rst'
        collection1.add_item(item1)

        item2 = TraceableItem('ITEM_2')
        item2.docname = 'doc2.rst'
        collection2.add_item(item2)

        # Merge collection2 into collection1
        collection1.merge_from(collection2)

        # Both items should be present
        assert collection1.has_item('ITEM_1')
        assert collection1.has_item('ITEM_2')
        assert len(collection1.items) == 2

    def test_placeholder_merging(self):
        """Test merging with placeholder items."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Add placeholder in collection1
        placeholder = TraceableItem('SHARED_ITEM', placeholder=True)
        collection1.add_item(placeholder)

        # Add real item in collection2
        real_item = TraceableItem('SHARED_ITEM')
        real_item.docname = 'doc.rst'
        real_item.content = 'Real content'
        collection2.add_item(real_item)

        # Merge should replace placeholder with real item
        collection1.merge_from(collection2)

        merged_item = collection1.get_item('SHARED_ITEM')
        assert not merged_item.is_placeholder
        assert merged_item.docname == 'doc.rst'
        assert merged_item.content == 'Real content'

    def test_same_item_merging(self):
        """Test merging the same item from the same document location."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Add same item to both collections (same document and line)
        item1 = TraceableItem('SAME_ITEM')
        item1.docname = 'doc.rst'
        item1.lineno = 10
        item1.content = 'Content'
        collection1.add_item(item1)

        item2 = TraceableItem('SAME_ITEM')
        item2.docname = 'doc.rst'
        item2.lineno = 10
        item2.content = 'Content'
        collection2.add_item(item2)

        # Merging should succeed (same item from same location)
        collection1.merge_from(collection2)

        # Should still have the item
        assert collection1.has_item('SAME_ITEM')
        assert len(collection1.items) == 1

    def test_different_document_merging(self):
        """Test merging items with same ID from different documents."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Add items with same ID from different documents
        item1 = TraceableItem('CROSS_REF_ITEM')
        item1.docname = 'doc1.rst'
        item1.content = 'Content 1'
        collection1.add_item(item1)

        item2 = TraceableItem('CROSS_REF_ITEM')
        item2.docname = 'doc2.rst'
        item2.content = 'Content 2'
        collection2.add_item(item2)

        # Merging should succeed (cross-references are allowed)
        collection1.merge_from(collection2)

        # Should keep the first item's content
        merged_item = collection1.get_item('CROSS_REF_ITEM')
        assert merged_item.docname == 'doc1.rst'
        assert merged_item.content == 'Content 1'

    def test_duplicate_item_error(self):
        """Test that merging duplicate real items from same document raises error."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Add real items with same ID from same document but different lines
        item1 = TraceableItem('DUPLICATE_ITEM')
        item1.docname = 'doc.rst'
        item1.lineno = 10
        collection1.add_item(item1)

        item2 = TraceableItem('DUPLICATE_ITEM')
        item2.docname = 'doc.rst'
        item2.lineno = 20
        collection2.add_item(item2)

        # Merging should raise an exception
        with pytest.raises(TraceabilityException) as exc_info:
            collection1.merge_from(collection2)

        assert 'Duplicate item' in str(exc_info.value)
        assert 'DUPLICATE_ITEM' in str(exc_info.value)

    def test_relation_merging(self):
        """Test merging relation configurations."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Add relations to both collections
        collection1.add_relation_pair('implements', 'implemented_by')
        collection2.add_relation_pair('depends_on', 'impacts_on')

        # Merge should combine relations
        collection1.merge_from(collection2)

        expected_relations = {
            'implements': 'implemented_by',
            'implemented_by': 'implements',
            'depends_on': 'impacts_on',
            'impacts_on': 'depends_on'
        }
        assert collection1.relations == expected_relations

    def test_conflicting_relation_error(self):
        """Test that conflicting relations raise an error."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Add conflicting relations
        collection1.add_relation_pair('test_rel', 'reverse1')
        collection2.add_relation_pair('test_rel', 'reverse2')

        # Should raise an exception
        with pytest.raises(TraceabilityException) as exc_info:
            collection1.merge_from(collection2)

        assert 'Conflicting reverse relation' in str(exc_info.value)

    def test_reverse_relationship_restoration(self):
        """Test that reverse relationships are restored after merging."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Set up relations
        collection1.add_relation_pair('implements', 'implemented_by')
        collection2.add_relation_pair('implements', 'implemented_by')

        # Add items to different collections
        item1 = TraceableItem('IMPL_ITEM')
        item1.docname = 'impl.rst'
        collection1.add_item(item1)

        item2 = TraceableItem('SPEC_ITEM')
        item2.docname = 'spec.rst'
        collection2.add_item(item2)

        # Add relationship in collection1 to item in collection2
        collection1.add_relation('IMPL_ITEM', 'implements', 'SPEC_ITEM')

        # Merge collections
        collection1.merge_from(collection2)

        # Verify both forward and reverse relationships exist
        impl_item = collection1.get_item('IMPL_ITEM')
        spec_item = collection1.get_item('SPEC_ITEM')

        assert 'SPEC_ITEM' in impl_item.iter_targets('implements')
        assert 'IMPL_ITEM' in spec_item.iter_targets('implemented_by')


class TestMergeTraceabilityInfoHandler:
    """Test the merge_traceability_info event handler."""

    def test_merge_traceability_info_handler(self):
        """Test the merge_traceability_info event handler."""
        # Create mock app
        app = Mock()

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
        merge_traceability_info(app, main_env, ['worker.rst'], worker_env)

        # Check that item was merged
        assert main_env.traceability_collection.has_item('WORKER-001')

        # Check that ref_nodes were merged
        assert main_env.traceability_ref_nodes['ref1'] == 'node1'


class TestDocumentPurging:
    """Test document purging functionality."""

    def test_remove_items_from_document(self):
        """Test removing all items from a specific document."""
        collection = TraceableCollection()

        # Add items from different documents
        item1 = TraceableItem('ITEM_1')
        item1.docname = 'doc1.rst'
        collection.add_item(item1)

        item2 = TraceableItem('ITEM_2')
        item2.docname = 'doc2.rst'
        collection.add_item(item2)

        item3 = TraceableItem('ITEM_3')
        item3.docname = 'doc1.rst'
        collection.add_item(item3)

        # Remove items from doc1.rst
        collection.remove_items_from_document('doc1.rst')

        # Only item from doc2.rst should remain
        assert not collection.has_item('ITEM_1')
        assert collection.has_item('ITEM_2')
        assert not collection.has_item('ITEM_3')
        assert len(collection.items) == 1

    def test_remove_relationships_to_purged_items(self):
        """Test that relationships to purged items are removed."""
        collection = TraceableCollection()
        collection.add_relation_pair('depends_on', 'impacts_on')

        # Create items with relationships
        item1 = TraceableItem('ITEM_1')
        item1.docname = 'doc1.rst'
        collection.add_item(item1)

        item2 = TraceableItem('ITEM_2')
        item2.docname = 'doc2.rst'
        collection.add_item(item2)

        # Add relationship from item2 to item1
        collection.add_relation('ITEM_2', 'depends_on', 'ITEM_1')

        # Verify relationship exists
        assert 'ITEM_1' in item2.iter_targets('depends_on')
        assert 'ITEM_2' in item1.iter_targets('impacts_on')

        # Remove doc1.rst (containing ITEM_1)
        collection.remove_items_from_document('doc1.rst')

        # ITEM_2 should no longer have relationship to ITEM_1
        remaining_item = collection.get_item('ITEM_2')
        assert list(remaining_item.iter_targets('depends_on')) == []

    def test_get_document_items(self):
        """Test getting items from a specific document."""
        collection = TraceableCollection()

        # Add items from different documents
        item1 = TraceableItem('ITEM_1')
        item1.docname = 'doc1.rst'
        collection.add_item(item1)

        item2 = TraceableItem('ITEM_2')
        item2.docname = 'doc2.rst'
        collection.add_item(item2)

        item3 = TraceableItem('ITEM_3')
        item3.docname = 'doc1.rst'
        collection.add_item(item3)

        # Get items from doc1.rst
        doc1_items = collection.get_document_items('doc1.rst')

        assert len(doc1_items) == 2
        assert 'ITEM_1' in doc1_items
        assert 'ITEM_3' in doc1_items
        assert 'ITEM_2' not in doc1_items


class TestParallelReadingIntegration:
    """Integration tests for full parallel reading workflow."""

    def test_worker_process_simulation(self):
        """Test simulating worker process behavior."""
        # Create main collection
        main_collection = ParallelSafeTraceableCollection()
        base_collection = TraceableCollection()
        base_collection.add_relation_pair('implements', 'implemented_by')
        main_collection.set_main_collection(base_collection)

        # Simulate worker process
        worker_collection = ParallelSafeTraceableCollection()
        worker_collection.set_main_collection(base_collection)
        worker_collection.mark_as_worker_process()

        # Worker should have relations but no items
        assert worker_collection.get_reverse_relation('implements') == 'implemented_by'
        assert len(worker_collection.items) == 0

        # Worker processes items
        item1 = TraceableItem('WORKER_ITEM_1')
        item1.docname = 'worker_doc.rst'
        worker_collection.add_item(item1)

        item2 = TraceableItem('WORKER_ITEM_2')
        item2.docname = 'worker_doc.rst'
        worker_collection.add_item(item2)

        # Add relationship
        worker_collection.add_relation('WORKER_ITEM_1', 'implements', 'WORKER_ITEM_2')

        # Verify worker has its items
        assert worker_collection.has_item('WORKER_ITEM_1')
        assert worker_collection.has_item('WORKER_ITEM_2')
        assert 'WORKER_ITEM_2' in worker_collection.get_item('WORKER_ITEM_1').iter_targets('implements')

    def test_merge_multiple_workers(self):
        """Test merging collections from multiple workers."""
        # Create main collection
        main_collection = TraceableCollection()
        main_collection.add_relation_pair('implements', 'implemented_by')
        main_collection.add_relation_pair('depends_on', 'impacts_on')

        # Create worker collections
        worker_collections = []
        for worker_id in range(3):
            worker_collection = TraceableCollection()
            worker_collection.relations = main_collection.relations.copy()

            # Each worker processes different items
            for item_id in range(2):
                item = TraceableItem(f'WORKER{worker_id}_ITEM{item_id}')
                item.docname = f'worker{worker_id}_doc{item_id}.rst'
                worker_collection.add_item(item)

            # Add relationships within worker
            worker_collection.add_relation(f'WORKER{worker_id}_ITEM0', 'implements', f'WORKER{worker_id}_ITEM1')

            # Add cross-worker relationship (will be resolved during merge)
            if worker_id > 0:
                worker_collection.add_relation(f'WORKER{worker_id}_ITEM0', 'depends_on', 'WORKER0_ITEM0')

            worker_collections.append(worker_collection)

        # Merge all workers into main collection
        for worker_collection in worker_collections:
            main_collection.merge_from(worker_collection)

        # Verify all items are present
        for worker_id in range(3):
            for item_id in range(2):
                assert main_collection.has_item(f'WORKER{worker_id}_ITEM{item_id}')

        # Verify relationships are maintained
        for worker_id in range(3):
            item0 = main_collection.get_item(f'WORKER{worker_id}_ITEM0')
            item1 = main_collection.get_item(f'WORKER{worker_id}_ITEM1')

            # Within-worker relationships
            assert f'WORKER{worker_id}_ITEM1' in item0.iter_targets('implements')
            assert f'WORKER{worker_id}_ITEM0' in item1.iter_targets('implemented_by')

            # Cross-worker relationships
            if worker_id > 0:
                assert 'WORKER0_ITEM0' in item0.iter_targets('depends_on')
                worker0_item0 = main_collection.get_item('WORKER0_ITEM0')
                assert f'WORKER{worker_id}_ITEM0' in worker0_item0.iter_targets('impacts_on')

        # Total items should be 3 workers * 2 items = 6
        assert len(main_collection.items) == 6

    def test_intermediate_nodes_merging(self):
        """Test that intermediate nodes are properly merged."""
        collection1 = TraceableCollection()
        collection2 = TraceableCollection()

        # Add intermediate nodes to both collections
        node1 = {'type': 'checkbox_result', 'document': 'doc1.rst', 'data': 'test1'}
        node2 = {'type': 'checkbox_result', 'document': 'doc2.rst', 'data': 'test2'}

        collection1.add_intermediate_node(node1)
        collection2.add_intermediate_node(node2)

        # Merge collections
        collection1.merge_from(collection2)

        # Both intermediate nodes should be present
        assert len(collection1._intermediate_nodes) == 2
        assert node1 in collection1._intermediate_nodes
        assert node2 in collection1._intermediate_nodes


if __name__ == '__main__':
    pytest.main([__file__])
