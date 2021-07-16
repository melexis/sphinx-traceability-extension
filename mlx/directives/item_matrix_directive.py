import re
from collections import namedtuple, OrderedDict
from copy import deepcopy

from docutils import nodes
from docutils.parsers.rst import directives
from natsort import natsorted

from mlx.traceability_exception import report_warning, TraceabilityException
from mlx.traceable_base_directive import TraceableBaseDirective
from mlx.traceable_base_node import TraceableBaseNode
from mlx.traceable_item import TraceableItem


def group_choice(argument):
    """Conversion function for the "group" option."""
    return directives.choice(argument, ('top', 'bottom'))


class ItemMatrix(TraceableBaseNode):
    '''Matrix for cross referencing documentation items'''

    def perform_replacement(self, app, collection):
        """
        Creates table with related items, printing their target references. Only source and target items matching
        respective regexp shall be included.

        Args:
            app: Sphinx application object to use.
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        Rows = namedtuple('Rows', "sorted covered uncovered")
        source_ids = collection.get_items(self['source'], attributes=self['filter-attributes'])
        targets_with_ids = []
        for target_regex in self['target']:
            targets_with_ids.append(collection.get_items(target_regex))
        top_node = self.create_top_node(self['title'])
        table = nodes.table()
        if self.get('classes'):
            table.get('classes').extend(self.get('classes'))

        # Column and heading setup
        titles = [nodes.paragraph('', title) for title in [self['sourcetitle'], *self['targettitle']]]

        if self['hidetarget']:
            titles = titles[0]
        for attr in reversed(self['sourceattributes']):
            titles.insert(1, self.make_attribute_ref(app, attr))
        for attr in self['targetattributes']:
            titles.append(self.make_attribute_ref(app, attr))
        show_intermediate = bool(self['intermediatetitle']) and bool(self['intermediate'])
        if show_intermediate:
            titles.insert(1 + len(self['sourceattributes']), nodes.paragraph('', self['intermediatetitle']))
        if self['hidesource']:
            titles.pop(0)
        headings = [nodes.entry('', title) for title in titles]
        number_of_columns = len(titles)
        tgroup = nodes.tgroup()
        tgroup += [nodes.colspec(colwidth=5) for _ in range(number_of_columns)]
        tgroup += nodes.thead('', nodes.row('', *headings))
        table += tgroup

        # External relationships are treated a bit special in item-matrices:
        # - External references are only shown if explicitly requested in the "type" configuration
        # - No target filtering is done on external references
        mapping_via_intermediate = {}
        if not self['type']:
            # if no explicit relationships were given, we consider all of them (except for external ones)
            relationships = [rel for rel in collection.iter_relations() if not self.is_relation_external(rel)]
            external_relationships = []
        else:
            relationships = self['type'].split(' ')
            external_relationships = [rel for rel in relationships if self.is_relation_external(rel)]
            if ' | ' in self['type']:
                mapping_via_intermediate = self.linking_via_intermediate(source_ids, targets_with_ids, collection)

        count_covered = 0
        duplicate_source_count = 0
        rows = Rows([], [], [])
        for source_id in source_ids:
            source_item = collection.get_item(source_id)
            if self['sourcetype'] and not source_item.has_relations(self['sourcetype']):
                continue
            covered = False
            rights = [[] for _ in range(int(bool(self['intermediate'])) + len(self['target']))]
            if mapping_via_intermediate:
                covered = source_id in mapping_via_intermediate
                if covered:
                    args = [rows, source_item, rights, app]
                    duplicate_source_count += self._store_source_via_intermediate(mapping_via_intermediate[source_id],
                                                                                  *args)
            else:
                has_external_target = self.add_external_targets(rights, source_item, external_relationships, app)
                has_internal_target = self.add_internal_targets(rights, source_id, targets_with_ids, relationships,
                                                                collection)
                covered = has_external_target or has_internal_target
            if not (covered and mapping_via_intermediate):
                self._create_and_store_row(rows, source_item, rights, covered, app)

        if not source_ids:
            # try to use external targets as source
            for ext_rel in external_relationships:
                external_targets = collection.get_external_targets(self['source'], ext_rel)
                # natural sorting on source
                for ext_source, target_ids in OrderedDict(natsorted(external_targets.items())).items():
                    covered = False
                    left = nodes.entry()
                    left += self.make_external_item_ref(app, ext_source, ext_rel)
                    rights = [nodes.entry('') for _ in range(number_of_columns - 1)]
                    covered = self._fill_target_cells(app, rights, target_ids)
                    self._create_and_store_row(rows, left, rights, covered, app)

        tgroup += self._build_table_body(rows, self['group'])

        count_total = len(rows.covered) + len(rows.uncovered) - duplicate_source_count
        count_covered = len(rows.covered) - duplicate_source_count
        try:
            percentage = int(100 * count_covered / count_total)
        except ZeroDivisionError:
            percentage = 0
        disp = 'Statistics: {cover} out of {total} covered: {pct}%'.format(cover=count_covered,
                                                                           total=count_total,
                                                                           pct=percentage)
        if self['stats']:
            if self['onlycovered']:
                disp += ' (uncovered items are hidden)'
            p_node = nodes.paragraph()
            txt = nodes.Text(disp)
            p_node += txt
            top_node += p_node

        top_node += table
        self.replace_self(top_node)

    @staticmethod
    def _build_table_body(rows, group):
        """ Creates the table body and fills it with rows, grouping when desired

        Args:
            rows (Rows): Rows namedtuple object
            group (str): Group option, falsy to disable grouping, 'top' or 'bottom' otherwise

        Returns:
            nodes.tbody: Filled table body
        """
        tbody = nodes.tbody()
        if not group:
            tbody += rows.sorted
        elif group == 'top':
            tbody += rows.uncovered
            tbody += rows.covered
        elif group == 'bottom':
            tbody += rows.covered
            tbody += rows.uncovered
        return tbody

    def add_all_targets(self, right_cells, linked_items):
        """ Adds intermediate items followed by internal target items

            right_cells (list): List of empty lists to fill with target items and, when enabled,
                intermediates items first
            linked_items (dict): Mapping of intermediate items to the list of sets of target items per target
        """
        for intermediate_item in linked_items:
            right_cells[0].append(intermediate_item)

        # avoid duplicate target IDs in the same cell due to multiple intermediates with the same target item
        added_items_per_column = {}
        for targets in linked_items.values():
            for idx, target_items in enumerate(targets):
                if idx not in added_items_per_column:
                    added_items_per_column[idx] = set()
                for target_item in target_items.difference(added_items_per_column[idx]):
                    if not self['hidetarget']:
                        right_cells[idx + 1].append(target_item)
                    added_items_per_column[idx].add(target_item)

    def add_external_targets(self, right_cells, source_item, external_relationships, app):
        """ Adds links to external targets for given source to the list of data per column

        Args:
            right_cells (list): List of lists to add external target link(s) to when covered
            source_item (TraceableItem): Source item
            external_relationships (list): List of all valid external relationships between source and target(s)
            app (sphinx.application.Sphinx): Sphinx application object

        Returns:
            bool: True if one or more external targets have been found for the given source item, False otherwise
        """
        has_external_target = False
        for external_relationship in external_relationships:
            for target_id in source_item.iter_targets(external_relationship):
                ext_item_ref = self.make_external_item_ref(app, target_id, external_relationship)
                for cell in right_cells:
                    cell.append(ext_item_ref)
                has_external_target = True
        return has_external_target

    def add_internal_targets(self, right_cells, source_id, targets_with_ids, relationships, collection):
        """ Adds internal target items for given source to the list of data per column

        Args:
            right_cells (list): List of lists to add target items to when covered
            source_id (str): Item ID of source item
            targets_with_ids (list): List of lists per target, listing target IDs to take into consideration
            relationships (list): List of all valid relationships between source and target(s)
            collection (TraceableCollection): Collection of TraceableItems

        Returns:
            bool: True if one or more internal targets have been found for the given source item, False otherwise
        """
        has_internal_target = False
        for idx, target_ids in enumerate(targets_with_ids):
            for target_id in target_ids:
                if collection.are_related(source_id, relationships, target_id):
                    right_cells[idx].append(collection.get_item(target_id))
                    has_internal_target = True
        return has_internal_target

    def linking_via_intermediate(self, source_ids, targets_with_ids, collection):
        """ Maps source IDs to IDs of target items that are linked via an itermediate item per target

        Only covered source IDs are stored.

        Args:
            source_ids (list): List of item IDs of source items
            targets_with_ids (list): List of lists, which contain target IDs to take into consideration, per target
            collection (TraceableCollection): Collection of TraceableItems

        Returns:
            dict: Mapping of source IDs as key with as value a mapping of intermediate items to
                the list of sets of target items per target
        """
        links_with_relationships = []
        for relationships_str in self['type'].split(' | '):
            links_with_relationships.append(relationships_str.split(' '))
        if len(links_with_relationships) > 2:
            raise TraceabilityException("Type option of item-matrix must not contain more than one '|' "
                                        "character; got {}".format(self['type']),
                                        docname=self["document"])
        # reverse relationship(s) specified for linking source to intermediate
        for idx, rel in enumerate(links_with_relationships[0]):
            links_with_relationships[0][idx] = collection.get_reverse_relation(rel)

        source_to_links_map = {}
        excluded_source_ids = set()
        for intermediate_id in collection.get_items(self['intermediate'], sort=bool(self['intermediatetitle'])):
            intermediate_item = collection.get_item(intermediate_id)

            potential_source_ids = set()
            for reverse_rel in links_with_relationships[0]:
                potential_source_ids.update(intermediate_item.iter_targets(reverse_rel, sort=False))
            # apply :source: filter
            potential_source_ids = potential_source_ids.intersection(source_ids)
            potential_source_ids = potential_source_ids.difference(excluded_source_ids)
            if not potential_source_ids:
                continue

            potential_target_ids = set()
            for forward_rel in links_with_relationships[1]:
                potential_target_ids.update(intermediate_item.iter_targets(forward_rel, sort=False))
            if not potential_target_ids:
                if self['coveredintermediates']:
                    excluded_source_ids.update(potential_source_ids)
                continue
            # apply :target: filter
            covered = False
            actual_targets = []
            for target_ids in targets_with_ids:
                linked_target_ids = potential_target_ids.intersection(target_ids)
                if linked_target_ids:
                    covered = True
                actual_targets.append(set(collection.get_item(id_) for id_ in linked_target_ids))

            if covered:
                self._store_targets(source_to_links_map, potential_source_ids, actual_targets, intermediate_item)
            elif self['coveredintermediates']:
                excluded_source_ids.update(potential_source_ids)
        for source_id in excluded_source_ids:
            source_to_links_map.pop(source_id, None)
        return source_to_links_map

    @staticmethod
    def _store_targets(source_to_links_map, source_ids, targets, intermediate_item):
        """ Extends given mapping with target IDs per target as value for each source ID as key

        Args:
            source_to_links_map (dict): Mapping of source IDs as key with as value a mapping of intermediate items to
                the list of sets of target IDs per target
                intermediate and target item IDs (set)
            source_ids (set): Source IDs to store targets for
            targets (list): List of linked target items (set) per target
            intermediate_item (TraceableItem): Intermediate item that links the given source items to the given target items
        """
        for source_id in source_ids:
            if source_id not in source_to_links_map:
                source_to_links_map[source_id] = {}
            source_to_links_map[source_id][intermediate_item] = targets

    def _store_source_via_intermediate(self, linked_items, *args):
        """ Stores row(s) for a source, linking targets via intermediates

        Args:
            linked_items (dict): Mapping of all intermediate IDs to the list of sets of target items per target

        Returns:
            int: Number of rows that have been added with a duplicate source ID
        """
        duplicate_source_count = 0
        if self['splitintermediates']:
            for intermediate, targets in linked_items.items():
                self._store_row_with_intermediate({intermediate: targets}, *args)
            duplicate_source_count += len(linked_items) - 1
        else:
            self._store_row_with_intermediate(linked_items, *args)
        return duplicate_source_count

    def _store_row_with_intermediate(self, linked_items, rows, source, empty_right_cells, app):
        """ Stores a row for a source, linking targets via one or all intermediates

        Args:
            linked_items (dict): Mapping of one or all intermediate IDs to the list of sets of target items per target
            rows (Rows): Rows namedtuple object to extend
            source (TraceableItem): Source item
            empty_right_cells (list): List of empty lists to fill with target items and, when enabled,
                intermediates items first
            app (sphinx.application.Sphinx): Sphinx application object
        """
        right_cells = deepcopy(empty_right_cells)
        self.add_all_targets(right_cells, linked_items)
        self._create_and_store_row(rows, source, right_cells, True, app)

    def _create_and_store_row(self, rows, source, right_cells, covered, app):
        """ Stores the leftmost cell and righthand cells in a row in the given Rows object.

        Args:
            rows (Rows): Rows namedtuple object to extend
            source (TraceableItem|nodes.entry): Traceable source item or cell for source
            right_cells (list): List of lists with intermediate or target items or paragraphs with a link to them
            covered (bool): True if the row shall be stored in the covered attribute, False for uncovered attribute
            app (sphinx.application.Sphinx): Sphinx application object
        """
        row = nodes.row()

        # source
        if isinstance(source, nodes.entry):
            source_cell = source
            source_attribute_cells = [nodes.entry() for _ in range(len(self['sourceattributes']))]
        else:
            source_cell = nodes.entry()
            source_cell += self.make_internal_item_ref(app, source.get_id())
            source_attribute_cells = self._create_cells_for_attributes([source], self['sourceattributes'])
        if not self['hidesource']:
            add_source_cell = True
            if self['splitintermediates'] and isinstance(source, TraceableItem) and rows.sorted:
                previous_row = rows.sorted[0]
                previous_source_cell = previous_row[0]
                if source.get_id() in str(previous_source_cell):
                    previous_source_cell['morerows'] = 1 + previous_source_cell.get('morerows', 0)
                    add_source_cell = False
            if add_source_cell:
                row += source_cell
        for cell in source_attribute_cells:
            row += cell

        # intermediate and/or target(s)
        target_attribute_cells = self._create_cells_for_attributes(right_cells[-1], self['targetattributes'])
        if self['intermediate'] and not self['intermediatetitle']:
            right_cells.pop(0)
        if self['hidetarget']:
            right_cells.pop(-1)
        for cell_data in right_cells:
            row += self._create_cell_for_items(cell_data, app)
        for cell in target_attribute_cells:
            row += cell

        # store row
        if covered:
            rows.covered.append(row)
            rows.sorted.append(row)
        else:
            rows.uncovered.append(row)
            if not self['onlycovered']:
                rows.sorted.append(row)

    def _fill_target_cells(self, app, target_cells, item_ids):
        """ Fills target cells with linked items, filtered by target option.

        Returns whether the source has been covered or not.

        Args:
            app: Sphinx application object to use
            target_cells (list): List of empty cells
            item_ids (list): List of item IDs

        Returns:
            bool: True if a target cell contains an item, False otherwise
        """
        covered = False
        for idx, target_regex in enumerate(self['target']):
            for target_id in item_ids:
                if re.match(target_regex, target_id):
                    target_cells[idx].append(self.make_internal_item_ref(app, target_id))
                    covered = True
        return covered

    def _create_cell_for_items(self, cell_data, app):
        cell = nodes.entry('')
        for entry in cell_data:
            if isinstance(entry, nodes.paragraph):
                cell += entry
            else:
                cell += self.make_internal_item_ref(app, entry.get_id())
        return cell

    @staticmethod
    def _create_cells_for_attributes(items, attributes):
        cells = []
        for attr in attributes:
            cell = nodes.entry('')
            for item in items:
                if isinstance(item, nodes.paragraph):
                    attribute_value = '-'
                else:
                    attribute_value = item.get_attribute(attr)
                if not attribute_value:
                    attribute_value = '-'
                cell += nodes.paragraph('', attribute_value)
            cells.append(cell)
        return cells


class ItemMatrixDirective(TraceableBaseDirective):
    """
    Directive to generate a matrix of item cross-references, based on
    a given set of relationship types.

    Syntax::

      .. item-matrix:: title
         :target: regexp
         :source: regexp
         :intermediate: regexp
         :<<attribute>>: regexp
         :targettitle: Target column header(s)
         :sourcetitle: Source column header
         :intermediatetitle: Intermediate column header
         :type: <<relationship>> ...
         :sourcetype: <<relationship>> ...
         :sourceattributes: <<attribute>> ...
         :targetattributes: <<attribute>> ...
         :hidesource:
         :hidetarget:
         :splitintermediates:
         :group: top | bottom
         :onlycovered:
         :stats:
         :nocaptions:
         :onlycaptions:
    """
    # Optional argument: title (whitespace allowed)
    optional_arguments = 1
    # Options
    option_spec = {
        'class': directives.class_option,
        'target': directives.unchanged,
        'source': directives.unchanged,
        'intermediate': directives.unchanged,
        'targettitle': directives.unchanged,
        'sourcetitle': directives.unchanged,
        'intermediatetitle': directives.unchanged,
        'type': directives.unchanged,  # relationship types separated by space
        'sourcetype': directives.unchanged,  # relationship types separated by space
        'sourceattributes': directives.unchanged,  # attributes separated by space
        'targetattributes': directives.unchanged,  # attributes separated by space
        'hidesource': directives.flag,
        'hidetarget': directives.flag,
        'splitintermediates': directives.flag,
        'group': group_choice,
        'onlycovered': directives.flag,
        'coveredintermediates': directives.flag,
        'stats': directives.flag,
        'nocaptions': directives.flag,
        'onlycaptions': directives.flag,
    }
    # Content disallowed
    has_content = False

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        item_matrix_node = ItemMatrix('')
        item_matrix_node['document'] = env.docname
        item_matrix_node['line'] = self.lineno

        if self.options.get('class'):
            item_matrix_node.get('classes').extend(self.options.get('class'))

        self.process_title(item_matrix_node, 'Traceability matrix of items')

        self.add_found_attributes(item_matrix_node)

        self.process_options(
            item_matrix_node,
            {
                'target':            {'default': ['']},
                'intermediate':      {'default': ''},
                'source':            {'default': ''},
                'targettitle':       {'default': ['Target'], 'delimiter': ','},
                'sourcetitle':       {'default': 'Source'},
                'intermediatetitle': {'default': ''},
                'type':              {'default': ''},
                'sourcetype':        {'default': []},
            },
        )

        if item_matrix_node['intermediate'] and ' | ' not in item_matrix_node['type']:
            raise TraceabilityException("The :intermediate: option is used, expected at least two relationships "
                                        "separated by ' | ' in the :type: option; got {!r}"
                                        .format(item_matrix_node['type']),
                                        docname=env.docname)

        # Process ``group`` option, given as a string that is either top or bottom or empty ().
        item_matrix_node['group'] = self.options.get('group', '')

        number_of_targets = len(item_matrix_node['target'])
        number_of_targettitles = len(item_matrix_node['targettitle'])
        if number_of_targets != number_of_targettitles:
            raise TraceabilityException(
                "Item-matrix directive should have the same number of values for the options 'target' and "
                "'targettitle'. Got target: {targets} and targettitle: {titles}"
                .format(targets=item_matrix_node['target'], titles=item_matrix_node['targettitle']),
                docname=env.docname)

        if item_matrix_node['type']:
            self.check_relationships(item_matrix_node['type'].replace(' | ', ' ').split(' '), env)
        self.check_relationships(item_matrix_node['sourcetype'], env)

        self.add_attributes(item_matrix_node, 'sourceattributes', [])
        self.add_attributes(item_matrix_node, 'targetattributes', [])
        if item_matrix_node['targetattributes'] and len(item_matrix_node['target']) > 1:
            item_matrix_node['targetattributes'] = []
            report_warning("Item-matrix directive cannot combine 'targetattributes' with more than one 'target'; "
                           "ignoring 'targetattributes' option", docname=env.docname, lineno=self.lineno)

        self.check_option_presence(item_matrix_node, 'hidesource')
        self.check_option_presence(item_matrix_node, 'hidetarget')
        self.check_option_presence(item_matrix_node, 'splitintermediates')
        self.check_option_presence(item_matrix_node, 'onlycovered')
        self.check_option_presence(item_matrix_node, 'coveredintermediates')
        self.check_option_presence(item_matrix_node, 'stats')

        self.check_caption_flags(item_matrix_node, app.config.traceability_matrix_no_captions)

        return [item_matrix_node]
