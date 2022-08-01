import re
from collections import namedtuple
from copy import copy, deepcopy

from docutils import nodes
from docutils.parsers.rst import directives
from natsort import natsorted, natsort_keygen

from mlx.traceability_exception import TraceabilityException, report_warning
from mlx.traceable_base_directive import TraceableBaseDirective
from mlx.traceable_base_node import TraceableBaseNode
from mlx.traceable_item import TraceableItem

natsort_key = natsort_keygen(key=lambda item: getattr(item, 'identifier', ''))


def group_choice(argument):
    """Conversion function for the "group" option."""
    return directives.choice(argument, ('top', 'bottom'))


class ItemMatrix(TraceableBaseNode):
    '''Matrix for cross referencing documentation items'''

    COVERAGE_REGEX = re.compile(r'([><]=?|==|!=)\s*[\d\./]+')

    def perform_replacement(self, app, collection):
        """
        Creates table with related items, printing their target references. Only source and target items matching
        respective regexp shall be included.

        Args:
            app: Sphinx application object to use.
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        Rows = namedtuple('Rows', "sorted covered uncovered counters")
        filters = {x: None for x in ['source', 'target']}
        if self['filtertarget']:
            filters['target'] = self['filter-attributes']
        else:
            filters['source'] = self['filter-attributes']
        source_ids = collection.get_items(self['source'], attributes=filters['source'])
        targets_with_ids = []
        for target_regex in self['target']:
            targets_with_ids.append(collection.get_items(target_regex, attributes=filters['target']))
        top_node = self.create_top_node(self['title'], hide_title=self['hidetitle'])
        table = nodes.table()
        if self.get('classes'):
            table.get('classes').extend(self.get('classes'))

        # Column and heading setup
        titles = [nodes.paragraph('', title) for title in [self['sourcetitle'], *self['targettitle']]]

        if self['hidetarget']:
            titles = titles[0]
        for value in reversed(self['sourcecolumns']):
            if value in TraceableItem.defined_attributes:
                titles.insert(1, self.make_attribute_ref(app, value))
            else:
                titles.insert(1, nodes.paragraph('', value))
        for value in self['targetcolumns']:
            if value in TraceableItem.defined_attributes:
                titles.append(self.make_attribute_ref(app, value))
            else:
                titles.append(nodes.paragraph('', app.config.traceability_relationship_to_string[value]))
        show_intermediate = bool(self['intermediatetitle']) and bool(self['intermediate'])
        if show_intermediate:
            titles.insert(1 + len(self['sourcecolumns']), nodes.paragraph('', self['intermediatetitle']))
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

        duplicate_count_total = 0
        duplicate_count_covered = 0
        rows = Rows([], [], [], [0, 0])
        for source_id in source_ids:
            source_item = collection.get_item(source_id)
            if self['sourcetype'] and not source_item.has_relations(self['sourcetype']):
                continue
            covered = False
            rights = [[] for _ in range(int(bool(self['intermediate'])) + len(self['target']))]
            if mapping_via_intermediate:
                intermediates = mapping_via_intermediate[source_id]
                if not intermediates:
                    self._store_data(rows, source_item, rights, False, app)
                    continue
                covered_intermediates = {intermediate: any(target_set for target_set in target_sets)
                                         for intermediate, target_sets in intermediates.items()}

                if self['coveredintermediates']:
                    covered = all(covered_intermediates.values())
                else:
                    covered = any(covered_intermediates.values())

                if self['splitintermediates']:
                    for intermediate, target_sets in intermediates.items():
                        self._store_row_with_intermediate({intermediate: target_sets},
                                                          rows, source_item, rights, covered, app)
                    duplicate_count_for_source = len(intermediates) - 1
                    duplicate_count_total += duplicate_count_for_source
                    duplicate_count_covered += duplicate_count_for_source if covered else 0
                else:
                    self._store_row_with_intermediate({intermediate: target_sets for intermediate, target_sets
                                                       in intermediates.items()
                                                       if covered and covered_intermediates[intermediate]},
                                                      rows, source_item, rights, covered, app)
            else:
                has_external_target = self.add_external_targets(rights, source_item, external_relationships, app)
                has_internal_target = self.add_internal_targets(rights, source_id, targets_with_ids, relationships,
                                                                collection)
                covered = has_external_target or has_internal_target
                self._store_data(rows, source_item, rights, covered, app)

        if not source_ids:
            # try to use external targets as source
            for ext_rel in external_relationships:
                external_targets = collection.get_external_targets(self['source'], ext_rel)
                # natural sorting on source
                for ext_source, target_ids in natsorted(external_targets.items()):
                    covered = False
                    source_link = self.make_external_item_ref(app, ext_source, ext_rel)
                    rights = [[] for _ in range(len(self['target']))]
                    target_items = [collection.get_item(id_) for id_ in target_ids]
                    covered = self._add_target_items(rights, target_items)
                    self._store_data(rows, source_link, rights, covered, app)

        tgroup += self._build_table_body(rows, self['group'], self['onlycovered'], self['onlyuncovered'])

        count_total = rows.counters[0] + rows.counters[1] - duplicate_count_total
        count_covered = rows.counters[0] - duplicate_count_covered
        try:
            percentage = 100 * count_covered / count_total
        except ZeroDivisionError:
            percentage = 0
        self._check_coverage(percentage)

        if self['stats']:
            disp = 'Statistics: {cover} out of {total} covered: {pct}%'.format(cover=count_covered,
                                                                               total=count_total,
                                                                               pct=int(percentage))
            if self['onlycovered']:
                disp += ' (uncovered items are hidden)'
            elif self['onlyuncovered']:
                disp += ' (covered items are hidden)'
            p_node = nodes.paragraph()
            txt = nodes.Text(disp)
            p_node += txt
            top_node += p_node

        if number_of_columns:
            top_node += table
        self.replace_self(top_node)

    def _build_table_body(self, rows, group, onlycovered, onlyuncovered):
        """ Creates the table body and fills it with rows, grouping and excluding uncovered source items when desired

        Args:
            rows (Rows): Rows namedtuple object
            group (str): Group option, falsy to disable grouping, 'top' or 'bottom' otherwise
            onlycovered (bool): True to only include source items that are covered; False otherwise
            onlyuncovered (bool): True to only include source items that are uncovered; False otherwise

        Returns:
            nodes.tbody: Filled table body
        """
        tbody = nodes.tbody()
        if onlycovered:
            tbody += rows.covered
        elif onlyuncovered:
            tbody += rows.uncovered
        elif not group:
            tbody += rows.sorted
        elif group == 'top':
            tbody += rows.uncovered
            tbody += rows.covered
        elif group == 'bottom':
            tbody += rows.covered
            tbody += rows.uncovered

        self._postprocess_tbody(tbody)

        return tbody

    def _postprocess_tbody(self, tbody):
        """ Merges cells where appropriate to avoid duplication and removes certain columns depending on configuration

        Args:
            tbody (nodes.tbody): Table body to modify
        """
        indexes_to_merge = range(1 + len(self['sourcecolumns']) + int(bool(self['intermediate'])))
        cells_to_remove = self._set_rowspan(tbody, indexes_to_merge)

        intermediate_idx = indexes_to_merge[-1] if self['intermediate'] else None
        target_idxes = []
        for idx in reversed(range(len(self['target']))):
            target_idxes.append(-1 * (idx + 1) * (1 + len(self['targetcolumns'])))
        for row_idx, row in enumerate(tbody):
            # order of if-statements below is important: remove cells from right to left
            if self['intermediate'] and (not self['intermediatetitle'] or intermediate_idx in cells_to_remove[row_idx]):
                row.pop(intermediate_idx)
            for idx in reversed(range(1, 1 + len(self['sourcecolumns']))):
                if idx in cells_to_remove[row_idx]:
                    row.pop(idx)
            if self['hidesource'] or 0 in cells_to_remove[row_idx]:
                row.pop(0)
            if self['hidetarget']:
                for idx in target_idxes:
                    row.pop(idx)

    @staticmethod
    def _set_rowspan(tbody, indexes):
        """ Sets the 'rowspan' attribute of cells that should span multiple rows to avoid duplication

        Args:
            tbody (nodes.tbody): Table body
            indexes (iterable): Range object with indexes of columns to take into account

        Returns:
            dict: Mapping of row indices to list of column indices, of cells that shall be removed from the table body
        """
        prev_row = None
        cells_to_remove = {}
        original_cells = {idx: None for idx in indexes}
        for row_idx, row in enumerate(tbody):
            cells_to_remove[row_idx] = []
            if prev_row is None:
                prev_row = row
                continue

            for col_idx, cell in original_cells.items():
                if str(row[col_idx]) == str(prev_row[col_idx]):
                    if cell is None:
                        original_cells[col_idx] = prev_row[col_idx]  # do not set `cell`
                    original_cells[col_idx]['morerows'] = 1 + original_cells[col_idx].get('morerows', 0)
                    cells_to_remove[row_idx].append(col_idx)
                elif col_idx == 0:  # new source so reset and move on to next row
                    original_cells = {idx: None for idx in indexes}
                    break
                else:
                    original_cells[col_idx] = None

            prev_row = row
        return cells_to_remove

    @staticmethod
    def add_all_targets(right_cells, linked_items):
        """ Adds intermediate items followed by internal target items

        Args:
            right_cells (list): List of empty lists to fill with intermediates items followed by target items
            linked_items (dict): Mapping of intermediate items to the list of sets of target items per target
        """
        # avoid duplicate target IDs in the same cell due to multiple intermediates with the same target item
        added_items_per_column = {}
        for intermediate_item, targets in linked_items.items():
            right_cells[0].append(intermediate_item)
            for idx, target_items in enumerate(targets, start=1):
                if idx not in added_items_per_column:
                    added_items_per_column[idx] = set()
                for target_item in target_items.difference(added_items_per_column[idx]):
                    right_cells[idx].append(target_item)
                    added_items_per_column[idx].add(target_item)
                right_cells[idx].sort(key=natsort_key)
        right_cells[0].sort(key=natsort_key)

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
            for target_id in source_item.yield_targets_sorted(external_relationship):
                ext_item_ref = self.make_external_item_ref(app, target_id, external_relationship)
                for cell in right_cells:
                    cell.append(ext_item_ref)
                has_external_target = True
        return has_external_target

    @staticmethod
    def add_internal_targets(right_cells, source_id, targets_with_ids, relationships, collection):
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

        source_to_links_map = {source_id: {} for source_id in source_ids}
        for intermediate_id in collection.get_items(self['intermediate'], sort=bool(self['intermediatetitle'])):
            intermediate_item = collection.get_item(intermediate_id)

            potential_source_ids = set()
            for reverse_rel in links_with_relationships[0]:
                potential_source_ids.update(intermediate_item.yield_targets(reverse_rel))
            # apply :source: filter
            potential_source_ids = potential_source_ids.intersection(source_ids)

            potential_target_ids = set()
            for forward_rel in links_with_relationships[1]:
                potential_target_ids.update(intermediate_item.yield_targets(forward_rel))
            # apply :target: filter
            actual_targets = []
            for target_ids in targets_with_ids:
                linked_target_ids = potential_target_ids.intersection(target_ids)
                actual_targets.append(set(collection.get_item(id_) for id_ in linked_target_ids))

            self._store_targets(source_to_links_map, potential_source_ids, actual_targets, intermediate_item)
        return source_to_links_map

    @staticmethod
    def _store_targets(source_to_links_map, source_ids, targets, intermediate_item):
        """ Extends given mapping with target IDs per target as value for each source ID as key

        Args:
            source_to_links_map (dict): Mapping of source IDs as key with as value a mapping of intermediate items to
                the list of sets of target IDs per target
            source_ids (set): Source IDs to store targets for
            targets (list): List of linked target items (set) per target
            intermediate_item (TraceableItem): Intermediate item that links the given source items to the given target
                items
        """
        for source_id in source_ids:
            if source_id not in source_to_links_map:
                source_to_links_map[source_id] = {}
            source_to_links_map[source_id][intermediate_item] = targets

    def _store_row_with_intermediate(self, linked_items, rows, source, empty_right_cells, *args):
        """ Stores a row for a source, linking targets via one or all intermediates

        Args:
            linked_items (dict): Mapping of one or all intermediate IDs to the list of sets of target items per target
            rows (Rows): Rows namedtuple object to extend
            source (TraceableItem): Source item
            empty_right_cells (list): List of empty lists to fill with intermediates items, followed by target items
        """
        right_cells = deepcopy(empty_right_cells)
        self.add_all_targets(right_cells, linked_items)
        self._store_data(rows, source, right_cells, *args)

    def _store_data(self, rows, source, right_cells, covered, app):
        """ Stores the data in one or more rows in the given Rows object.

        Note that merging and removing cells happens in a later stage.

        Args:
            rows (Rows): Rows namedtuple object to extend
            source (TraceableItem|nodes.paragraph): Traceable source item or paragraph with link to it
            right_cells (list): List of lists with intermediate or target items or paragraphs with a link to them
            covered (bool): True if the row shall be stored in the covered attribute, False for uncovered attribute
            app (sphinx.application.Sphinx): Sphinx application object
        """
        source_attribute_cells = self._create_cells_for_info_cols(source, self['sourcecolumns'], app)
        has_intermediate = bool(self['intermediate'])
        intermediate_items = []
        if has_intermediate:
            intermediate_items = right_cells.pop(0)
        targets_per_target = right_cells

        new_rows = []
        number_of_rows = 1
        if self['splittargets']:
            number_of_rows = max([1] + [len(targets) for targets in targets_per_target])
        for row_idx in range(number_of_rows):
            row = nodes.row()

            # source
            row += self._create_cell_for_items([source], app)
            # source columns: attributes and extra relations
            for cell in source_attribute_cells:
                row += copy(cell)
            # intermediate
            if has_intermediate:
                if intermediate_items:
                    row += self._create_cell_for_items(intermediate_items, app)
                else:
                    row += nodes.entry('')
            # targets
            for target_items in targets_per_target:
                items = [nodes.paragraph('')]
                if number_of_rows == 1 and target_items:
                    items = target_items
                elif row_idx < len(target_items):
                    items = [target_items[row_idx]]
                items.sort(key=natsort_key)
                row += self._create_cell_for_items(items, app)
            # target columns: attributes and extra relations
            target_attribute_cells = []
            if self['targetcolumns']:
                if targets_per_target[-1]:
                    target_item = targets_per_target[-1][row_idx]
                else:
                    target_item = nodes.paragraph('')
                target_attribute_cells = self._create_cells_for_info_cols(target_item, self['targetcolumns'], app)
            row += target_attribute_cells

            new_rows.append(row)

        if covered:
            rows.counters[0] += 1
            rows.covered.extend(new_rows)
            rows.sorted.extend(new_rows)
        else:
            rows.counters[1] += 1
            rows.uncovered.extend(new_rows)
            rows.sorted.extend(new_rows)

    def _add_target_items(self, target_cells, target_items):
        """ Stores target items after filtering by target option.

        Returns whether the source has been covered or not.

        Args:
            target_cells (list): List of empty lists to fill
            target_items (list): List of potential target items

        Returns:
            bool: True if a target item has been stored, False otherwise
        """
        covered = False
        for idx, target_regex in enumerate(self['target']):
            for target in target_items:
                if target_regex and target_regex.match(target.identifier):
                    target_cells[idx].append(target)
                    covered = True
        return covered

    def _create_cell_for_items(self, cell_data, app):
        """ Creates a cell with one or more links, creating the link first in case a traceable item is given.

        Args:
            cell_data (list): List of nodes and/or TraceableItems to add as links to the cell
            app (sphinx.application.Sphinx): Sphinx application object

        Returns:
            nodes.entry: Cell filled with one or more links to items
        """
        cell = nodes.entry('')
        for entry in cell_data:
            if isinstance(entry, nodes.Node):
                cell += entry
            else:
                cell += self.make_internal_item_ref(app, entry.identifier)
        return cell

    def _create_cells_for_info_cols(self, item, values, app):
        """ Creates a cell with the item's attribute value for each attribute in the given list.

        Args:
            item (TraceableItem): TraceableItem instance
            values (list): List of attributes and/or relationships (str)
            app: Sphinx' application object to use.

        Returns:
            list[nodes.entry]: Cells filled with attribute values for the given item
        """
        cells = []
        for value in values:
            if value in TraceableItem.defined_attributes:
                cells.append(self._create_cell_for_attribute(item, value))
            else:
                cells.append(self._create_cell_for_relation(item, value, app))
        return cells

    @staticmethod
    def _create_cell_for_attribute(item, attribute):
        """ Creates a cell with the item's attribute value for the given attribute.

        Args:
            item (TraceableItem): TraceableItem instance
            attribute (str): Attribute for which to get the value from the given item

        Returns:
            nodes.entry: Cell filled with attribute value for the given item
        """
        cell = nodes.entry('')
        if not isinstance(item, nodes.paragraph):
            attribute_value = item.get_attribute(attribute)
            cell += nodes.paragraph('', attribute_value)
        return cell

    def _create_cell_for_relation(self, item, relation, app):
        """ Creates a cell with linked items via the given relation.

        Args:
            item (TraceableItem): TraceableItem instance
            relation (str): Relation for which to get the linked items
            app: Sphinx' application object to use.

        Returns:
            nodes.entry: Cell filled with attribute value for the given item
        """
        cell = nodes.entry('')
        if not isinstance(item, nodes.paragraph):
            for linked_item in item.yield_targets_sorted(relation):
                if self.is_relation_external(relation):
                    cell += self.make_external_item_ref(app, linked_item, relation)
                else:
                    cell += self.make_internal_item_ref(app, linked_item)
        return cell

    def _check_coverage(self, percentage):
        """ Checks the coverage percentage using the configured expression

        A warning is reported when the configured expression is invalid or if the evaluation returns False.

        Args:
            percentage (float): Coverage percentage
        """
        if self['coverage']:
            pattern = r'([><]=?|==|!=)\s*[\d\./]+'
            if self.COVERAGE_REGEX.fullmatch(self['coverage']):
                expression = '{} {}'.format(percentage, self['coverage'])
                if not eval(expression):  # pylint: disable=eval-used
                    report_warning('Item-matrix with title {!r} has bad coverage: {} evaluates to False'
                                   .format(self['title'], expression),
                                   docname=self['document'],
                                   lineno=self['line'])
            else:
                report_warning('Expected value for coverage option to fully match regex {}; got {!r}'
                               .format(pattern, self['coverage']),
                               docname=self['document'],
                               lineno=self['line'])


class ItemMatrixDirective(TraceableBaseDirective):
    """
    Directive to generate a matrix of item cross-references, based on
    a given set of relationship types.

    Syntax::

      .. item-matrix:: title
         :target: regexp ...
         :source: regexp
         :intermediate: regexp
         :<<attribute>>: regexp
         :targettitle: Target column header(s)
         :sourcetitle: Source column header
         :intermediatetitle: Intermediate column header
         :type: <<relationship>> ...
         :sourcetype: <<relationship>> ...
         :sourcecolumns: <<attribute>> ...
         :targetcolumns: <<attribute>> ...
         :hidesource:
         :hidetarget:
         :splitintermediates:
         :splittargets:
         :group: top | bottom
         :onlycovered:
         :onlyuncovered:
         :stats:
         :coverage: Evaluation, e.g. >=95
         :nocaptions:
         :onlycaptions:
         :hidetitle:
         :filtertarget:
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
        'sourcecolumns': directives.unchanged,  # attributes separated by space
        'targetcolumns': directives.unchanged,  # attributes separated by space
        'hidesource': directives.flag,
        'hidetarget': directives.flag,
        'splitintermediates': directives.flag,
        'splittargets': directives.flag,
        'group': group_choice,
        'onlycovered': directives.flag,
        'onlyuncovered': directives.flag,
        'coveredintermediates': directives.flag,
        'stats': directives.flag,
        'coverage': directives.unchanged,
        'nocaptions': directives.flag,
        'onlycaptions': directives.flag,
        'hidetitle': directives.flag,
        'filtertarget': directives.flag,
    }
    # Content disallowed
    has_content = False

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        node = ItemMatrix('')
        node['document'] = env.docname
        node['line'] = self.lineno

        if self.options.get('class'):
            node.get('classes').extend(self.options.get('class'))

        self.process_title(node, 'Traceability matrix of items')

        self.add_found_attributes(node, is_pattern=True)

        self.process_options(
            node,
            {
                'target':            {'default': [''], 'is_pattern': True},
                'intermediate':      {'default': '', 'is_pattern': True},
                'source':            {'default': '', 'is_pattern': True},
                'targettitle':       {'default': ['Target'], 'delimiter': ','},
                'sourcetitle':       {'default': 'Source'},
                'intermediatetitle': {'default': ''},
                'type':              {'default': ''},
                'sourcetype':        {'default': []},
                'coverage':          {'default': ''},
            },
        )

        if node['intermediate'] and ' | ' not in node['type']:
            raise TraceabilityException("The :intermediate: option is used, expected at least two relationships "
                                        "separated by ' | ' in the :type: option; got {!r}".format(node['type']),
                                        docname=env.docname)
        if ' | ' in node['type'] and not node['intermediate']:
            raise TraceabilityException("The value of the :type: option contains the '|' character,  but the option "
                                        ":intermediate: is missing for item-matrix {!r}".format(node['title']),
                                        docname=env.docname)

        # Process ``group`` option, given as a string that is either top or bottom or empty ().
        node['group'] = self.options.get('group', '')

        number_of_targets = len(node['target'])
        number_of_targettitles = len(node['targettitle'])
        if number_of_targets != number_of_targettitles:
            raise TraceabilityException(
                "Item-matrix directive should have the same number of values for the options 'target' and "
                "'targettitle'. Got target: {targets!r} and targettitle: {titles!r}"
                .format(targets=self.options['target'], titles=self.options['targettitle']),
                docname=env.docname)

        if node['type']:
            self.check_relationships(node['type'].replace(' | ', ' ').split(' '), env)
        self.check_relationships(node['sourcetype'], env)
        self.add_attributes_and_relations(node, 'sourcecolumns', app.env.traceability_collection.relations)
        self.add_attributes_and_relations(node, 'targetcolumns', app.env.traceability_collection.relations)
        if number_of_targets > 1 and node['targetcolumns']:
            node['targetcolumns'] = []
            raise TraceabilityException(
                "Item-matrix {!r} cannot combine 'targetcolumns' with more than one 'target'; "
                "ignoring 'targetcolumns' option".format(node['title']),
                docname=env.docname)

        self.check_option_presence(node, 'hidesource')
        self.check_option_presence(node, 'hidetarget')
        self.check_option_presence(node, 'splitintermediates')
        self.check_option_presence(node, 'splittargets')
        self.check_option_presence(node, 'onlycovered')
        self.check_option_presence(node, 'onlyuncovered')
        self.check_option_presence(node, 'coveredintermediates')
        self.check_option_presence(node, 'stats')
        self.check_option_presence(node, 'hidetitle')
        self.check_option_presence(node, 'filtertarget')

        if node['onlycovered'] and node['onlyuncovered']:
            raise TraceabilityException(
                "Item-matrix directive cannot combine 'onlycovered' with 'onlyuncovered' flag",
                docname=env.docname)

        if node['targetcolumns']:
            node['splittargets'] = True

        self.check_caption_flags(node, app.config.traceability_matrix_no_captions)

        return [node]
