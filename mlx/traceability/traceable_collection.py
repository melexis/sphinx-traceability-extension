'''
Storage classes for collection of traceable items
'''
import json
import re
from operator import attrgetter
from pathlib import Path
from typing import Dict

from natsort import natsorted

from .traceability_exception import MultipleTraceabilityExceptions, TraceabilityException
from .traceable_item import TraceableItem


class TraceableCollection:
    '''
    Storage for a collection of TraceableItems
    '''

    NO_RELATION_STR = ''

    def __init__(self):
        '''Initializer for container of traceable items'''
        self.relations = {}
        self.items = {}
        self.relations_sorted = {}
        self._intermediate_nodes = []
        self.attributes_sort = {}
        # Move defined_attributes from TraceableItem class to collection instance
        # This ensures proper isolation during parallel processing
        self.defined_attributes = {}

    def add_relation_pair(self, forward, reverse=NO_RELATION_STR):
        '''
        Add a relation pair to the collection

        Args:
            forward (str): Keyword for the forward relation
            reverse (str): Keyword for the reverse relation, or NO_RELATION_STR for external relations
        '''
        # Link forward to reverse relation
        self.relations[forward] = reverse
        # Link reverse to forward relation
        if reverse != self.NO_RELATION_STR:
            self.relations[reverse] = forward

    def get_reverse_relation(self, forward):
        '''
        Get the matching reverse relation

        Args:
            forward (str): Keyword for the forward relation
        Returns:
            str: Keyword for the matching reverse relation, or None
        '''
        if forward in self.relations:
            return self.relations[forward]
        return None

    def iter_relations(self):
        '''
        Iterate over available relations: naturally sorted

        Returns:
            Naturally sorted list over available relations in the collection
        '''
        if len(self.relations) != len(self.relations_sorted):
            self.relations_sorted = natsorted(self.relations)
        return self.relations_sorted

    def add_item(self, item):
        '''
        Add a TraceableItem to the list

        Args:
            item (TraceableItem): Traceable item to add
        '''
        # Set collection reference for improved API
        item._collection = self

        # If the item already exists ...
        if item.identifier in self.items:
            olditem = self.items[item.identifier]
            # ... and it's not a placeholder, log an error
            if not olditem.is_placeholder:
                raise TraceabilityException('duplicating {itemid}'.format(itemid=item.identifier), item.docname)
            # ... otherwise, update the item with new content
            item.update(olditem)
        # add it
        self.items[item.identifier] = item

    def get_item(self, itemid):
        '''
        Get a TraceableItem from the list

        Args:
            itemid (str): Identification of traceable item to get
        Returns:
            TraceableItem/None: Object for traceable item; None if the item was not found
        '''
        return self.items.get(itemid)

    def iter_items(self):
        '''
        Iterate over items: naturally sorted identification

        Returns:
            Sorted iterator over identification of the items in the collection
        '''
        return natsorted(self.items)

    def has_item(self, itemid):
        '''
        Verify if a item with given id is in the collection

        Args:
            itemid (str): Identification of item to look for
        Returns:
            bool: True if the given itemid is in the collection, false otherwise
        '''
        return itemid in self.items

    def add_relation(self, source_id, relation, target_id):
        '''
        Add relation between two items

        The function adds the forward and the automatic reverse relation.

        Args:
            source_id (str): ID of the source item
            relation (str): Relation between source and target item
            target_id (str): ID of the target item
        '''
        # Add placeholder if source item is unknown
        if source_id not in self.items:
            src = TraceableItem(source_id, True)
            self.add_item(src)
        source = self.items[source_id]
        # Error if relation is unknown
        if relation not in self.relations:
            raise TraceabilityException('Relation {name} not known'.format(name=relation), source.docname)
        # Add forward relation
        source.add_target(relation, target_id)
        # When reverse relation exists, continue to create/adapt target-item
        reverse_relation = self.get_reverse_relation(relation)
        if reverse_relation:
            # Add placeholder if target item is unknown
            if target_id not in self.items:
                tgt = TraceableItem(target_id, True)
                self.add_item(tgt)
            # Add reverse relation to target-item
            self.items[target_id].add_target(reverse_relation, source_id, implicit=True)

    def add_attribute_sorting_rule(self, filter_regex, attributes):
        """ Configures how the attributes of matching items should be sorted.

        The attributes that are missing from the given list will be sorted alphabetically underneath. The items that
        already have their attributes sorted will be returned as a list; used to report a warning.

        Args:
            filter_regex (str): Regular expression used to match items to apply the attribute sorting to.
            attributes (list): List of attributes (str) in the order they should be sorted on.

        Returns:
            list: Items that already have the order of their attributes configured.
        """
        ignored_items = []
        item_ids = self.get_items(filter_regex)
        for item_id in item_ids:
            item = self.get_item(item_id)
            if item.attribute_order:
                ignored_items.append(item)
            else:
                item.attribute_order = attributes
        return ignored_items

    def add_intermediate_node(self, node):
        """ Adds an intermediate node """
        self._intermediate_nodes.append(node)

    def define_attribute(self, attr):
        """
        Define an attribute in this collection.

        Args:
            attr (TraceableAttribute): The attribute to define
        """
        self.defined_attributes[attr.identifier] = attr

    def process_intermediate_nodes(self):
        """ Processes all intermediate nodes in order by calling its ``apply_effect`` """
        for node in sorted(self._intermediate_nodes, key=attrgetter('order')):
            node.apply_effect(self)

    def export(self, fname):
        '''
        Exports collection content. The target location of the json file gets created if it doesn't exist yet.

        Args:
            fname (str): Path to the json file to export
        '''
        Path(fname).parent.mkdir(parents=True, exist_ok=True)
        with open(fname, 'w') as outfile:
            data = []
            for itemid in self.iter_items():
                item = self.items[itemid]
                entry = item.to_dict()
                if entry:
                    data.append(entry)
            json.dump(data, outfile, indent=4, sort_keys=True)

    def self_test(self, notification_item_id, docname=None):
        '''
        Perform self test on collection content

        Args:
            notification_item_id (str/None): ID of the configured notification item, None if not configured.
            docname (str): Document on which to run the self test, None for all.
        '''
        errors = []
        notification_item = self.get_item(notification_item_id)
        # Having no valid relations, is invalid
        if not self.relations:
            raise TraceabilityException('No relations configured', 'configuration')
        # Validate each item
        for itemid, item in self.items.items():
            # Only for relevant items, filtered on document name
            if docname is not None and item.docname != docname and item.docname is not None:
                continue
            # Check if docname of notification item will be used
            if item.docname is None and notification_item:
                continue
            # On item level
            try:
                item.self_test(collection=self)
            except TraceabilityException as err:
                errors.append(err)
            # targetted items shall exist, with automatic reverse relation
            for relation in self.relations:
                # Exception: no reverse relation (external links)
                rev_relation = self.get_reverse_relation(relation)
                if rev_relation == self.NO_RELATION_STR:
                    continue
                for tgt in item.yield_targets(relation):
                    # Target item exists?
                    if tgt not in self.items:
                        errors.append(TraceabilityException("{source} {relation} {target}, but {target} is not known"
                                                            .format(source=itemid,
                                                                    relation=relation,
                                                                    target=tgt),
                                                            item.docname))
                        continue
                    # Reverse relation exists?
                    target = self.get_item(tgt)
                    if itemid not in target.yield_targets(rev_relation):
                        errors.append(TraceabilityException("No automatic reverse relation: {source} {relation} "
                                                            "{target}".format(source=tgt,
                                                                              relation=rev_relation,
                                                                              target=itemid),
                                                            item.docname))
                    # Circular relation exists?
                    for target_of_target in target.yield_targets(relation):
                        if target_of_target in item.yield_targets(rev_relation):
                            errors.append(TraceabilityException(
                                "Circular relationship found: {src} {rel} {tgt} {rel} {nested} {rel} {src}"
                                .format(src=itemid, rel=relation, tgt=tgt, nested=target_of_target),
                                item.docname))
        if errors:
            raise MultipleTraceabilityExceptions(errors)

    def __str__(self):
        '''
        Convert object to string
        '''
        retval = 'Available relations:'
        for relation in self.relations:
            reverse = self.get_reverse_relation(relation)
            retval += '\t{forward}: {reverse}\n'.format(forward=relation, reverse=reverse)
        for itemid in self.items:
            retval += str(self.items[itemid])
        return retval

    def are_related(self, source_id, relations, target_id):
        '''
        Check if 2 items are related using a list of relationships

        Placeholders are excluded

        Args:
            source_id (str): id of the source item
            relations (list): list of relations, empty list for wildcard
            target_id (str): id of the target item
        Returns:
            bool: True if both items are related through the given relationships, false otherwise
        '''
        if source_id not in self.items:
            return False
        source = self.items[source_id]
        if not source or source.is_placeholder:
            return False
        if target_id not in self.items:
            return False
        target = self.items[target_id]
        if not target or target.is_placeholder:
            return False
        if not relations:
            relations = self.relations
        return self.items[source_id].is_related(relations, target_id)

    def get_items(self, regex, attributes=None, sortattributes=None, reverse=False, sort=True):
        '''
        Get all items that match a given regular expression

        Placeholders are excluded

        Args:
            regex (str/re.Pattern): Regex pattern or object to match the items in this collection against
            attributes (dict): Dictionary with attribute-regex pairs to match the items in this collection against
            sortattributes (list): List of attributes on which to sort the items alphabetically, or using a custom
                sort order if at least one attribute is in ``attributes_sort``
            reverse (bool): True for reverse sorting
            sort (bool): When sortattributes is falsy: True to enable natural sorting, False to disable sorting

        Returns:
            list: A sorted list of item-id's matching the given regex. Sorting is done naturally when sortattributes is
            unused.
        '''
        matches = []
        for itemid, item in self.items.items():
            if item.is_placeholder:
                continue
            if item.is_match(regex) and (not attributes or item.attributes_match(attributes)):
                matches.append(itemid)
        if sortattributes:
            for attr in sortattributes:
                if attr in self.attributes_sort:
                    sorted_func = self.attributes_sort[attr]
                    break
            else:
                sorted_func = sorted
            return sorted_func(matches, key=lambda itemid: self.get_item(itemid).get_attributes(sortattributes),
                               reverse=reverse)
        if sort:
            return natsorted(matches, reverse=reverse)
        return matches

    def get_item_objects(self, regex, attributes=None):
        ''' Get all items that match a given regular expression as TraceableItem instances.

        Placeholders are excluded.

        Args:
            regex (str): Regex to match the items in this collection against
            attributes (dict): Dictionary with attribute-regex pairs to match the items in this collection against

        Returns:
            generator: An iterable of items matching the given regex.
        '''
        for item in self.items.values():
            if item.is_placeholder:
                continue
            if item.is_match(regex) and (not attributes or item.attributes_match(attributes)):
                yield item

    def get_external_targets(self, regex, relation):
        ''' Get all external targets for a given external relation with the IDs of their linked internal items

        Args:
            regex (str/re.Pattern): Regex pattern or object to match the external target
            relation (str): External relation
        Returns:
            dict: Dictionary mapping external targets to the IDs of their linked internal items
        '''
        external_targets_to_item_ids = {}
        for item_id, item in self.items.items():
            for target in item.yield_targets(relation):
                try:
                    match = regex.match(target)
                except AttributeError:
                    match = re.match(regex, target)
                if not match:
                    continue
                external_targets_to_item_ids.setdefault(target, []).append(item_id)
        return external_targets_to_item_ids

    def _handle_item_merge_conflict(self, item_id, existing_item, other_item):
        """Handle potential conflicts when merging items with the same ID."""
        # In parallel processing, the same item might be referenced by multiple workers
        # Only consider it a conflict if they have different content from different docs
        if (existing_item.docname == other_item.docname and
                existing_item.lineno == other_item.lineno):
            # Same item from same location - this is expected in parallel processing
            # Only merge relationships, not content (content should be identical)
            self._merge_relationships_only(existing_item, other_item)
            return

        if existing_item.docname != other_item.docname:
            # Items from different documents with same ID
            # This could be a real duplicate or cross-references
            # Only merge relationships, keep the first item's content
            self._merge_relationships_only(existing_item, other_item)
            return

        # Same document, different lines - this is likely a real duplicate
        raise TraceabilityException(
            f"Duplicate item '{item_id}' found in document {existing_item.docname} "
            f"at lines {existing_item.lineno} and {other_item.lineno}"
        )

    def _merge_single_item(self, item_id, other_item):
        """Merge a single item from another collection."""
        if item_id in self.items:
            existing_item = self.items[item_id]

            # If existing is placeholder but other is real, replace
            if existing_item.is_placeholder and not other_item.is_placeholder:
                self.items[item_id] = other_item
                return

            # If other is placeholder but existing is real, keep existing
            if not existing_item.is_placeholder and other_item.is_placeholder:
                # Only merge relationships from placeholder, not content
                self._merge_relationships_only(existing_item, other_item)
                return

            # If both are real items, check carefully
            if not existing_item.is_placeholder and not other_item.is_placeholder:
                self._handle_item_merge_conflict(item_id, existing_item, other_item)
                return

        # No existing item, add the new one
        self.items[item_id] = other_item

    def merge_from(self, other_collection):
        """
        Merge items and attributes from another TraceableCollection into this one.

        This method is designed to safely merge collections from worker processes
        during parallel processing, avoiding duplicate warnings while preserving
        all necessary data.

        Args:
            other_collection (TraceableCollection): The collection to merge from.
        """
        # Merge relations (should be identical across workers)
        for relation, reverse in other_collection.relations.items():
            if relation not in self.relations:
                self.relations[relation] = reverse
            elif self.relations[relation] != reverse:
                # This shouldn't happen in normal operation
                raise TraceabilityException(
                    f"Conflicting reverse relation for '{relation}': "
                    f"'{self.relations[relation]}' vs '{reverse}'"
                )

        # Merge actual items with careful conflict detection
        for item_id, other_item in other_collection.items.items():
            self._merge_single_item(item_id, other_item)

        # Merge intermediate nodes
        self._intermediate_nodes.extend(other_collection._intermediate_nodes)

        # Merge attributes_sort (should be identical)
        for key, value in other_collection.attributes_sort.items():
            if key not in self.attributes_sort:
                self.attributes_sort[key] = value

        # Merge defined_attributes (critical for parallel processing)
        # Worker processes may have modified attribute definitions, preserve these
        for attr_id, attr in other_collection.defined_attributes.items():
            self._merge_single_attribute(attr_id, attr)

        # CRITICAL FIX: After merging items, restore missing reverse relationships
        # This handles cases where workers created forward relationships but targets were in different workers
        self._restore_reverse_relationships()

    def _merge_single_attribute(self, attr_id, attr):
        """Merge a single attribute from another collection."""
        if attr_id not in self.defined_attributes:
            # New attribute from worker
            self.defined_attributes[attr_id] = attr
            return

        # Attribute exists in both - merge information from both
        existing_attr = self.defined_attributes[attr_id]
        self._update_existing_attribute(existing_attr, attr)

    def _update_existing_attribute(self, existing_attr, attr):
        """Update existing attribute with information from another attribute."""
        # Merge caption if the other has it and existing doesn't
        if attr.caption and not existing_attr.caption:
            existing_attr.caption = attr.caption

        # Merge docname and location info if the other has it and existing doesn't
        if attr.docname and not existing_attr.docname:
            existing_attr.docname = attr.docname
            existing_attr.lineno = attr.lineno

        # Merge content - handle parallel processing cases
        if hasattr(attr, 'content') and attr.content:
            existing_content = getattr(existing_attr, 'content', None)
            if not existing_content:
                # Existing has no content, use the new content
                self._safely_merge_attribute_content(existing_attr, attr)
            elif existing_content != attr.content:
                # Both have content but they differ - this shouldn't happen in normal parallel processing
                # since they should be processing the same directive content
                # Use the new content but log that we're overwriting
                self._safely_merge_attribute_content(existing_attr, attr)

        # Merge content_node if the other has it and existing doesn't
        if hasattr(attr, 'content_node') and attr.content_node and not getattr(existing_attr, 'content_node', None):
            existing_attr.content_node = attr.content_node

        # Always update the identifier to ensure consistency
        existing_attr.identifier = attr.identifier

    def _safely_merge_attribute_content(self, existing_attr, attr):
        """Safely merge attribute content with proper cleanup."""
        # Suppress content warnings during legitimate merging operations
        existing_attr._suppress_content_warnings = True
        try:
            existing_attr.content = attr.content
        finally:
            # Always clean up the flag
            if hasattr(existing_attr, '_suppress_content_warnings'):
                delattr(existing_attr, '_suppress_content_warnings')

    def _merge_relationships_only(self, target_item, source_item):
        """
        Merge only relationships from source_item into target_item, without touching content.

        This is safer than using update() which can modify content inappropriately.
        """
        # Merge explicit relationships
        for relation, targets in source_item.explicit_relations.items():
            if relation not in target_item.explicit_relations:
                target_item.explicit_relations[relation] = []
            for target_id in targets:
                if target_id not in target_item.explicit_relations[relation]:
                    target_item.explicit_relations[relation].append(target_id)

        # Merge implicit relationships
        for relation, targets in source_item.implicit_relations.items():
            if relation not in target_item.implicit_relations:
                target_item.implicit_relations[relation] = []
            for target_id in targets:
                if target_id not in target_item.implicit_relations[relation]:
                    target_item.implicit_relations[relation].append(target_id)

    def _restore_reverse_relationships(self):
        """
        Restore missing reverse relationships after merging collections.

        During parallel processing, a worker might create a forward relationship to an item
        that exists in another worker. After merging, we need to ensure all reverse
        relationships are properly established.
        """
        for item_id, item in self.items.items():
            # Check all explicit relationships in this item
            for relation, targets in item.explicit_relations.items():
                self._restore_reverse_for_relation(item_id, relation, targets)

    def _restore_reverse_for_relation(self, item_id, relation, targets):
        """Restore reverse relationships for a specific relation."""
        reverse_relation = self.get_reverse_relation(relation)
        if not reverse_relation or reverse_relation == self.NO_RELATION_STR:
            return

        # For each target, ensure the reverse relationship exists
        for target_id in targets:
            self._ensure_reverse_relationship(item_id, target_id, reverse_relation)

    def _ensure_reverse_relationship(self, item_id, target_id, reverse_relation):
        """Ensure a reverse relationship exists between target and item."""
        if target_id not in self.items:
            return

        target_item = self.items[target_id]
        # Check if reverse relationship already exists (implicitly)
        existing_reverse_targets = list(
            target_item.iter_targets(reverse_relation, explicit=False, implicit=True)
        )

        if item_id not in existing_reverse_targets:
            # Add the missing reverse relationship as implicit
            try:
                target_item.add_target(reverse_relation, item_id, implicit=True)
            except TraceabilityException:
                # Target already exists - this is fine
                pass

    def remove_items_from_document(self, docname: str):
        """
        Remove all items and related data that belong to a specific document.

        This method is used during env-purge-doc to clean up removed documents.

        Args:
            docname (str): The document name to remove items from
        """
        # Find items to remove
        items_to_remove = []
        for item_id, item in self.items.items():
            if item.docname == docname:
                items_to_remove.append(item_id)

        # Remove the items
        for item_id in items_to_remove:
            del self.items[item_id]

        # Remove relationships pointing to removed items
        for item in self.items.values():
            item.remove_targets_by_ids(items_to_remove)

        # Remove intermediate nodes from this document
        self._intermediate_nodes = [
            node for node in self._intermediate_nodes
            if node.get('document') != docname
        ]

    def get_document_items(self, docname: str) -> Dict[str, 'TraceableItem']:
        """
        Get all items that belong to a specific document.

        Args:
            docname (str): The document name

        Returns:
            Dict[str, TraceableItem]: Dictionary of item_id -> item for the document
        """
        return {
            item_id: item for item_id, item in self.items.items()
            if item.docname == docname
        }


