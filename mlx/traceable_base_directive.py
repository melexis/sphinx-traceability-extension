""" Module for the base class for all Traceability directives. """
from abc import ABC, abstractmethod
from docutils.parsers.rst import Directive

from mlx.traceability_exception import report_warning
from mlx.traceable_item import TraceableItem


class TraceableBaseDirective(Directive, ABC):
    """ Base class for all Traceability directives. """

    final_argument_whitespace = True

    @abstractmethod
    def run(self):
        """ Processes directive's contents. Called by Sphinx. """

    def get_caption(self):
        """ Gets the item's caption.

        Item caption is the text following the mandatory id argument. Caption should be considered a to be line of text.
        Remove line breaks.

        Returns:
            (str) Formatted caption.
        """
        if len(self.arguments) > 1:
            return self.arguments[1].replace('\n', ' ')
        return ''

    def add_found_attributes(self, node):
        """ Adds found attributes to item. Attribute data is a single string.

        Args:
            node (TraceableBaseNode): Node object for which to add found attributes to.
        """
        node['filter-attributes'] = {}
        for attr in TraceableItem.defined_attributes.keys():
            if attr in self.options:
                node['filter-attributes'][attr] = self.options[attr]


    def remove_unknown_attributes(self, attributes, description, env):
        """ Removes any unknown attributes from the given list while reporting a warning.

        Args:
            attributes (list): List of attributes (str).
            description (str): Description of an element in the attributes list.
            env (sphinx.environment.BuildEnvironment): Sphinx' build environment.
        """
        for attr in attributes:
            if attr not in TraceableItem.defined_attributes.keys():
                report_warning(env, 'Traceability: unknown %s for item-attributes-matrix: %s' % (description, attr),
                               env.docname, self.lineno)
                attributes.remove(attr)

    def check_relationships(self, relationships, env):
        """  Checks if given relationships are in configuration.

        Args:
            relationships (list): List of relationships (str).
        """
        for rel in relationships:
            if rel not in env.traceability_collection.iter_relations():
                report_warning(env, 'Traceability: unknown relation for %s: %s' % (self.name, rel),
                               env.docname, self.lineno)

    def check_no_captions_flag(self, node, no_captions_config):
        """ Checks the nocaptions flag.

        Args:
            node (TraceableBaseNode): Node object for which to set the nocaptions flag.
            no_captions_config (bool): Value for nocaptions option in configuration.
        """
        node['nocaptions'] = bool(no_captions_config or 'nocaptions' in self.options)

    def process_options(self, node, options):
        """ Processes given options.

        Args:
            node (TraceableBaseNode): Node object for which to set the target and source options.
            options (dict): Dictionary with options (str) as keys and default values (str) as values.
        """
        for option, default_value in options.items():
            if option in self.options:
                if isinstance(default_value, list):
                    node[option] = self.options[option].split()
                else:
                    node[option] = self.options[option]
            else:
                node[option] = default_value

    def check_option_presence(self, node, option):
        """ Checks the presence of the given option. Set the value to True if the option is present, False otherwise.

        Args:
            node (TraceableBaseNode): Node object for which to set the nocaptions flag.
            option (str): Name of the option.
        """
        if option in self.options:
            node[option] = True
        else:
            node[option] = False
