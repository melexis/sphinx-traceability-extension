from docutils import nodes
from docutils.parsers.rst import directives
from natsort import natsorted, natsort_keygen
from sphinx.builders.latex import LaTeXBuilder

from mlx.traceability import report_warning, TraceabilityException
from mlx.traceable_base_directive import TraceableBaseDirective
from mlx.traceable_base_node import TraceableBaseNode

natsort_key = natsort_keygen()


class ItemTree(TraceableBaseNode):
    '''Tree-view on documentation items'''

    def perform_replacement(self, app, collection):
        """ Performs the node replacement.

        Args:
            app: Sphinx application object to use.
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        top_items = collection.get_item_objects(self['top'], self['filter-attributes'])
        top_node = self.create_top_node(self['title'])
        if isinstance(app.builder, LaTeXBuilder):
            p_node = nodes.paragraph()
            p_node.append(nodes.Text('Item tree is not supported in latex builder'))
            top_node.append(p_node)
        else:
            ul_node = nodes.bullet_list()
            ul_node['classes'].append('bonsai')
            container = {}
            for item in top_items:
                if not item.is_linked(self['top_relation_filter'], self['top']):
                    container[item.identifier] = []
                    self._fill_container(collection, item, container)
            del top_items
            for item_id in natsorted(container):
                ul_node.append(self._generate_bullet_list_tree(app, item_id, container[item_id]))
            del container
            top_node += ul_node
        self.replace_self(top_node)

    def _fill_container(self, collection, item, container):
        """ Fills the container with the ID of every valid target of the given item, recursively

        Args:
            collection (TraceableCollection): Collection of all traceable items.
            item (TraceableItem): Traceable item to add if it has at least one valid target item.
            container (dict): Container to fill.

        Returns:
            dict: Container: mapping of an item ID to a list of nested containers.
        """
        parent_id = item.identifier
        for relation in self['type']:
            target_ids = item.yield_targets_sorted(relation)
            for target_id in target_ids:
                target_item = collection.get_item(target_id)
                if target_item.attributes_match(self['filter-attributes']):
                    try:
                        container[parent_id].append(self._fill_container(collection, target_item, {target_id: []}))
                    except RecursionError as err:
                        msg = ("Could not process item-tree {!r} because of a circular relationship: {} {} {}"
                               .format(self['title'], parent_id, relation, target_id))
                        raise TraceabilityException(msg) from err
            del target_ids
        container[parent_id].sort(key=natsort_key)
        return container

    def _generate_bullet_list_tree(self, app, item_id, containers):
        '''
        Generates a bullet list tree for the given item ID.

        This function returns the given item ID as a bullet item node, makes a child bulleted list, and adds all
        of the matching child items to it.
        '''
        # First add current item ID
        bullet_list_item = nodes.list_item()
        bullet_list_item['id'] = nodes.make_id(item_id)
        arrow_node = nodes.paragraph()
        arrow_node['classes'].append('thumb')
        bullet_list_item.append(arrow_node)
        p_node = self.make_internal_item_ref(app, item_id)
        bullet_list_item.append(p_node)
        bullet_list_item['classes'].append('has-children')
        bullet_list_item['classes'].append('collapsed')
        if containers:
            childcontent = nodes.bullet_list()
            childcontent['classes'].append('bonsai')
            bullet_list_item.append(childcontent)
        # Then recurse one level, and add dependencies
        for container in containers:
            for target_id, nested_containers in container.items():
                childcontent.append(self._generate_bullet_list_tree(app, target_id, nested_containers))
            del container
        return bullet_list_item


class ItemTreeDirective(TraceableBaseDirective):
    """
    Directive to generate a treeview of items, based on
    a given set of relationship types.

    Syntax::

      .. item-tree:: title
         :top: regexp
         :top_relation_filter: <<relationship>> ...
         :<<attribute>>: regexp
         :type: <<relationship>> ...
         :nocaptions:
         :onlycaptions:

    """
    # Optional argument: title (whitespace allowed)
    optional_arguments = 1
    # Options
    option_spec = {
        'class': directives.class_option,
        'top': directives.unchanged,
        'top_relation_filter': directives.unchanged,  # a string with relationship types separated by space
        'type': directives.unchanged,  # a string with relationship types separated by space
        'nocaptions': directives.flag,
        'onlycaptions': directives.flag,
    }
    # Content disallowed
    has_content = False

    def run(self):
        """ Processes the contents of the directive. """
        env = self.state.document.settings.env
        app = env.app

        item_tree_node = ItemTree('')
        item_tree_node['document'] = env.docname
        item_tree_node['line'] = self.lineno

        self.process_title(item_tree_node, 'Tree of items')

        self.process_options(
            item_tree_node,
            {
                'top':                 {'default': '', 'is_pattern': True},
                'top_relation_filter': {'default': []},
                'type':                {'default': []},
            },
        )

        self.add_found_attributes(item_tree_node, is_pattern=True)

        self.check_relationships(item_tree_node['top_relation_filter'], env)

        # Check if given relationships are in configuration
        # Combination of forward + matching reverse relationship cannot be in the same list, as it will give
        # endless treeview (and endless recursion in python --> exception)
        collection = env.traceability_collection
        for rel in item_tree_node['type']:
            if rel not in collection.relations:
                report_warning('Traceability: unknown relation for item-tree: %s' % rel, env.docname, self.lineno)
                continue
            if collection.get_reverse_relation(rel) in item_tree_node['type']:
                report_warning('Traceability: combination of forward+reverse relations for item-tree: %s' % rel,
                               env.docname, self.lineno)
                raise ValueError('Traceability: combination of forward+reverse relations for item-tree: %s' % rel)

        self.check_caption_flags(item_tree_node, app.config.traceability_tree_no_captions)

        return [item_tree_node]
