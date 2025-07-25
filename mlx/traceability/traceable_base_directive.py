""" Module for the base class for all Traceability directives. """
import re
from abc import ABC, abstractmethod
from sphinx.util.docutils import SphinxDirective

from .traceability_exception import report_warning
from .traceable_item import TraceableItem


class TraceableBaseDirective(SphinxDirective, ABC):
    """ Base class for all Traceability directives. """

    final_argument_whitespace = True
    conflicting_options = set()

    @abstractmethod
    def run(self):
        """ Processes directive's contents. Called by Sphinx. """

    def process_title(self, node, default_title=''):
        """ Adds the title to the item. If no title is specified, the given default title is used.

        Args:
            node (TraceableBaseNode): Node object for which to add found attributes to.
            default_title (str): Default title.
        """
        if self.arguments:
            node['title'] = self.arguments[0]
        else:
            node['title'] = default_title

    @property
    def caption(self):
        """ Gets the item's caption.

        Item caption is the text following the mandatory id argument. Caption should be considered a to be line of text.
        Remove line breaks.

        Returns:
            (str) Formatted caption.
        """
        if len(self.arguments) > 1:
            return self.arguments[1].replace('\n', ' ')
        return ''

    def add_found_attributes(self, node, is_pattern=False):
        """ Adds found attributes to node. Attribute data is a single string.

        Args:
            node (TraceableBaseNode): Node object for which to add found attributes to.
            is_pattern (bool): True to treat the attribute value as a regular expression pattern and compile it if it
                is not empty.
        """
        node['filter-attributes'] = {}
        for attr in set(TraceableItem.defined_attributes) & set(self.options) - self.conflicting_options:
            value = self.options[attr]
            if is_pattern and value != '':
                value = re.compile(value)
            node['filter-attributes'][attr] = value

    def add_attributes(self, node, option, default, description='attribute'):
        """ Adds all valid attribute keys in the option's value to the node

        A warning is reported for every unknown attribute and in case of comma- instead of space-separation.
        If the option is not used or its value is empty, the ``default`` value is used.

        Args:
            node (TraceableBaseNode): Node object for which to add the attributes to, using ``option`` as key.
            option (str): Name of the option to look for
            default (list): Default attributes to use
            description (str): Describes what kind of attribute it is, to use in warning message
        """
        if option in self.options and self.options[option]:
            self._warn_if_comma_separated(option, node['document'])
            node[option] = self.options[option].split()
        else:
            node[option] = default
        self.remove_unknown_attributes(node[option], description, node['document'])

    def remove_unknown_attributes(self, attributes, description, docname):
        """ Removes any unknown attributes from the given list while reporting a warning.

        Args:
            attributes (list): List of attributes (str).
            description (str): Description of an element in the attributes list.
            docname (str): Document name.
        """
        for attr in set(attributes) - set(TraceableItem.defined_attributes):
            report_warning('Traceability: unknown %s for item-(attributes-)matrix: %s' % (description, attr),
                           docname, self.lineno)
            attributes.remove(attr)

    def add_attributes_and_relations(self, node, option, defined_relations):
        """ Adds all valid attribute keys in the option's value to the node along with valid relationships

        Args:
            node (TraceableBaseNode): Node object for which to add valid values to, using ``option`` as key.
            option (str): Name of the option to look for
            defined_relations (dict): All defined relationships
        """
        node[option] = []
        if option in self.options:
            values = self.options[option].split()
            self._warn_if_comma_separated(option, node['document'])
            for value in values:
                if value in defined_relations or value in TraceableItem.defined_attributes:
                    node[option].append(value)
            leftover_values = set(values).difference(node[option])
            self.remove_unknown_attributes(leftover_values, 'attribute/relationship', node['document'])

    def check_relationships(self, relationships, env):
        """  Checks if given relationships are in configuration.

        Args:
            relationships (list): List of relationships (str).
            env (sphinx.environment.BuildEnvironment): Sphinx's build environment.
        """
        for rel in set(relationships) - set(env.traceability_collection.relations):
            report_warning('Traceability: unknown relation for %s: %s' % (self.name, rel),
                           env.docname, self.lineno)

    def check_caption_flags(self, node, no_captions_config):
        """ Checks the nocaptions and onlycaptions flags.

        Args:
            node (TraceableBaseNode): Node object for which to set the nocaptions flag.
            no_captions_config (bool): Value for nocaptions option in configuration.
        """
        if 'onlycaptions' in self.options:
            node['nocaptions'] = False
            node['onlycaptions'] = True
        else:
            node['nocaptions'] = bool(no_captions_config or 'nocaptions' in self.options)
            node['onlycaptions'] = False

    def process_options(self, node, options, docname=None):
        """ Processes given options.

        If the document name is specified, all options are treated as required, a warning is reported for the
        first missing option, and False is returned. If all goes well, True is returned.

        Args:
            node (TraceableBaseNode): Node object for which to set the target and source options.
            options (dict): Dictionary with options (str) as keys and a dict of additional configurations as values:
                Example:

                | {
                |     'target': { 'default': [''] },
                |     'source': { 'default': '', 'is_pattern': True },
                |     'targettitle': { 'default': ['Target'], 'delimiter': ',' },
                |     'sourcetitle': { 'default': 'Source' },
                |     'type': { 'default': [] },
                | }

                The 'default' configuration is mandatory. It is used to set the value in case none is given AND it is
                used to determine the type of the option (list or single value).
                The 'delimiter' configuration is optional and defaults to ' ' (single space). It is used to determine
                which character needs to be used to split the option value into a list.
                The 'is_pattern' configuration is optional and defaults to False. If True, each option value is
                treated as a regular expression pattern (str) and compiled to a re.Pattern object.
            docname (str): Document name.

        Returns:
            (bool) False if a required option is missing, True otherwise.
        """
        for option, option_config in options.items():
            if option in self.options:
                value = self.options[option]
                if option == 'filter':
                    value = value.replace('\n', '').strip()
                if isinstance(option_config['default'], list):
                    delimiter = option_config.get('delimiter', None)
                    if delimiter == ' ':
                        self._warn_if_comma_separated(option, docname)
                    node[option] = [x.strip() for x in value.split(delimiter)]
                else:
                    node[option] = value
            elif docname:
                report_warning('%s argument required for %s directive' % (option, self.name),
                               docname,
                               self.lineno)
                return False
            else:
                node[option] = option_config['default']

            if option_config.get('is_pattern') and node[option]:
                if isinstance(node[option], str):
                    node[option] = re.compile(node[option])
                else:
                    node[option] = [re.compile(value) for value in node[option]]
        return True

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

    def _warn_if_comma_separated(self, option, docname):
        """ Reports a warning if the option's arguments are comma-separated.

        Args:
            option (str): Option name.
            docname (str): Document name.
        """
        if len(self.options[option].split(',')) > 1:
            report_warning("The arguments of the '{}' option must be space-separated without commas; "
                           "got '{}'.".format(option, self.options[option]),
                           docname,
                           self.lineno)
