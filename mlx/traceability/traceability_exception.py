'''
Exception classes for traceability
'''
from sphinx.util.logging import getLogger


def report_warning(msg, docname=None, lineno=None):
    '''Convenience function for logging a warning

    Args:
        msg (any __str__): Message of the warning, gets converted to str.
        docname (str): Relative path to the document on which the error occurred, without extension.
        lineno (int): Line number in the document on which the error occurred.
    '''
    msg = str(msg)
    logger = getLogger(__name__)
    if lineno is not None:
        logger.warning(msg, location=(docname, str(lineno)))
    else:
        logger.warning(msg, location=docname)


class MultipleTraceabilityExceptions(Exception):
    '''
    Multiple exceptions for traceability plugin
    '''
    def __init__(self, errors):
        '''
        Constructor for multiple traceability exceptions
        '''
        self.errors = errors

    def __iter__(self):
        '''Iterate over multiple exceptions'''
        yield from self.errors


class TraceabilityException(Exception):
    '''
    Exception for traceability plugin
    '''
    def __init__(self, message, docname=''):
        '''
        Constructor for traceability exception

        Args:
            message (str): Message for the exception
            docname (str): Name of the document triggering the exception
        '''
        super().__init__(message)
        self.docname = docname