class ParallelSafeTraceableCollection:
    """
    Multiprocess-safe wrapper for TraceableCollection that enables parallel reading.

    During parallel reading, each worker process gets its own TraceableCollection
    instance. After reading, all process collections are merged via env-merge-info.
    """

    def __init__(self):
        # Use a regular collection - no threading.local() since Sphinx uses multiprocessing
        object.__setattr__(self, '_collection', TraceableCollection())
        object.__setattr__(self, '_is_worker_process', False)

    def _get_current_collection(self) -> TraceableCollection:
        """Get the current collection."""
        return self._collection

    def set_main_collection(self, collection: TraceableCollection):
        """Set the main collection (called during environment initialization)."""
        # Always copy the configuration
        self._collection.relations = collection.relations.copy()
        self._collection.attributes_sort = collection.attributes_sort.copy()
        self._collection.defined_attributes = collection.defined_attributes.copy()

        # Copy items only if we're not in a worker process
        if not self._is_worker_process:
            self._collection.items = collection.items.copy()
            self._collection._intermediate_nodes = collection._intermediate_nodes.copy()

    def mark_as_worker_process(self):
        """Mark this collection as being in a worker process."""
        self._is_worker_process = True
        # Clear items for worker process (they should build their own subset)
        self._collection.items = {}
        self._collection._intermediate_nodes = []

    def add_relation_pair(self, forward, reverse=None):
        """Add a relation pair (ensure this works for workers)."""
        if reverse is None:
            reverse = self._collection.NO_RELATION_STR
        return self._collection.add_relation_pair(forward, reverse)

    # Delegate all collection methods to the current collection
    def __getattr__(self, name):
        """Delegate attribute access to the current collection."""
        # Avoid recursion during pickling/unpickling
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        # Check if we have a collection to delegate to
        try:
            collection = object.__getattribute__(self, '_collection')
        except AttributeError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        if collection is None:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        return getattr(collection, name)

    def __setattr__(self, name, value):
        """Handle attribute setting."""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._collection, name, value)

    # Explicitly define key methods to ensure they work properly
    def add_item(self, item):
        """Add item to current collection."""
        return self._collection.add_item(item)

    def add_relation(self, source_id, relation, target_id):
        """Add relation to current collection."""
        return self._collection.add_relation(source_id, relation, target_id)

    def add_intermediate_node(self, node):
        """Add intermediate node to current collection."""
        return self._collection.add_intermediate_node(node)

    def has_item(self, item_id):
        """Check if item exists."""
        return self._collection.has_item(item_id)

    def get_item(self, item_id):
        """Get an item by ID."""
        return self._collection.get_item(item_id)

    def iter_items(self):
        """Iterate over items."""
        return self._collection.iter_items()

    def get_reverse_relation(self, relation):
        """Get reverse relation."""
        return self._collection.get_reverse_relation(relation)

    def iter_relations(self):
        """Iterate relations."""
        return self._collection.iter_relations()

    def merge_from(self, other_collection):
        """Merge items from another collection."""
        if hasattr(other_collection, '_collection'):
            # If it's a ParallelSafeTraceableCollection, get the inner collection
            return self._collection.merge_from(other_collection._collection)
        else:
            # If it's a regular TraceableCollection, merge directly
            return self._collection.merge_from(other_collection)

    def remove_items_from_document(self, docname: str):
        """Remove all items from a specific document."""
        return self._collection.remove_items_from_document(docname)

    def define_attribute(self, attr):
        """Define an attribute in the collection."""
        return self._collection.define_attribute(attr)

    def __getstate__(self):
        """Custom pickling support."""
        return {
            '_collection': self._collection,
            '_is_worker_process': self._is_worker_process
        }

    def __setstate__(self, state):
        """Custom unpickling support."""
        object.__setattr__(self, '_collection', state['_collection'])
        object.__setattr__(self, '_is_worker_process', state['_is_worker_process'])
