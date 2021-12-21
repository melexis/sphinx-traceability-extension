"""Module for the item-relink directive"""
from docutils.parsers.rst import directives

from mlx.traceability import report_warning
from mlx.traceable_base_directive import TraceableBaseDirective
from mlx.traceable_base_node import TraceableBaseNode


class ItemRelink(TraceableBaseNode):
    """Relinking of documentation items"""

    def perform_replacement(self, app, collection):
        """ Processes the item-link items. The ItemRelink node has no final representation, so is removed from the tree.

        Args:
            app: Sphinx application object to use.
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        self.replace_self([])


class ItemRelinkDirective(TraceableBaseDirective):
    """Directive to link a source to a different target or remove a relationship.

    Syntax::

      .. item-link::
         :source: item
         :target: item
         :type: relationship_type
    """
    # Options
    option_spec = {
        'source': directives.unchanged,
        'target': directives.unchanged,
        'type': directives.unchanged,
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
                'source': {'default': ''},
                'target': {'default': ''},
                'type':   {'default': ''},
            },
            docname=env.docname
        )
        if not process_options_success:
            return []

        # Processing of the item-relink items. Should be done before converting anything to docutils.
        collection = env.traceability_collection
        source_id = node['source']
        source = collection.get_item(source_id)
        target_id = node['target']
        forward_type = node['type']
        reverse_type = collection.get_reverse_relation(forward_type)
        affected_items = set()
        if source is None:
            report_warning("Could not find source item {!r} specified in item-relink directive".format(source_id))
            return []
        else:
            for item_id in source.iter_targets(reverse_type, sort=False):
                affected_items.add(item_id)
        for item_id in affected_items:
            item = collection.get_item(item_id)
            item.remove_targets(source_id, explicit=True, implicit=True, relations={forward_type})
            source.remove_targets(item_id, explicit=True, implicit=True, relations={reverse_type})
            if target_id:
                collection.add_relation(item_id, forward_type, target_id)

        # Remove source from collection if it is not defined as an item
        if source.is_placeholder():
            collection.items.pop(source_id)

        # The ItemRelink node has no final representation, so is removed from the tree
        return [node]
