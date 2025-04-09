'''
Base class for traceable stuff
'''

import hashlib
from docutils.statemachine import StringList, ViewList

from sphinx.util.docutils import nodes

from .traceability_exception import TraceabilityException, report_warning


class TraceableBaseClass:
    '''
    Storage for a traceable base class
    '''

    def __init__(self, name, directive=None):
        '''
        Initialize a new base class

        Args:
            name (str): Base class object identification
            directive: The associated SphinxDirective instance, if one exists
        '''
        self.identifier = self.to_id(name)
        self.name = name
        self.caption = None
        self.docname = None
        self.lineno = None
        self.node = None
        self._content = None
        self.content_node = nodes.container()
        self.content_node['ids'].append(f'content-{self.identifier}')
        self.directive = directive
        if directive is not None:
            directive.state.document.ids[f'content-{self.identifier}'] = self.content_node

    @staticmethod
    def to_id(identifier):
        '''
        Convert a given identification to a storable id

        Args:
            id (str): input identification
        Returns:
            str - Converted storable identification
        '''
        return identifier

    def update(self, other):
        '''
        Update with new object

        Store the sum of both objects
        '''
        if self.identifier != other.identifier:
            raise ValueError('Update error {old} vs {new}'.format(old=self.identifier, new=other.identifier))
        if other.name is not None:
            self.name = other.name
        if other.docname is not None:
            self.docname = other.docname
        if other.lineno is not None:
            self.lineno = other.lineno
        if other.node is not None:
            self.node = other.node
        if other.caption is not None:
            self.caption = other.caption
        if other.content is not None:
            self.content = other.content

    def set_location(self, docname, lineno=0, offset=2):
        '''
        Set location in document

        Args:
            docname (str/Path): Path to docname
            lineno (int): Line number in given document
            offset (int): Offset of the directive's content compared to its definition
        '''
        self.docname = str(docname)
        self.lineno = lineno
        self.content_lineno = lineno + offset  # remove?

    @property
    def content(self):
        """Returns content as a string"""
        if isinstance(self._content, (StringList, ViewList)):
            # Initial content from directive needs conversion
            self._content = '\n'.join(self._content.data)
        return self._content

    @content.setter
    def content(self, content):
        if content is None:
            self._content = None
            return

        # Store content as string internally
        if isinstance(content, str):
            self._content = content
        else:  # StringList or ViewList
            self._content = '\n'.join(content.data)

        # Update directive's content if still available
        if self.directive:
            if isinstance(content, str):
                self._update_directive_content_from_string(content)
            else:
                self.directive.content = content

            # Update content_node by parsing updated content
            self.content_node.children = []
            self.content_node += self.directive.parse_content_to_nodes(allow_section_headings=True)
        elif self._content:
            # Warn if content modified with no directive available
            report_warning(
                f"Content of item {self.identifier!r} was modified but no directive is available for parsing. "
                "Content modification should be performed in an earlier Sphinx event, "
                "e.g. via traceability_callback_per_item.",
                self.docname
            )

    def _update_directive_content_from_string(self, content_str):
        """
        Update the directive's content StringList from a string while preserving metadata.

        Args:
            content_str (str): The content string to use for updating
        """
        lines = content_str.splitlines()
        source = self.directive.content.source(0) if len(self.directive.content) > 0 else ""

        # Create a new list of (source, offset) tuples for each line
        items = []
        for i, _ in enumerate(lines):
            # Try to preserve original line offsets when possible
            if i < len(self.directive.content):
                _, offset = self.directive.content.info(i)
                items.append((source, offset))
            else:
                # For new lines, use the last known offset or 0
                last_offset = self.directive.content.offset(len(self.directive.content)-1) \
                    if len(self.directive.content) > 0 else 0
                items.append((source, last_offset + i - len(self.directive.content) + 1))

        # Update the directive's content with new StringList
        self.directive.content = StringList(initlist=lines, source=source, items=items)

    def clear_state(self):
        '''
        Clear access to the directive attribute, which should not be used after it has been processed
        '''
        self.directive = None

    def to_dict(self):
        '''
        Export to dictionary

        Returns:
            (dict) Dictionary representation of the object
        '''
        data = {}
        data['id'] = self.identifier
        data['name'] = self.name
        caption = self.caption
        if caption:
            data['caption'] = caption
        data['document'] = self.docname
        data['line'] = self.lineno
        if self.content:
            data['content-hash'] = hashlib.md5(self.content.encode('utf-8')).hexdigest()
        else:
            data['content-hash'] = "0"
        return data

    def self_test(self):
        '''
        Perform self test on content
        '''
        # should hold a reference to a document
        if self.docname is None:
            raise TraceabilityException("Item '{identification}' has no reference to source document."
                                        .format(identification=self.identifier))
