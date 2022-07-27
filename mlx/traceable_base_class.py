'''
Base class for traceable stuff
'''

import hashlib

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles

from mlx.traceability_exception import report_warning, TraceabilityException


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

    @property
    def id(self):
        report_warning("TraceableBaseClass.id will be removed in version 10.x in favor of "
                       "TraceableBaseClass.identifier", docname=self.docname, lineno=self.lineno)
        return self.identifier

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

    def get_id(self):
        '''
        Getter for identification

        Returns:
            str: identification
        '''
        report_warning("TraceableBaseClass.get_id() will be removed in version 10.x in favor of "
                       "TraceableBaseClass.identifier", docname=self.docname, lineno=self.lineno)
        return self.identifier

    def set_name(self, name):
        '''
        Set readable name

        Args:
            name (str): Short name
        '''
        report_warning("TraceableBaseClass.set_name() will be removed in version 10.x: "
                       "set TraceableBaseClass.name directly instead", docname=self.docname, lineno=self.lineno)
        self.name = name

    def get_name(self):
        '''
        Get readable name

        Returns:
            str: Short name
        '''
        report_warning("TraceableBaseClass.get_name() will be removed in version 10.x in favor of "
                       "TraceableBaseClass.name", docname=self.docname, lineno=self.lineno)
        return self.name

    def set_caption(self, caption):
        '''
        Set caption

        Args:
            caption (str): Short caption
        '''
        report_warning("TraceableBaseClass.set_caption() will be removed in version 10.x: "
                       "set TraceableBaseClass.caption directly instead", docname=self.docname, lineno=self.lineno)
        self.caption = caption

    def get_caption(self):
        '''
        Get caption

        Returns:
            str: Short caption
        '''
        report_warning("TraceableBaseClass.get_caption() will be removed in version 10.x in favor of "
                       "TraceableBaseClass.caption", docname=self.docname, lineno=self.lineno)
        return self.caption

    def set_location(self, docname, lineno=0):
        '''
        Set location in document

        Args:
            docname (str): Path to docname
            lineno (int): Line number in given document
        '''
        self.docname = docname
        self.lineno = lineno

    def set_document(self, docname, lineno=0):
        '''
        Set location in document

        Args:
            docname (str): Path to docname
            lineno (int): Line number in given document
        '''
        self.set_location(docname, lineno=lineno)
        report_warning("TraceableBaseClass.set_document() will be removed in version 10.x: "
                       "use TraceableBaseClass.set_location() instead", docname=self.docname, lineno=self.lineno)

    def get_document(self):
        '''
        Get location in document

        Returns:
            str: Path to docname
        '''
        report_warning("TraceableBaseClass.get_document() will be removed in version 10.x in favor of "
                       "TraceableBaseClass.docname", docname=self.docname, lineno=self.lineno)
        return self.docname

    def get_line_number(self):
        '''
        Get line number in document

        Returns:
            int: Line number in given document
        '''
        report_warning("TraceableBaseClass.get_line_number() will be removed in version 10.x in favor of "
                       "TraceableBaseClass.lineno", docname=self.docname, lineno=self.lineno)
        return self.lineno

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

    def set_content(self, content):
        '''
        Set content of the item

        Args:
            content (str): Content of the item
        '''
        self.content = content
        report_warning("TraceableBaseClass.set_content() will be removed in version 10.x: "
                       "set TraceableBaseClass.content directly instead", docname=self.docname, lineno=self.lineno)

    def get_content(self):
        '''
        Get content of the item

        Returns:
            str: Content of the item
        '''
        report_warning("TraceableBaseClass.get_content() will be removed in version 10.x in favor of "
                       "TraceableBaseClass.content", docname=self.docname, lineno=self.lineno)
        return self.content

    def bind_node(self, node):
        '''
        Bind to node

        Args:
            node (node): Docutils node object
        '''
        report_warning("TraceableBaseClass.bind_node() will be removed in version 10.x: "
                       "set TraceableBaseClass.node directly instead", docname=self.docname, lineno=self.lineno)
        self.node = node

    def get_node(self):
        '''
        Get the node to which the object is bound

        Returns:
            node: Docutils node object
        '''
        report_warning("TraceableBaseClass.get_node() will be removed in version 10.x in favor of "
                       "TraceableBaseClass.node", docname=self.docname, lineno=self.lineno)
        return self.node

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
