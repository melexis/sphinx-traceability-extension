import re
import warnings
from hashlib import sha256
from os import environ, mkdir, path

from docutils import nodes
from docutils.parsers.rst import directives
import matplotlib as mpl
if not environ.get('DISPLAY'):
    mpl.use('Agg')
import matplotlib.pyplot as plt  # pylint: disable=wrong-import-order
from sphinx.builders.latex import LaTeXBuilder

from mlx.traceability_exception import report_warning
from mlx.traceable_base_directive import TraceableBaseDirective
from mlx.traceable_base_node import TraceableBaseNode
from mlx.traceable_item import TraceableItem


def pct_wrapper(sizes):
    """ Helper function for matplotlib which returns the percentage and the absolute size of the slice.

    Args:
        sizes (list): List containing the amount of elements per slice.
    """
    def make_pct(pct):
        absolute = int(round(pct / 100 * sum(sizes)))
        return "{:.0f}%\n({:d})".format(pct, absolute)
    return make_pct


class ItemPieChart(TraceableBaseNode):
    '''Pie chart on documentation items'''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = None
        self.source_relationships = []
        self.target_relationships = []
        self.relationship_to_string = {}
        self.priorities = []  # default priority order is 'uncovered', 'covered', 'executed'
        self.nested_target_regex = re.compile('')
        self.linked_labels = {}  # source_id (str): attr_value/relationship_str (str)

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
        self._set_priorities()
        self._set_nested_target_regex()
        target_regex = re.compile(self['id_set'][1])
        for source_id in self.collection.get_items(self['id_set'][0], self['filter-attributes']):
            source_item = self.collection.get_item(source_id)
            # placeholders don't end up in any item-piechart (less duplicate warnings for missing items)
            if source_item.is_placeholder:
                continue
            self.linked_labels[source_id] = self.priorities[0]  # default is "uncovered"
            self.loop_relationships(source_id, source_item, self.source_relationships, target_regex,
                                    self._match_covered)

        data, statistics = self._prepare_labels_and_values(self.priorities,
                                                           list(self.linked_labels.values()),
                                                           self['colors'])
        if data['colors'] and len(data['colors']) < len(data['labels']):
            report_warning("item-piechart contains {} slices: {} color(s) will be reused"
                           .format(len(data['labels']), len(data['labels']) - len(data['colors'])),
                           self['document'], self['line'])
        p_node = nodes.paragraph()
        p_node += nodes.Text(statistics)
        if data['labels']:
            top_node += self.build_pie_chart(data['sizes'], data['labels'], data['colors'], env)
        top_node += p_node
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

    def _set_priorities(self):
        """ Initializes the priorities dictionary with labels as keys and priority numbers as values. """
        self.priorities = list(self['label_set'])

        if self['splitsourcetype'] and self['sourcetype']:
            self.priorities.extend(reversed(self._relationships_to_labels(self['sourcetype'])))

        if self['attr_values']:
            self.priorities.extend(reversed([val.lower() for val in self['attr_values']]))
        elif self['targettype']:
            self.priorities.extend(reversed(self._relationships_to_labels(self['targettype'])))

    def _set_nested_target_regex(self):
        """ Sets the ``nested_target_regex`` if a third item ID in the id_set option is given. """
        if len(self['id_set']) > 2:
            self.nested_target_regex = re.compile(self['id_set'][2])

    def _store_linked_label(self, top_source_id, label):
        """ Stores the label with the given item ID as key in ``linked_labels`` if it has a higher priority.

        Args:
            top_source_id (str): Identifier of the top source item, e.g. requirement identifier.
            label (str): Label to store if it has a higher priority than the one that has been stored.
        """
        if label != self.linked_labels[top_source_id]:
            # store different label if it has a higher priority
            stored_priority = self.priorities.index(self.linked_labels[top_source_id])
            latest_priority = self.priorities.index(label)
            if latest_priority > stored_priority:
                self.linked_labels[top_source_id] = label

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
                    if consider_nested_targets is False:  # at least one target doesn't have a nested target
                        _ = match_function(top_source_id, None, relationship)
                    else:
                        consider_nested_targets = match_function(top_source_id, target_item, relationship)
        return has_valid_target and consider_nested_targets

    def _match_covered(self, top_source_id, nested_source_item, relationship):
        """
        Sets the appropriate label when the top-level relationship is accounted for. If the <<attribute>> option is
        used for labeling, it loops through the target relationships, this time with the matched item as the source.
        Otherwise, if the targettype option is used, those relationships will be used as labels. If no nested
        target is found or `nested_source_item` is None, the top-level relationship is used to determine the label.

        Args:
            top_source_id (str): Identifier of the top source item, e.g. requirement identifier.
            nested_source_item (None/TraceableItem): Nested traceable item to be used as a source for looping through
                its relationships, e.g. a test item. If None, only the given `relationship` is taken into account.
            relationship (str): Relationship from top-level source item to the target item

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
        if not has_nested_target:
            if self['splitsourcetype'] and self['sourcetype']:
                self._match_by_type(top_source_id, None, relationship)
            else:
                self.linked_labels[top_source_id] = self.priorities[1]  # default is "covered"
        return has_nested_target

    def _match_by_type(self, top_source_id, _, relationship):
        """ Links the reverse of the highest priority relationship of nested relations to the top source id.

        Args:
            top_source_id (str): Identifier of the top source item, e.g. requirement identifier.
            nested_target_item (TraceableItem): Nested traceable item used as a target while looping through
                relationships, e.g. a test report item.
            relationship (str): Relationship with ``nested_target_item`` as target
        """
        reverse_relationship = self.collection.get_reverse_relation(relationship)
        reverse_relationship_str = self.relationship_to_string[reverse_relationship].lower()
        self._store_linked_label(top_source_id, reverse_relationship_str)
        return True

    def _match_attribute_values(self, top_source_id, nested_target_item, *_):
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

    def _prepare_labels_and_values(self, ordered_labels, discovered_labels, colors):
        """ Keeps case-sensitivity of :<<attribute>>: arguments in labels and calculates slice size based on the
        highest-priority label for each relevant item.

        Args:
            ordered_labels (list): List of unique labels (str), ordered by priority from low to high.
            discovered_labels (list): List of labels with the highest priority for each relevant item.
            colors (list): List of colors in the order as they are defined

        Returns:
            (dict) Dictionary containing the slice labels as keys and slice sizes (int) as values.
            (str) Coverage statistics.
        """
        # initialize dictionary for each possible value, and count label occurences
        ordered_colors = colors[:len(ordered_labels)]
        if len(colors) > 3:
            # reverse order for labels specified by :sourcetype: or :<<attribute>>: or :targettype:
            sourcetypes = len(self['sourcetype']) if self['splitsourcetype'] else 0
            ordered_colors[3:3+sourcetypes] = reversed(ordered_colors[3:3+sourcetypes])
            ordered_colors[3+sourcetypes:] = reversed(ordered_colors[3+sourcetypes:])

        pie_data = {
            'labels': ordered_labels,
            'sizes': [0] * len(ordered_labels),
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
            fig.savefig(path.join(env.app.srcdir, rel_file_path), format=image_format, bbox_inches='tight')
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

        if not node['stats']:
            warnings.warn('Pie chart statistics will not be displayed in mlx.traceability>=10 unless the stats flag '
                          'is provided.', FutureWarning)

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
