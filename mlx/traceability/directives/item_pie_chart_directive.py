"""Module for the item-piechart directive"""
import operator
import re
from hashlib import sha256
from itertools import zip_longest
from os import environ, mkdir, path

from docutils import nodes
from docutils.parsers.rst import directives
import matplotlib as mpl
if not environ.get('DISPLAY'):
    mpl.use('Agg')
import matplotlib.pyplot as plt  # pylint: disable=wrong-import-order
from natsort import natsorted
from sphinx.builders.latex import LaTeXBuilder

from ..traceability_exception import report_warning
from ..traceable_base_directive import TraceableBaseDirective
from ..traceable_base_node import TraceableBaseNode
from ..traceable_item import TraceableItem


def pct_wrapper(sizes):
    """ Helper function for matplotlib which returns the percentage and the absolute size of the slice.

    Args:
        sizes (list): List containing the amount of elements per slice.
    """
    def make_pct(pct):
        absolute = int(round(pct / 100 * sum(sizes)))
        return "{:.0f}%\n({:d})".format(pct, absolute)
    return make_pct


class Match:
    """ Class for storing the label and targets for a single source item """
    def __init__(self, label):
        self.label = label
        self.targets = {}

    @property
    def targets_iter(self):
        """ iter(tuple): generator that yields a target and corresponding nested targets, natural sorting order """
        for target in natsorted(self.targets, key=operator.attrgetter('identifier')):
            yield target, natsorted(self.targets[target], key=operator.attrgetter('identifier'))

    def add_target(self, target):
        """ Add a target item

        Args:
            target (TraceableItem): Target item
        """
        if target not in self.targets:
            self.targets[target] = []

    def add_nested_target(self, target, nested_target):
        """ Add a nested target item belonging to a target item

        Args:
            target (TraceableItem): Target item
            target (TraceableItem): Nested target item
        """
        self.targets[target].append(nested_target)


