""" Module for the directive for declaring checklist items. """
from .item_directive import ItemDirective
from ..traceability_exception import report_warning, TraceabilityException


class ChecklistItemDirective(ItemDirective):
    """
    Directive to declare checklist items and their traceability relationships. The behavior is the same as
    ItemDirective except that an extra attribute is added when the item ID is found in the queried checklist.
    The checklist has been queried using the ``traceability_checklist`` configuration variable.
    """
    query_results = {}

    def run(self):
        """ Processes the contents of the directive. """
        env = self.state.document.settings.env
        env.traceability_checklist['has_checklist_items'] = True

        nodes = super().run()
        target_id = self.arguments[0]
        if not env.traceability_checklist.get('configured'):
            raise TraceabilityException("The checklist attribute in 'traceability_checklist' is not configured "
                                        "properly. See documentation for more details.")
        try:
            item = env.traceability_collection.get_item(target_id)
            attribute_name = env.traceability_checklist['attribute_name']
            item.add_attribute(attribute_name, self.query_results.pop(target_id).attr_val)
        except TraceabilityException as err:
            report_warning(err, env.docname, self.lineno)
        except KeyError:
            # the checklist-item can still get the checklist_attribute by the checkbox-result directive
            pass

        return nodes
