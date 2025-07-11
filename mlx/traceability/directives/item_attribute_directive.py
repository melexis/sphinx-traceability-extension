"""Module for the item-attribute directive"""
from pathlib import Path
from docutils import nodes

from ..traceability_exception import report_warning
from ..traceable_attribute import TraceableAttribute
from ..traceable_base_directive import TraceableBaseDirective
from ..traceable_base_node import TraceableBaseNode


class ItemAttribute(TraceableBaseNode):
    """Attribute to documentation item"""

    def perform_replacement(self, app, collection):
        """
        Perform the node replacement
        Args:
            app: Sphinx application object to use.
            collection (TraceableCollection): Collection for which to generate the nodes.
        """
        if self['id'] in collection.defined_attributes:
            attr = collection.defined_attributes[self['id']]
            header = attr.name
            if attr.caption:
                header += ': ' + attr.caption
            # Include the attribute content if it exists
            top_node = self.create_top_node(header)
            if hasattr(attr, 'content_node') and attr.content_node:
                top_node.append(attr.content_node)
        else:
            header = self['id']
            top_node = self.create_top_node(header)
        self.replace_self(top_node)


class ItemAttributeDirective(TraceableBaseDirective):
    """
    Directive to declare attribute for items

    Syntax::

      .. item-attribute:: attribute_id [attribute_caption]

         [attribute_content]

    """
    # Required argument: id
    required_arguments = 1
    # Optional argument: caption (whitespace allowed)
    optional_arguments = 1
    # Content allowed
    has_content = True

    def run(self):
        """ Processes the contents of the directive. """
        env = self.state.document.settings.env

        # Convert to lower-case as sphinx only allows lowercase arguments (attribute to item directive)
        attribute_id = self.arguments[0]
        attribute_node = ItemAttribute('')
        attribute_node['document'] = env.docname
        attribute_node['line'] = self.lineno

        stored_id = TraceableAttribute.to_id(attribute_id)
        target_node = nodes.target('', '', ids=[stored_id])
        if stored_id not in env.traceability_collection.defined_attributes:
            report_warning('Found attribute description which is not defined in configuration ({})'
                           .format(attribute_id),
                           env.docname,
                           self.lineno)
            attr = TraceableAttribute(stored_id, ".*", directive=self)
            env.traceability_collection.define_attribute(attr)
            attribute_node['id'] = stored_id
        else:
            attr = env.traceability_collection.defined_attributes[stored_id]
            if self.caption:
                attr.caption = self.caption
            doc_path_str, lineno = self.get_source_info()
            doc_path = Path(doc_path_str)
            if doc_path.is_absolute():
                doc_path = doc_path.relative_to(env.srcdir)
            attr.set_location(doc_path, lineno)
            attribute_node['id'] = attr.identifier

            # Set directive reference for content parsing
            # This ensures content can be parsed even for existing attributes
            attr.directive = self

        attr.content = self.content
        return [target_node, attribute_node, attr.content_node]
