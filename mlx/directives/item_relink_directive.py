"""Module for the item-relink directive"""
from docutils.parsers.rst import directives

from mlx.traceability import TraceabilityException, report_warning
from mlx.traceable_base_directive import TraceableBaseDirective
from mlx.traceable_base_node import TraceableBaseNode


class ItemRelink(TraceableBaseNode):
    """Relinking of documentation items"""
    order = 2  # after ItemLink
    source_ids = set()

    def perform_replacement(self, app, collection):
        """ The ItemRelink node has no final representation, so is removed from the tree.

        Args:
            app: Sphinx application object to use.
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        self.replace_self([])

    def apply_effect(self, collection):
        """ Processes the item-relink items, which shall be done before converting anything to docutils.

        Args:
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        source_id = self['remap']
        source = collection.get_item(source_id)
        target_id = self['target']
        forward_type = self['type']
        reverse_type = collection.get_reverse_relation(forward_type)

        if source is None:
            report_warning("Could not find item {!r} with type {!r} specified in item-relink directive"
                           .format(source_id, forward_type), self['document'], self['line'])
            return
        if not reverse_type:
            report_warning(("Could not find reverse relationship type for type {!r} specified in "
                            "{!r} item-relink directive").format(forward_type, source_id),
                           self['document'], self['line'])
            return

        affected_items = set()
        for item_id in source.yield_targets(reverse_type):
            affected_items.add(item_id)
        for item_id in affected_items:
            item = collection.get_item(item_id)
            item.remove_targets(source_id, explicit=True, implicit=True, relations={forward_type})
            source.remove_targets(item_id, explicit=True, implicit=True, relations={reverse_type})
            if target_id:
                try:
                    collection.add_relation(item_id, forward_type, target_id)
                except TraceabilityException as err:
                    if not self['nooverwrite']:
                        report_warning(err, self['document'], self['line'])

        self.source_ids.add(source_id)

    @staticmethod
    def remove_placeholders(collection):
        """Removes items that are no longer needed to avoid a warning about them being undefined.

        Items that are no longer needed are placeholders without any targets; if it has targets left, i.e. they have
        not been relinked, a warning for each target will be reported.

        Args:
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        for source_id in ItemRelink.source_ids:
            source = collection.get_item(source_id)
            if source.is_placeholder and not [targets for _, targets in source.all_relations if targets]:
                collection.items.pop(source_id)


class ItemRelinkDirective(TraceableBaseDirective):
    """Directive to link items to a different target or remove a relationship.

    Syntax::

      .. item-link::
         :remap: item
         :target: item
         :type: relationship_type
         :nooverwrite: flag
    """
    # Options
    option_spec = {
        'remap': directives.unchanged,
        'target': directives.unchanged,
        'type': directives.unchanged,
        'nooverwrite': directives.flag,
    }
    # Content disallowed
    has_content = False

    def run(self):
        """ Processes the contents of the directive. """
        env = self.state.document.settings.env

        node = ItemRelink('')
        node['document'] = env.docname
        node['line'] = self.lineno

        process_options_success = self.process_options(
            node,
            {
                'remap': {'default': ''},
                'target': {'default': ''},
                'type':   {'default': ''},
            },
            docname=env.docname
        )
        self.check_option_presence(node, 'nooverwrite')

        if not process_options_success:
            return []
        env.traceability_collection.add_intermediate_node(node)
        return [node]
