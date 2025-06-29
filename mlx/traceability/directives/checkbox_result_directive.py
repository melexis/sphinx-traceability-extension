""" Module for the directive used to set the checklist attribute. """
from re import match

from ..traceable_base_directive import TraceableBaseDirective
from ..traceable_base_node import TraceableBaseNode
from ..traceability_exception import report_warning


class CheckboxResult(TraceableBaseNode):
    """Intermediate node for checkbox-result directive that gets processed later."""
    order = 0  # Process early, before other nodes

    def perform_replacement(self, app, collection):
        """The CheckboxResult node has no final representation, so is removed from the tree."""
        self.replace_self([])

    def apply_effect(self, collection):
        """Apply the checkbox result effect during consistency check when all items are available."""
        target_id = self['target_id']
        attribute_value = self['attribute_value']

        checklist_item = collection.get_item(target_id)
        if not checklist_item:
            msg = "Could not find item ID {!r}".format(target_id)
            report_warning(msg, self['document'], self['line'])
            return

        # Get configuration from stored values
        checklist_configured = self.get('checklist_configured', False)
        if not checklist_configured:
            msg = ("The checklist attribute in 'traceability_checklist' is not configured "
                   "properly. See documentation for more details.")
            report_warning(msg, self['document'], self['line'])
            return

        checklist_attribute_name = self['checklist_attribute_name']
        regexp = self['attribute_regexp']
        if match(regexp, attribute_value):
            checklist_item.add_attribute(checklist_attribute_name, attribute_value, overwrite=True)
        else:
            msg = "Checkbox value invalid: {!r} does not match regex {}".format(attribute_value, regexp)
            report_warning(msg, self['document'], self['line'])


class CheckboxResultDirective(TraceableBaseDirective):
    """
    Directive to set value of the checklist attribute for a checklist-item.

    Syntax::
      .. checkbox-result:: item_id attribute_value

    When run, no nodes will be returned.
    """
    # Required argument: id + attribute_value (separated by a whitespace)
    required_arguments = 2

    def run(self):
        """ Processes the contents of the directive. """
        env = self.state.document.settings.env
        app = env.app

        target_id = self.arguments[0]
        attribute_value = self.arguments[1]

        # Extract and store only the configuration values we need (avoid storing app object)
        checklist_configured = app.config.traceability_checklist.get('configured', False)
        checklist_attribute_name = None
        attribute_regexp = None

        if checklist_configured:
            checklist_attribute_name = app.config.traceability_checklist['attribute_name']
            attribute_regexp = app.config.traceability_attributes[checklist_attribute_name]

        # Create intermediate node for deferred processing
        node = CheckboxResult('')
        node['document'] = env.docname
        node['line'] = self.lineno
        node['target_id'] = target_id
        node['attribute_value'] = attribute_value
        node['checklist_configured'] = checklist_configured
        node['checklist_attribute_name'] = checklist_attribute_name
        node['attribute_regexp'] = attribute_regexp

        # Add to intermediate nodes for processing during consistency check
        env.traceability_collection.add_intermediate_node(node)

        return [node]
