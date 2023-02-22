from docutils.parsers.rst import directives

from mlx.traceability_exception import report_warning, TraceabilityException
from mlx.traceable_base_directive import TraceableBaseDirective
from mlx.traceable_base_node import TraceableBaseNode


class ItemLink(TraceableBaseNode):
    '''Linking of documentation items'''
    order = 1  # before ItemRelink

    def perform_replacement(self, app, collection):
        """ The ItemLink node has no final representation, so is removed from the tree.

        Args:
            app: Sphinx application object to use.
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        self.replace_self([])

    def apply_effect(self, collection):
        """ Processes the item-link items, which shall be done before converting anything to docutils and before any
        item-relink items have been processed.

        Args:
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        if self['sources']:
            source_items = self['sources']
        else:
            source_items = collection.get_items(self['source'], sort=False)
        if self['targets']:
            target_items = self['targets']
        else:
            target_items = collection.get_items(self['target'], sort=False)
        # Processing of the item-link items. They get added as additional relationships
        # to the existing items. Should be done before converting anything to docutils.
        for source in source_items:
            for target in target_items:
                try:
                    collection.add_relation(source, self['type'], target)
                except TraceabilityException as err:
                    if not self['nooverwrite']:
                        report_warning(err, self['document'], self['line'])


class ItemLinkDirective(TraceableBaseDirective):
    """
    Directive to add additional relations between lists of items.

    Syntax::

      .. item-link::
         :source: regexp
         :sources: list_of_items
         :target: regexp
         :targets: list_of_items
         :type: relationship_type
         :nooverwrite: flag
    """
    # Options
    option_spec = {
        'source': directives.unchanged,
        'sources': directives.unchanged,
        'target': directives.unchanged,
        'targets': directives.unchanged,
        'type': directives.unchanged,
        'nooverwrite': directives.flag,
    }
    # Content disallowed
    has_content = False

    def run(self):
        """ Processes the contents of the directive. """
        env = self.state.document.settings.env

        node = ItemLink('')
        node['document'] = env.docname
        node['line'] = self.lineno

        process_options_success = self.process_options(
            node,
            {
                'type':    {'default': ''},
            },
            docname=env.docname
        )
        self.process_options(
            node,
            {
                'sources': {'default': []},
                'targets': {'default': []},
                'source':  {'default': '', 'is_pattern': True},
                'target':  {'default': '', 'is_pattern': True},
            },
        )
        for mutually_exclusive_options in ({'sources', 'source'}, {'targets', 'target'}):
            option_amount = len(mutually_exclusive_options.intersection(self.options))
            if option_amount != 1:
                report_warning(f"item-link: expected exactly one of the following options but got {option_amount}: "
                               f"{mutually_exclusive_options}", env.docname, self.lineno)
                process_options_success = False

        self.check_option_presence(node, 'nooverwrite')
        if not process_options_success:
            return []
        env.traceability_collection.add_intermediate_node(node)
        return [node]