class ItemPieChart(TraceableBaseNode):
    '''Pie chart on documentation items'''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = None
        self.source_relationships = []
        self.target_relationships = []
        self.relationship_to_string = {}
        self.priorities = []  # default priority order is 'uncovered', 'covered', 'executed'
        self.labels = []
        self.nested_target_regex = re.compile('')
        self.matches = {}  # source_id (str): Match

    def perform_replacement(self, app, collection):
        """
        Very similar to item-matrix: but instead of creating a table, the empty cells in the right column are counted.
        Generates a pie chart with coverage percentages. Only items matching regexp in ``id_set`` option shall be
        included.

        Args:
            app: Sphinx application object to use.
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        env = app.builder.env
        top_node = self.create_top_node(self['title'], hide_title=self['hidetitle'])
        self.collection = collection
        self.source_relationships = self['sourcetype'] if self['sourcetype'] else self.collection.iter_relations()
        self.target_relationships = self['targettype'] if self['targettype'] else self.collection.iter_relations()
        self.relationship_to_string = app.config.traceability_relationship_to_string
        self._store_labels()
        self._set_nested_target_regex()
        target_regex = re.compile(self['id_set'][1])
        for source_id in self.collection.get_items(self['id_set'][0], self['filter-attributes']):
            source_item = self.collection.get_item(source_id)
            # placeholders don't end up in any item-piechart (less duplicate warnings for missing items)
            if source_item.is_placeholder:
                continue
            self.matches[source_id] = Match(self.priorities[0])  # default is "uncovered"
            self.loop_relationships(source_id, source_item, self.source_relationships, target_regex,
                                    self._match_covered)

        if self['colors'] and len(self['colors']) < len(self.priorities):
            report_warning("item-piechart can contain up to {} slices but only {} colors have been provided: some "
                           "colors may be reused".format(len(self.priorities), len(self['colors'])),
                           self['document'], self['line'])
        data, statistics = self._prepare_labels_and_values([x.label for x in self.matches.values()],
                                                           self['colors'])
        if data['labels']:
            top_node += self.build_pie_chart(data['sizes'], data['labels'], data['colors'], env)

        if self['stats']:
            p_node = nodes.paragraph()
            p_node += nodes.Text(statistics)
            top_node += p_node

        if self['matrix'] and data['labels']:
            top_node += self.build_table(app)
        self.replace_self(top_node)

    def _relationships_to_labels(self, relationships):
        """ Converts the list of relationships to a list to the corresponding labels.

        The human-readable version of the reverse relationship will be used as label.

        Args:
            relationships (list): List of relationships (str)

        Returns:
            list: Labels to use
        """
        labels = []
        for relationship in relationships:
            reverse_relationship = self.collection.get_reverse_relation(relationship)
            labels.append(self.relationship_to_string[reverse_relationship].lower())
        return labels

    def _store_labels(self):
        """ Stores all labels """
        self.priorities = list(self['label_set'])
        self.labels = list(self['label_set'])

        if self['splitsourcetype'] and self['sourcetype']:
            sourcetype_labels = self._relationships_to_labels(self['sourcetype'])
            self.priorities.extend(sourcetype_labels)
            self.labels.extend(sourcetype_labels)

        custom_labels = []
        if self['attr_values']:
            custom_labels.extend([val.lower() for val in self['attr_values']])
        elif self['targettype']:
            custom_labels.extend(self._relationships_to_labels(self['targettype']))
        self.priorities.extend(reversed(custom_labels))
        self.labels.extend(custom_labels)

    def _set_nested_target_regex(self):
        """ Sets the ``nested_target_regex`` if a third item ID in the id_set option is given. """
        if len(self['id_set']) > 2:
            self.nested_target_regex = re.compile(self['id_set'][2])

    def _store_linked_label(self, top_source_id, label):
        """ Stores the label in ``matches`` for the given item ID if it has a higher priority and the currently stored
        label is different from 'executed'.

        Args:
            top_source_id (str): Identifier of the top source item, e.g. requirement identifier.
            label (str): Label to store if it has a higher priority than the one that has been stored.
        """
        stored_label = self.matches[top_source_id].label
        if stored_label not in (label, self.priorities[2]):
            # store different label if it has a higher priority
            stored_priority = self.priorities.index(stored_label)
            latest_priority = self.priorities.index(label)
            if latest_priority > stored_priority:
                self.matches[top_source_id].label = label

    def loop_relationships(self, top_source_id, source_item, relationships, regex, match_function):
        """
        Loops through the relationships and for each relationship it loops through the matches that have been
        found for the source item. If the matched item is not a placeholder and matches to the specified regular
        expression object, the specified function is called with the matched item as a parameter.

        Args:
            top_source_id (str): Item identifier of the top source item.
            source_item (TraceableItem): Traceable item to be used as a source for the relationship search.
            relationships (list): List of relationships to consider.
            regex (re.Pattern): Compiled regex pattern to be used on items that have a relationship to the source
                item.
            match_function (func): Function to be called when the regular expression hits.

        Returns:
            bool: True when the source item has at least one item linked to it via one of the given relationships
                and its ID was a match for the given regex; False otherwise
        """
        has_valid_target = False
        consider_nested_targets = True
        for relationship in relationships:
            for target_id in source_item.yield_targets(relationship):
                target_item = self.collection.get_item(target_id)
                # placeholders don't end up in any item-piechart (less duplicate warnings for missing items)
                if not target_item or target_item.is_placeholder:
                    continue
                if regex.match(target_id):
                    has_valid_target = True
                    if source_item.identifier == top_source_id:
                        self.matches[top_source_id].add_target(target_item)
                    else:
                        self.matches[top_source_id].add_nested_target(source_item, target_item)
                    if consider_nested_targets is False:  # at least one target doesn't have a nested target
                        _ = match_function(top_source_id, target_item, relationship, consider_nested_targets=False)
                    else:
                        consider_nested_targets = match_function(top_source_id, target_item, relationship)
        return has_valid_target and consider_nested_targets

    def _match_covered(self, top_source_id, nested_source_item, relationship, consider_nested_targets=True):
        """
        Sets the appropriate label when the top-level relationship is accounted for. If the <<attribute>> option is
        used for labeling, it loops through the target relationships, this time with the matched item as the source.
        Otherwise, if the targettype option is used, those relationships will be used as labels. If no nested
        target is found or `nested_source_item` is None, the top-level relationship is used to determine the label.

        Args:
            top_source_id (str): Identifier of the top source item, e.g. requirement identifier.
            nested_source_item (None/TraceableItem): Nested traceable item to be used as a source for looping through
                its relationships, e.g. a test item.
            relationship (str): Relationship from top-level source item to the target item
            consider_nested_targets (bool): False to ignore any nested targets that are found for labeling/statistics.

        Returns:
            bool: False if no valid target could be found for `nested_source_item` or it was None; True otherwise
        """
        has_nested_target = False
        if nested_source_item and self.nested_target_regex.pattern:
            if self['targettype'] and not self['attr_values']:
                match_function = self._match_by_type
            else:
                match_function = self._match_attribute_values
            has_nested_target = self.loop_relationships(
                top_source_id, nested_source_item, self.target_relationships, self.nested_target_regex, match_function)
        if not has_nested_target or not consider_nested_targets:
            if self['splitsourcetype'] and self['sourcetype']:
                self._match_by_type(top_source_id, None, relationship)
            else:
                self.matches[top_source_id].label = self.priorities[1]  # default is "covered"
        return has_nested_target and consider_nested_targets

    def _match_by_type(self, top_source_id, _, relationship, **__):
        """ Links the reverse of the highest priority relationship of nested relations to the top source id.

        Args:
            top_source_id (str): Identifier of the top source item, e.g. requirement identifier.
            relationship (str): Relationship with ``nested_target_item`` as target
        """
        reverse_relationship = self.collection.get_reverse_relation(relationship)
        reverse_relationship_str = self.relationship_to_string[reverse_relationship].lower()
        self._store_linked_label(top_source_id, reverse_relationship_str)
        return True

    def _match_attribute_values(self, top_source_id, nested_target_item, *_, **__):
        """ Links the highest priority attribute value of nested relations to the top source id.

        This function is only called when the <<attribute>> option is used. It gets the attribute value from the nested
        target item and stores it as value in the dict `linked_labels` with the top source id as key, but only if
        the priority of the attribute value is higher than what's already been stored.

        Args:
            top_source_id (str): Identifier of the top source item, e.g. requirement identifier.
            nested_target_item (TraceableItem): Traceable item with ID that matched for ``nested_target_regex``:
                its <<attribute>> value needs to be considered
        """
        # case-insensitivity
        attribute_value = nested_target_item.get_attribute(self['attribute']).lower()
        if attribute_value not in self.priorities:
            attribute_value = self.priorities[2]  # default is "executed"
        self._store_linked_label(top_source_id, attribute_value)
        return True

    def _prepare_labels_and_values(self, discovered_labels, colors):
        """ Keeps case-sensitivity of :<<attribute>>: arguments in labels and calculates slice size based on the
        highest-priority label for each relevant item.

        Args:
            discovered_labels (list): List of labels with the highest priority for each relevant item.
            colors (list): List of colors in the order as they are defined

        Returns:
            (dict) Dictionary containing the slice labels as keys and slice sizes (int) as values.
            (str) Coverage statistics.
        """
        # initialize dictionary for each possible value, and count label occurences
        ordered_colors = colors[:len(self.labels)]
        pie_data = {
            'labels': self.labels,
            'sizes': [0] * len(self.labels),
            'colors': ordered_colors,
        }
        labels = pie_data['labels']
        for label in discovered_labels:
            pie_data['sizes'][labels.index(label)] += 1

        # get statistics before removing any labels with value 0
        statistics = self._get_statistics(pie_data['sizes'][0], len(discovered_labels))
        # removes labels with count value equal to 0 and the corresponding configured color
        for idx in reversed(range(len(labels))):
            if pie_data['sizes'][idx] == 0:
                del pie_data['labels'][idx]
                del pie_data['sizes'][idx]
                if len(pie_data['colors']) > idx:
                    del pie_data['colors'][idx]

        for priority in self['attr_values']:
            priority_lowercase = priority.lower()
            if priority != priority_lowercase and priority_lowercase in pie_data['labels']:
                index = pie_data['labels'].index(priority_lowercase)
                pie_data['labels'][index] = priority
        return pie_data, statistics

    @staticmethod
    def _get_statistics(count_uncovered, count_total):
        """ Returns the coverage statistics based in the number of uncovered items and total number of items.

        Args:
            count_uncovered (int): The number of uncovered items.
            count_total (int): The total number of items.

        Returns:
            (str) Coverage statistics in string representation.
        """
        count_covered = count_total - count_uncovered
        try:
            percentage = int(100 * count_covered / count_total)
        except ZeroDivisionError:
            percentage = 0
        return 'Statistics: {cover} out of {total} covered: {pct}%'.format(cover=count_covered,
                                                                           total=count_total,
                                                                           pct=percentage,)

    def build_pie_chart(self, sizes, labels, colors, env):
        """
        Builds and returns image node containing the pie chart image.

        Args:
            sizes (list): List of slice sizes (int)
            labels (list): List of labels (str)
            colors (list): List of colors (str); if empty, default colors will be used
            env (sphinx.environment.BuildEnvironment): Sphinx' build environment.

        Returns:
            (nodes.image) Image node containing the pie chart image.
        """
        mpl.rcParams['font.sans-serif'] = ['Lato', 'DejaVu Sans']
        explode = self._get_explode_values(labels, self['label_set'])
        if not colors:
            colors = None
        fig, axes = plt.subplots(subplot_kw=dict(aspect="equal"))
        _, texts, autotexts = axes.pie(sizes, explode=explode, labels=labels, autopct=pct_wrapper(sizes),
                                       startangle=90, colors=colors)
        folder_name = path.join(env.app.srcdir, '_images')
        if not path.exists(folder_name):
            mkdir(folder_name)
        hash_string = str(colors) + str(texts) + str(autotexts)
        hash_value = sha256(hash_string.encode()).hexdigest()  # create hash value based on chart parameters
        image_format = 'pdf' if isinstance(env.app.builder, LaTeXBuilder) else 'svg'
        rel_file_path = path.join('_images', 'piechart-{}.{}'.format(hash_value, image_format))
        if rel_file_path not in env.images:
            out_path = path.join(env.app.srcdir, rel_file_path)
            fig.savefig(out_path, format=image_format, bbox_inches='tight', transparent=True)
            env.images[rel_file_path] = ['_images', path.split(rel_file_path)[-1]]  # store file name in build env
        plt.close(fig)

        image_node = nodes.image()
        image_node['classes'].append('pie-chart')
        image_node['uri'] = rel_file_path
        image_node['candidates'] = '*'  # look at uri value for source path, relative to the srcdir folder
        return image_node

    @staticmethod
    def _get_explode_values(labels, label_set):
        """ Gets a list of values indicating how far to detach each slice of the pie chart

        Only the first configured state gets detached slightly; default is "uncovered"

        Args:
            labels (list): Slice labels (str)
            label_set (list): All labels as configured by the label_set option

        Returns:
            list: List of numbers for each slice indicating how far to detach it
        """
        explode = [0] * len(labels)
        uncovered_label = label_set[0]
        if uncovered_label in labels:
            uncovered_index = labels.index(uncovered_label)
            explode[uncovered_index] = 0.05
        return explode

    def _determine_headings(self, app):
        """Determine the table headings with either custom titles and/or the regexp patterns from id_set.

        Note: If not enough custom titles are provided, the regexp patterns are used for completion.

        Return:
            list[nodes.entry]: Header cells
            bools: True to add a fourth column with relevant info about each nested target item, False otherwise
        """
        add_result_column = bool(self.nested_target_regex.pattern) and \
            (bool(self['attribute']) or bool(self['targettype']))
        titles = []
        for title, pattern in zip_longest(self['matrixtitles'], self['id_set'], fillvalue=None):
            if title is not None:
                titles.append(nodes.paragraph('', title))
            else:
                titles.append(nodes.paragraph('', pattern))
        if add_result_column and len(titles) < 4:
            if self['attribute']:
                titles.append(self.make_attribute_ref(app, self['attribute']))
            else:
                titles.append(nodes.paragraph('', ''))  # only targettype option used; cannot assume a suitable title
        headings = [nodes.entry('', title) for title in titles]
        return headings, add_result_column

    def build_table(self, app):
        """ Builds a table node for the 'matrix' option

        The labels of the pie chart (or a subset) are used as subheaders and a way to group the source items.
        Besides that, the table is similar to the item-matrix directive with the 'splitintermediates' flag enabled.

        Args:
            app (sphinx.application.Sphinx): Sphinx application object

        Returns:
            nodes.table: Table node
        """
        table = nodes.table()
        if self['matrix'] == ['']:
            self['matrix'] = self.labels
        self['nocaptions'] = True
        table = nodes.table()
        if self.get('classes'):
            table.get('classes').extend(self.get('classes'))
        # Column and heading setup
        headings, add_result_column = self._determine_headings(app)
        number_of_columns = len(headings)
        tgroup = nodes.tgroup()
        tgroup += [nodes.colspec(colwidth=5) for _ in range(number_of_columns)]
        tgroup += nodes.thead('', nodes.row('', *headings))
        table += tgroup
        # Table body
        tbody = nodes.tbody()
        tgroup += tbody
        for label in self['matrix']:
            row = nodes.row()
            subheader = nodes.entry('', nodes.strong('', label), morecols=max(0, number_of_columns-1))
            subheader.get('classes').append('centered')
            row += subheader
            tbody += row
            for source_id, match in {k: v for k, v in self.matches.items() if v.label.lower() == label.lower()}.items():
                source = self.collection.get_item(source_id)
                tbody += self._rows_per_source(source, match, add_result_column, app)
        return table

    def _rows_per_source(self, source, match, add_result_column, app):
        """ Builds a list of rows for the given source item

        Args:
            source (TraceableItem): Source item
            match (Match): The corresponding Match instance
            add_result_column (bool): True to display the used attribute value or relationship to the right of each
                nested target
            app (sphinx.application.Sphinx): Sphinx application object

        Returns:
            list: List of rows to add to the table body
        """
        rows = []
        source_row = nodes.row()
        nr_rows_per_target = (max(1, len(nested_targets)) for nested_targets in match.targets.values())
        morerows = max(0, sum(nr_rows_per_target)-1)
        source_row += self._create_cell_for_items([source], app, morerows=morerows)
        if match.targets:
            row_without_targets = source_row
            for target, nested_targets in match.targets_iter:
                morerows = max(0, len(nested_targets)-1)
                row_without_targets += self._create_cell_for_items([target], app, morerows=morerows)
                if self.nested_target_regex.pattern:
                    for nested_target in nested_targets:
                        row_without_targets += self._create_cell_for_items([nested_target], app)
                        if add_result_column:
                            row_without_targets += self.generate_result_cell(target, nested_target)
                        if nested_target != nested_targets[-1]:
                            rows.append(row_without_targets)
                            row_without_targets = nodes.row()
                    if not nested_targets:
                        row_without_targets += nodes.entry('')
                        if add_result_column:
                            row_without_targets += nodes.entry('')
                rows.append(row_without_targets)
                row_without_targets = nodes.row()
        else:
            source_row += nodes.entry('')
            if self.nested_target_regex.pattern:
                source_row += nodes.entry('')
                if add_result_column:
                    source_row += nodes.entry('')
            rows.append(source_row)
        return rows

    def generate_result_cell(self, target, nested_target):
        """Generate the cell for the fourth column.

        It should contain either the relevant attribute value of the nested target item,
        or the pie chart label associated with the relationship from the nested target to the target item.

        Args:
            target (TraceableItem): The target item
            nested_target (TraceableItem): The nested target item
        """
        result_cell = nodes.entry('')
        if self['attribute']:
            entry_node = self._create_cell_for_attribute(nested_target, self['attribute'])
            p_node = entry_node.children[0]
            result_cell += p_node
        elif self['targettype']:
            labels = self._relationships_to_labels(self['targettype'])
            for targettype, label in zip(self['targettype'], labels):
                if nested_target.identifier in target.iter_targets(targettype, sort=False):
                    result_cell += nodes.paragraph('', nodes.Text(label))
                    break
        return result_cell


class ItemPieChartDirective(TraceableBaseDirective):
    """
    Directive to generate a pie chart for coverage of item cross-references.

    Syntax::

      .. item-piechart:: title
         :id_set: source_regexp target_regexp (nested_target_regexp)
         :label_set: uncovered, covered(, executed)
         :<<attribute>>: error, fail, pass ...
         :<<attribute>>: regexp
         :colors: <<color>> ...
         :sourcetype: <<relationship>> ...
         :targettype: <<relationship>> ...
         :splitsourcetype:
         :hidetitle:
         :stats:
         :matrix: uncovered, covered, executed, error,fail,pass
    """
    # Optional argument: title (whitespace allowed)
    optional_arguments = 1
    # Options
    option_spec = {
        'class': directives.class_option,
        'id_set': directives.unchanged,
        'label_set': directives.unchanged,
        'colors': directives.unchanged,
        'sourcetype': directives.unchanged,
        'targettype': directives.unchanged,
        'splitsourcetype': directives.flag,
        'hidetitle': directives.flag,
        'stats': directives.flag,
        'matrix': directives.unchanged,
        'matrixtitles':  directives.unchanged,
    }
    # Content disallowed
    has_content = False

    def run(self):
        """ Processes the contents of the directive. """
        env = self.state.document.settings.env

        node = ItemPieChart('')
        node['document'] = env.docname
        node['line'] = self.lineno

        self.process_title(node)
        self._process_id_set(node)
        self._process_label_set(node)
        self._process_attribute(node)
        self.add_found_attributes(node)
        self.process_options(
            node,
            {
                'colors': {'default': []},
                'sourcetype': {'default': []},
                'targettype': {'default': []},
                'matrix': {'default': [], 'delimiter': ','},
                'matrixtitles': {'default': [], 'delimiter': ','},
            }
        )
        self.check_relationships(node['sourcetype'], env)
        self.check_relationships(node['targettype'], env)
        self.check_option_presence(node, 'splitsourcetype')
        self.check_option_presence(node, 'hidetitle')
        self.check_option_presence(node, 'stats')

        if node['splitsourcetype'] and not node['sourcetype']:
            report_warning('item-piechart: The splitsourcetype flag must not be used when the sourcetype option is '
                           'unused; disabling splitsourcetype.', node['document'], node['line'])
            node['splitsourcetype'] = False

        return [node]

    def _process_id_set(self, node):
        """ Processes id_set option. At least two arguments are required. Otherwise, a warning is reported. """
        if 'id_set' in self.options and len(self.options['id_set'].split()) >= 2:
            self._warn_if_comma_separated('id_set', node['document'])
            node['id_set'] = self.options['id_set'].split()
            if len(node['id_set']) < 3 and self.options.get('targettype'):
                report_warning('item-piechart: the targettype option is only viable with an id_set with 3 '
                               'arguments.', node['document'], node['line'])
        else:
            node['id_set'] = []
            report_warning('item-piechart: Expected at least two arguments in id_set.',
                           node['document'],
                           node['line'])

    def _process_label_set(self, node):
        """ Processes label_set option. If not (fully) used, default labels are used. """
        default_labels = ['uncovered', 'covered', 'executed']
        if 'label_set' in self.options:
            node['label_set'] = [x.strip(' ') for x in self.options['label_set'].split(',')]
            if len(node['label_set']) != len(node['id_set']):
                node['label_set'].extend(
                    default_labels[len(node['label_set']):len(node['id_set'])])
        else:
            id_amount = len(node['id_set'])
            node['label_set'] = default_labels[:id_amount]  # default labels

    def _process_attribute(self, node):
        """
        Processes the <<attribute>> option. Attribute data is a comma-separated list of attribute values.
        A warning is reported when this option is given while the id_set does not contain 3 IDs.
        """
        node['attribute'] = ''
        node['attr_values'] = []
        for attr in set(TraceableItem.defined_attributes) & set(self.options):
            if ',' not in self.options[attr]:
                continue  # this :<<attribute>>: is meant for filtering
            if len(node['id_set']) == 3:
                node['attribute'] = attr
                node['attr_values'] = [x.strip(' ') for x in self.options[attr].split(',') if x]
                del self.options[attr]
            else:
                report_warning('item-piechart: The <<attribute>> option is only viable with an id_set with 3 '
                               'arguments.',
                               node['document'],
                               node['line'],)
            break  # only one <<attribute>> option is valid
