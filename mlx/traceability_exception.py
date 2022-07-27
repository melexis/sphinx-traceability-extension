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

    def iter(self):
        '''Iterator for multiple exceptions'''
        report_warning("MultipleTraceabilityExceptions.iter() will be removed in version 10.x: "
                       "you can now loop over an instance of this class directly")
        return self.errors


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

    def get_document(self):
        '''
        Get document in which error occurred

        Returns:
            str: The name of the document in which the error occurred
        '''
        report_warning("TraceabilityException.get_document() will be removed in version 10.x in favor of "
                       "TraceabilityException.docname", docname=self.docname)
        return self.docname
