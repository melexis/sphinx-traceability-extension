'''
Base class for traceable stuff
'''

import hashlib

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles

from .traceability_exception import TraceabilityException


class TraceableBaseClass:
    '''
    Storage for a traceable base class
    '''

    def __init__(self, name, state=None):
        '''
        Initialize a new base class

        Args:
            name (str): Base class object identification
            state: The state of the state machine, which controls the parsing
        '''
        self.identifier = self.to_id(name)
        self.name = name
        self.caption = None
        self.docname = None
        self.lineno = None
        self.node = None
        self._content = None
        self.content_node = nodes.block_quote()
        self._state = state

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

    def set_location(self, docname, lineno=0):
        '''
        Set location in document

        Args:
            docname (str): Path to docname
            lineno (int): Line number in given document
        '''
        self.docname = docname
        self.lineno = lineno

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        self._content = content
        if self._state:
            template = ViewList(source=self.docname, parent_offset=self.lineno)
            for idx, line in enumerate(content.split('\n')):
                template.append(line, self.docname, idx)
            self.content_node = nodes.block_quote()  # reset
            nested_parse_with_titles(self._state, template, self.content_node)

    def clear_state(self):
        '''
        Clear value of state attribute, which should not be used after directives have been processed
        '''
        self._state = None

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
